from pathlib import Path
from flask import render_template, request, flash, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user
from website import create_app, mp3_downloader
from website import db
from website.database import User, YoutubeLinks
from werkzeug.security import generate_password_hash, check_password_hash

app = create_app()

@app.route('/', methods = ['GET', 'POST'])
@login_required
def home():
    data = request.form
    print(data)
    if request.method == 'POST':
        url = data["url"]
        return mp3_downloader.downloader(url, 'website/mp3')
    return render_template('home.html', user = current_user)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        print(request.form)
        user = User.query.filter_by(email=request.form["email"]).first()
        if user:
            if check_password_hash(user.password, request.form["password"]):
                flash(f"Logged in successfully! Welcome back, {user.username}.", category="success")
                login_user(user, remember=True)
                return redirect(url_for("home"))
            else:
                flash("Incorrect password.", category="error")
        else:
            flash("Email does not exist.", category="error")

    return render_template("login.html", user = current_user)

@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

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
                if User.query.filter_by(email=email).first() != None:
                    flash("Email already exists.", category="error")
                    valid_details = False
                if User.query.filter_by(username=username).first() != None:
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
            new_user = User(email=email, username=username, password=generate_password_hash(password, method="sha256"))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash(f"Account created! Welcome, {username}.", category="success")

    return redirect(url_for('home')) if valid_sign_up_details else render_template("sign-up.html", user = current_user)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port = 25565)
