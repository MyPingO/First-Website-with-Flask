from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path

db = SQLAlchemy()
database_name ="gradebook.db"

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'MyPing0'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{database_name}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # from .visuals import visuals
    # from .authentication import authentication

    # app.register_blueprint(visuals, url_prefix='/')
    # app.register_blueprint(authentication, url_prefix='/')

    from .database import Teacher, Classroom, Student, Test

    create_database_if_not_exist(app)

    return app


def create_database_if_not_exist(app):
    if not Path('website/' + database_name).exists():
        db.create_all(app=app)
        print('Created Database!')