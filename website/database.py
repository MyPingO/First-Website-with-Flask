from website import db
from flask_login import UserMixin

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'))
    test_number = db.Column(db.Integer, nullable = False)
    grade = db.Column(db.Integer, nullable = False)
    letter_grade = db.Column(db.String(2), nullable = False)
    date_taken = db.Column(db.DateTime, nullable = False)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'))
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    average = db.Column(db.Integer, nullable=False)
    letter_average = db.Column(db.String(2), nullable=False)
    tests = db.relationship('Classroom', backref='student')

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'))
    name = db.Column(db.String(100), nullable=False)
    teacher = db.Column(db.String(100), nullable=False)
    students = db.relationship('Teacher', backref='classroom')

class Teacher(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable = False)
    username = db.Column(db.String(150), unique=True, nullable = False)
    password = db.Column(db.String(150), nullable = False)