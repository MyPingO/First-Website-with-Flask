from asyncio.windows_events import NULL
from flask import render_template, request, flash, redirect, url_for
from website import create_app
from website import db
from website.database import Teacher, Classroom, Student, Test
from werkzeug.security import generate_password_hash, check_password_hash

# import traceback
# import re
# from pytube import Playlist
# import youtube_dl

app = create_app()

@app.route('/', methods = ['GET', 'POST'])
def home():
    data = request.form
    print(data)
    if request.method == 'POST':
        pass
    return render_template('home.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        print(request.form)
        teacher = Teacher.query.filter_by(email=request.form["email"]).first()
        if teacher:
            if check_password_hash(teacher.password, request.form["password"]):
                flash(f"Logged in successfully! Welcome back {teacher.username}.", category="success")
                return redirect(url_for("home"))
            else:
                flash("Incorrect password.", category="error")
        else:
            flash("Email does not exist.", category="error")

    return render_template("login.html")


def check_sign_up_details(email, username, password, confirm_password) -> bool:
    if email and username and password and confirm_password:
            symbols = set("!@#$%^&*()_+-=[]{};:,./<>?")

            if len(email) < 4:
                flash("Email must be greater than 3 characters.", category="error")
            if len(username) < 2:
                flash("Username must be greater than 1 character.", category="error")
            if len(password) < 5:
                flash("Password must be greater than 4 characters.", category="error")
                return False
            else:
                valid_details = True
                if (
                    any(c.isdigit() for c in password) == False 
                    or any(c.isupper() for c in password) == False
                    or any(c.islower() for c in password) == False
                    or any(c in symbols for c in password) == False
                ):
                    flash(
                        "Password must contain at least one Uppercase letter, one Lowercase letter, one Number, and one Symbol.",
                        category="error",
                    )
                    return False
                if password != confirm_password:
                    flash("Passwords don't match.", category="error")
                    valid_details = False
                if Teacher.query.filter_by(email=email).first() != None:
                    flash("Email already exists.", category="error")
                    valid_details = False
                if Teacher.query.filter_by(username=username).first() != None:
                    flash("Username already exists.", category="error")
                    valid_details = False
                return valid_details
    else:
        flash("Please fill out all fields.", category="error")
    return False


@app.route("/sign-up", methods=["GET", "POST"])
def sign_up():
    data = request.form
    valid_sign_up_details = False
    print(data)
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm-password"]
        valid_sign_up_details = check_sign_up_details(email, username, password, confirm_password)

        if valid_sign_up_details:
            new_teacher = Teacher(email=email, username=username, password=generate_password_hash(password, method="sha256"))
            db.session.add(new_teacher)
            db.session.commit()
            flash(f"Account created! Welcome, {username}.", category="success")

    return redirect(url_for('home')) if valid_sign_up_details else render_template("sign-up.html")

if __name__ == '__main__':
    app.run(debug=True, port = 25565)
