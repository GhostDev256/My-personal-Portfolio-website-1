from urllib.parse import urlsplit
from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
import sqlalchemy as sa
from app import application, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, FollowToggleForm, ReviewForm, CreateTopicForm, CommentForm
from app.models import User, ReviewsMessage, ForumTopic, CommentTopic, MyProjects
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta
import io


@application.route('/')
@application.route('/index')
def index():
    return render_template('index.html', title='Главная страница')


@application.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()

    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        
        if user.is_banned:
            flash('Ваш аккаунт заблокирован.', 'error') 
            return redirect(url_for('login'))
        
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')

        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('index')

        return redirect(next_page)
    
    return render_template('login.html', title='Вход', form=form)


@application.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@application.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = RegistrationForm()

    if form.validate_on_submit():
        if form.username.data == 'admin':
            user = User(username=form.username.data, email=form.email.data, is_admin=True)
        else:
            user = User(username=form.username.data, email=form.email.data)
            
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    
    return render_template('register.html', title='Регистрация', form=form)


@application.route('/about', methods=['GET', 'POST'])
def about():
    return render_template('about.html', title='Регистрация')


@application.route('/projects', methods=['GET', 'POST'])
def projects():
    myprojects = db.session.scalars(sa.select(MyProjects)).all()
    return render_template('projects.html', title='Регистрация', myprojects=myprojects)


@application.route('/reviews', methods=['GET', 'POST'])
def reviews():
    form = ReviewForm()
    reviews = db.session.scalars(sa.select(ReviewsMessage)).all()
    if form.validate_on_submit():
        try:
            if form.username.data:

                review = ReviewsMessage(user_id=current_user.id, timestamp=datetime.now(timezone.utc), 
                                        body=form.text.data, username_message=form.username.data)
            else:
                review = ReviewsMessage(user_id=current_user.id, timestamp=datetime.now(timezone.utc), 
                                        body=form.text.data)
                
            db.session.add(review)
            db.session.commit()
            
            flash('Отзыв оставлен!')
            return redirect(url_for('reviews'))
        except Exception as e: 
            db.session.rollback() 
            flash(f'При изменении данных произошла ошибка: {e}', 'error')
    
    elif request.method == 'GET':
        if not current_user.is_authenticated:
            form.username.data = 'Анонимус'
        else:
            form.username.data = current_user.username

    return render_template('reviews.html', title='Регистрация', form=form, reviews=reviews)


@application.route('/price', methods=['GET', 'POST'])
def price():
    return render_template('price.html', title='Регистрация')


@application.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()


@application.route('/profile/<username>', methods=['GET', 'POST'])
@login_required
def profile(username):
    user = db.first_or_404(sa.select(User).where(User.username == username))

    is_own_profile = current_user.is_authenticated and current_user == user
    show_follow_button = current_user.is_authenticated and not is_own_profile

    edit_form = None
    follow_form = None 
    is_following = False 

    if is_own_profile:
        edit_form = EditProfileForm(current_user.username)
        if edit_form.validate_on_submit():
            try:
                if edit_form.avatar.data:
                     current_user.avatar_data = io.BytesIO(edit_form.avatar.data.read()).read()

                current_user.about_me = edit_form.about_me.data
                current_user.username = edit_form.username.data

                db.session.commit()
                flash('Изменения приняты успешно!', 'message')
            except Exception as e:
                db.session.rollback()
                flash(f'При изменении данных произошла ошибка: {e}', 'error')
            return redirect(url_for('profile', username=current_user.username))

        elif request.method == 'GET':
            edit_form.username.data = current_user.username
            edit_form.about_me.data = current_user.about_me

    elif show_follow_button: 
        follow_form = FollowToggleForm()
        is_following = current_user.is_following(user)

    online_threshold_seconds = 120 
    is_online = False 
    if user.last_seen:
         time_difference = datetime.utcnow() - user.last_seen
         is_online = time_difference < timedelta(seconds=online_threshold_seconds)

    return render_template(
        'profile.html',
        title=f'Профиль пользователя {user.username}',
        user=user, 
        is_online=is_online,
        edit_form=edit_form, 
        follow_form=follow_form, 
        is_following=is_following 
    )


