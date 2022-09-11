# from flask import Blueprint, render_template, request, flash, redirect, url_for

# authentication = Blueprint("authentication", __name__)

# symbols = set("!@#$%^&*()_+-=[]{};:,./<>?")


# @authentication.route("/login", methods=["GET", "POST"])
# def login():
#     if request.method == "POST":
#         pass

#     return render_template("login.html")


# @authentication.route("/sign-up", methods=["GET", "POST"])
# def sign_up():
#     data = request.form
#     print(data)
#     account_created = False
#     if request.method == "POST":
#         email = request.form.get("email")
#         username = request.form.get("username")
#         password = request.form.get("password")
#         confirm_password = request.form.get("confirm-password")

#         if email and username and password and confirm_password:
#             if len(email) < 4:
#                 flash("Email must be greater than 3 characters.", category="error")
#             if len(username) < 2:
#                 flash("Username must be greater than 1 character.", category="error")
#             if len(password) < 5:
#                 flash("Password must be greater than 4 characters.", category="error")
#             else:
#                 if (
#                     any(c.isdigit() for c in password) == False 
#                     or any(c.isupper() for c in password) == False
#                     or any(c.islower() for c in password) == False
#                     or any(c in symbols for c in password) == False
#                 ):
#                     flash(
#                         "Password must contain at least one Uppercase letter, one Lowercase letter, one Number, and one Symbol.",
#                         category="error",
#                     )
#                 if password != confirm_password:
#                     flash("Passwords don't match.", category="error")
#                 else:
#                     account_created = True
#                     flash("Account created!", category="success")
#         else:
#             flash("Please fill out all fields.", category="error")

#     return redirect(url_for('authentication.login')) if account_created else render_template("sign-up.html")
