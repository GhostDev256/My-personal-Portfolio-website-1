from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length
import sqlalchemy as sa
from app import db
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Имя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомните меня')
    submit = SubmitField('Вход')


class EditProfileForm(FlaskForm):
    username = StringField('Имя', validators=[DataRequired()])
    about_me = TextAreaField('Обо мне', validators=[Length(min=0, max=140)])
    avatar = FileField('Выберите аватар', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    submit = SubmitField('Обновить')
    subscribe = SubmitField('Подписаться')

    def __init__(self, original_username, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = db.session.scalar(sa.select(User).where(
                User.username == self.username.data))
            if user is not None:
                raise ValidationError('Это имя пользователя уже занято.')


class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    email = StringField('Почта', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Регистрация')

    def validate_username(self, username):
        user = db.session.scalar(sa.select(User).where(User.username == username.data))
        if user is not None:
            raise ValidationError('Это имя пользователя уже занято.')

    def validate_email(self, email):
        user = db.session.scalar(sa.select(User).where(User.email == email.data))
        if user is not None:
            raise ValidationError('Данная почта уже используется.')
        

class FollowToggleForm(FlaskForm):
    submit = SubmitField('Submit')


class ReviewForm(FlaskForm):
    username = StringField('Ваш логин', validators=[DataRequired()])
    text = TextAreaField('Отзыв', validators=[Length(min=0, max=2000)])
    submit = SubmitField('Отправить')


class CreateTopicForm(FlaskForm):
    title = StringField('Заголовок темы', validators=[DataRequired(), Length(min=1, max=128)])
    body = TextAreaField('Текст первого сообщения', validators=[DataRequired(), Length(min=1, max=5000)]) 
    submit = SubmitField('Создать тему')


class CommentForm(FlaskForm):
    body = TextAreaField('Ваш комментарий', validators=[DataRequired(), Length(min=1, max=5000)]) 
    submit = SubmitField('Оставить комментарий')


class MyProjectsForm(FlaskForm): 
    name = StringField('Название проекта', validators=[DataRequired(), Length(max=64)])
    body = TextAreaField('Описание проекта', validators=[DataRequired(), Length(max=3000)])