@application.route('/forum', methods=['GET', 'POST'])
@login_required 
def forum():
    filter_by = request.args.get('filter')
    active_filter = 'all'

    if filter_by == 'subscribed' and current_user.is_authenticated:
        topics_query = current_user.followed_topics_query()
        active_filter = 'subscribed'
    else:
        topics_query = sa.select(ForumTopic)

    topics = db.session.scalars(topics_query.order_by(ForumTopic.timestamp.desc())).all()

    subscribed_users = []
    if current_user.is_authenticated:
        subscribed_users = db.session.scalars(current_user.followed.select()).all()

    return render_template(
        'forum.html',
        title='Форум',
        topics=topics,
        active_filter=active_filter, 
        subscribed_users=subscribed_users
    )

@application.route('/search_topics', methods=['GET'])
@login_required 
def search_topics():
    query = request.args.get('q')

    if not query:
        return redirect(url_for('forum'))

    search_results = db.session.scalars(
        sa.select(ForumTopic)
        .where(
            sa.or_(
                ForumTopic.title.ilike(f'%{query}%'), 
                ForumTopic.body.ilike(f'%{query}%')   
            )
        )
        .order_by(ForumTopic.timestamp.desc()) 
    ).all()

    subscribed_users = []
    if current_user.is_authenticated:
        subscribed_users = db.session.scalars(current_user.followed.select()).all()

    return render_template(
        'forum.html', 
        title=f'Результаты поиска: "{query}"', 
        topics=search_results, 
        search_query=query,
        subscribed_users=subscribed_users 
    )

@application.route('/create_topic', methods=['GET', 'POST'])
@login_required 
def create_topic():
    form = CreateTopicForm()

    if form.validate_on_submit():
        try:
            topic = ForumTopic(
                title=form.title.data,
                body=form.body.data,
                author=current_user 
            )
            db.session.add(topic)
            db.session.commit()
            flash('Новая тема создана!', 'message')
            return redirect(url_for('view_topic', topic_id=topic.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Произошла ошибка при создании темы: {e}', 'error')

    return render_template('create_topic.html', title='Создать тему', form=form)

@application.route('/view_topic/<int:topic_id>', methods=['GET', 'POST'])
@login_required
def view_topic(topic_id):
    topic = db.first_or_404(sa.select(ForumTopic).where(ForumTopic.id == topic_id))

    form = CommentForm()

    if form.validate_on_submit():
        if current_user.is_authenticated:
            try:
                comment = CommentTopic(
                    body=form.body.data,
                    author=current_user, 
                    topic=topic
                )
                db.session.add(comment) 
                db.session.commit()

                flash('Ваш комментарий добавлен!', 'message') 
                return redirect(url_for('view_topic', topic_id=topic.id) + '#comments')

            except Exception as e:
                 db.session.rollback()
                 flash(f'Произошла ошибка при добавлении комментария: {e}', 'error')
        else:
            flash('Чтобы оставить комментарий, пожалуйста, войдите.', 'error')
            return redirect(url_for('login'))

    comments = db.session.scalars(
        sa.select(CommentTopic)
        .where(CommentTopic.topic_id == topic.id)
        .order_by(CommentTopic.timestamp.asc()) 
    ).all()

    return render_template(
        'view_topic.html',
        title=topic.title,
        topic=topic,
        comments=comments,
        form=form 
    )

@application.route('/follow/<username>', methods=['POST'])
@login_required 
def follow(username):
    form = FollowToggleForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(f'Пользователь {username} не найден.', 'error')
            return redirect(url_for('index')) 

        if user == current_user:
            flash('Вы не можете подписаться на самого себя!', 'warning')
            return redirect(url_for('profile', username=username))

        current_user.follow(user)
        db.session.commit()
        flash(f'Вы подписались на пользователя {username}!', 'message')

    else:
        flash('Произошла ошибка при подписке.', 'error')

    return redirect(url_for('profile', username=username))


@application.route('/unfollow/<username>', methods=['POST'])
@login_required 
def unfollow(username):
    form = FollowToggleForm() 
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.username == username))
        if user is None:
            flash(f'Пользователь {username} не найден.', 'error')
            return redirect(url_for('index')) 

        if user == current_user:
            flash('Вы не можете отписаться от самого себя!', 'warning')
            return redirect(url_for('profile', username=username))

        current_user.unfollow(user) 
        db.session.commit()
        flash(f'Вы отписались от пользователя {username}.', 'message')
    else:
        flash('Произошла ошибка при отписке.', 'error')

    return redirect(url_for('profile', username=username))