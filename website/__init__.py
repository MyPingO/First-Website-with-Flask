from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from flask_login import LoginManager

db = SQLAlchemy()
database_name ="gradebook.db"

def create_app():
    created_app = Flask(__name__)
    created_app.config['SECRET_KEY'] = 'MyPing0'
    created_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_name}'
    created_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(created_app)

    # from .visuals import visuals
    # from .authentication import authentication

    # created_app.register_blueprint(visuals, url_prefix='/')
    # created_app.register_blueprint(authentication, url_prefix='/')

    from .database import User, YoutubeLinks

    create_database_if_not_exist(created_app)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(created_app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    return created_app


def create_database_if_not_exist(created_app):
    if not Path('website/' + database_name).exists():
        db.create_all(app=created_app)
        print('Created Database!')