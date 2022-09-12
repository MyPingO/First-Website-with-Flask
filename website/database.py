from website import db
from flask_login import UserMixin

class YoutubeLinks(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    link = db.Column(db.String(300), nullable=False)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable = False)
    username = db.Column(db.String(150), unique=True, nullable = False)
    password = db.Column(db.String(150), nullable = False)
    links = db.relationship('YoutubeLinks', backref='user')