from datetime import datetime, timezone
from typing import Optional
import sqlalchemy as sa
import sqlalchemy.orm as so
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login
from flask import url_for
from PIL import Image
import base64
import io


followers = sa.Table(
    'followers',
    db.metadata,
    sa.Column('follower_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True), 
    sa.Column('followed_id', sa.Integer, sa.ForeignKey('user.id'), primary_key=True)  
)


class User(UserMixin, db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    username: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    email: so.Mapped[str] = so.mapped_column(sa.String(120), index=True, unique=True)
    password_hash: so.Mapped[Optional[str]] = so.mapped_column(sa.String(256))
    avatar_data: so.Mapped[Optional[bytes]] = so.mapped_column(sa.LargeBinary)
    about_me: so.Mapped[Optional[str]] = so.mapped_column(sa.String(140))
    last_seen: so.Mapped[Optional[datetime]] = so.mapped_column(default=lambda: datetime.now(timezone.utc))
    is_admin: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False)
    is_banned: so.Mapped[bool] = so.mapped_column(sa.Boolean, default=False)

    followed: so.WriteOnlyMapped['User'] = so.relationship(
        secondary=followers, 
        primaryjoin=(followers.c.follower_id == id), 
        secondaryjoin=(followers.c.followed_id == id), 
        backref=so.backref('followers', lazy='dynamic') 
    )

    reviews: so.WriteOnlyMapped['ReviewsMessage'] = so.relationship(back_populates='author', cascade='all, delete-orphan', passive_deletes=True)
    topics: so.WriteOnlyMapped['ForumTopic'] = so.relationship(back_populates='author', cascade='all, delete-orphan', passive_deletes=True)
    comments: so.WriteOnlyMapped['CommentTopic'] = so.relationship(back_populates='author', cascade='all, delete-orphan', passive_deletes=True)

    def __str__(self):
        return self.username
    
    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def defult_avatar(self, size):
        image = Image.open('app/static/avatars/default.jpg')
        image.thumbnail((size, size))

        output_stream = io.BytesIO()
        image.save(output_stream, format=image.format)
        base64_image = base64.b64encode(output_stream.getvalue()).decode('utf-8')
        return f'data:image/jpeg;base64,{base64_image}'
    
    def follow(self, user):
        if not self.is_following(user):
            self.followed.add(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        if user.id is None: 
            return False

        return db.session.scalar(self.followed.select().where(User.id == user.id).limit(1)) is not None

    def followed_topics_query(self):
        followed_user_ids_query = sa.select(followers.c.followed_id).where(followers.c.follower_id == self.id)
        followed_user_ids = db.session.scalars(followed_user_ids_query).all()
        followed_user_ids.append(self.id)

        return sa.select(ForumTopic).where(ForumTopic.user_id.in_(followed_user_ids))

    
    def avatar(self, size):
        if self.avatar_data:
            try:
                image = Image.open(io.BytesIO(self.avatar_data))
                image.thumbnail((size, size))

                if image.format == 'JPEG' and image.mode == 'RGBA':
                    image = image.convert('RGB')

                output_stream = io.BytesIO()
                image.save(output_stream, format=image.format)

                base64_image = base64.b64encode(output_stream.getvalue()).decode('utf-8')
                return f'data:image/jpeg;base64,{base64_image}'
            
            except Exception as e:
                print(f"Ошибка при обработке аватара: {e}")
                return self.defult_avatar(size)

        else:
            return self.defult_avatar(size)


@login.user_loader
def load_user(id):
    if id is not None:
        user = db.session.get(User, int(id)) 
        if user and not user.is_banned:
            return user

    return None

    
class ReviewsMessage(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(140))
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id, ondelete='CASCADE'), index=True)
    username_message: so.Mapped[str] = so.mapped_column(sa.String(140), nullable=False)

    author: so.Mapped[User] = so.relationship(back_populates='reviews')

    def __repr__(self):
        return '<Post {}>'.format(self.body)
    

class ForumTopic(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    title: so.Mapped[str] = so.mapped_column(sa.String(128), index=True) 
    body: so.Mapped[str] = so.mapped_column(sa.String(8000)) 
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id, ondelete='CASCADE'), index=True)

    author: so.Mapped[User] = so.relationship(back_populates='topics')
    comments: so.WriteOnlyMapped['CommentTopic'] = so.relationship(back_populates='topic', cascade='all, delete-orphan', passive_deletes=True)

    def __repr__(self):
        return f'<Topic {self.title}>'


class CommentTopic(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(3000))
    timestamp: so.Mapped[datetime] = so.mapped_column(index=True, default=lambda: datetime.now(timezone.utc))
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id, ondelete='CASCADE'), index=True)
    topic_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(ForumTopic.id, ondelete='CASCADE'), index=True)

    author: so.Mapped[User] = so.relationship(back_populates='comments')
    topic: so.Mapped[ForumTopic] = so.relationship(back_populates='comments')

class MyProjects(db.Model):
    id: so.Mapped[int] = so.mapped_column(primary_key=True)
    name: so.Mapped[str] = so.mapped_column(sa.String(64), index=True, unique=True)
    body: so.Mapped[str] = so.mapped_column(sa.String(3000))