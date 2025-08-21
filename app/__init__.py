from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_moment import Moment
import logging

from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from logging.handlers import RotatingFileHandler
import os

application = Flask(__name__)

application.config.from_object(Config)

db = SQLAlchemy(application)
migrate = Migrate(application, db)

login = LoginManager(application)
login.login_view = 'login'

moment = Moment(application)

if not application.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter( '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    application.logger.addHandler(file_handler)

    application.logger.setLevel(logging.INFO)
    application.logger.info('Microblog startup')

from app import routes, models, errors
from app.models import User, ReviewsMessage, ForumTopic, CommentTopic, MyProjects
from app.forms import MyProjectsForm
from flask import render_template, redirect, url_for, request
from flask_login import current_user

admin = Admin(application, url='/admin', name='Моя Админка', template_mode='bootstrap3') 

class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

    column_exclude_list = ['password_hash', 'avatar_data']
    form_excluded_columns = [
        'password_hash',
        'avatar_data',  
        'followed',    
        'followers',    
        'reviews',      
        'topics',      
        'comments'      
    ]

    form_columns = [
        'is_admin',
        'is_banned'
    ]


class OtherModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))


class MyProjectsModelView(ModelView):
    form = MyProjectsForm

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('login', next=request.url))

admin.add_view(SecureModelView(User, db.session))
admin.add_view(OtherModelView(ForumTopic, db.session))
admin.add_view(OtherModelView(CommentTopic, db.session))
admin.add_view(OtherModelView(ReviewsMessage, db.session))
admin.add_view(MyProjectsModelView(MyProjects, db.session))

