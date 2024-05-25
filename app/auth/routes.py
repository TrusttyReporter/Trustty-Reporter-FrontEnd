from flask import render_template, request, redirect, url_for, session, abort
from app.auth import auth_bp
from app.models import Local_users
from app import db, oauth, login_manager
from flask_login import login_user, logout_user, login_required, current_user
import requests
import os

@login_manager.user_loader
def loader_user(user_id):
    if user_id is None:
        return None

    try:
        user_id = int(user_id)
    except ValueError:
        return None

    user = Local_users.query.get(user_id)
    return user

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    else:
        return redirect(url_for("auth.signin"))

@auth_bp.route('/signin', methods=["GET", "POST"])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if not email:
            error = "Please enter your email address."
            return render_template("signin.html", error=error)
        
        if not password:
            error = "Please enter your password."
            return render_template("signin.html", error=error)
        
        user = Local_users.query.filter_by(user_email=email).first()
        
        if user:
            if user.check_password(password):
                login_user(user)
                return redirect(url_for("dashboard.index"))
            else:
                error = "Invalid password. Please try again."
                return render_template("signin.html", error=error)
        else:
            error = "No account found with the provided email address."
            return render_template("signin.html", error=error)
    
    return render_template("signin.html")

@auth_bp.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == 'POST':
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        email = request.form['email']
        password = request.form['password']

        # Check if the email is already registered
        existing_user = Local_users.query.filter_by(user_email=email).first()
        if existing_user:
            error = "Email is already registered. Please use a different email."
            return render_template("signup.html", error=error)

        # Check if any required fields are empty
        if not first_name or not last_name or not email or not password:
            error = "Please fill in all the required fields."
            return render_template("signup.html", error=error)

        # Create a new user
        new_user = Local_users(first_name=first_name, last_name=last_name, user_email=email, password=password, auth_provider='local')
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("auth.signin"))

    return render_template("signup.html")

@auth_bp.route('/resetpassword')
def restpassword():
    return render_template("resetpassword.html")

@auth_bp.route("/google-login")
def googleLogin():
    return oauth.myApp.authorize_redirect(redirect_uri=url_for("auth.googleCallback", _external=True))

@auth_bp.route("/signin-google")
def googleCallback():
    try:
        token = oauth.myApp.authorize_access_token()
        personDataUrl = "https://people.googleapis.com/v1/people/me?personFields=genders,birthdays"
        personData = requests.get(personDataUrl, headers={"Authorization": f"Bearer {token['access_token']}"}).json()
        token["personData"] = personData
        user_name = token["userinfo"]["name"]
        user_email = token["userinfo"]["email"]
        user = Local_users.query.filter_by(user_email=user_email).first()
        if not user:
            new_user = Local_users(first_name=user_name.split()[0], last_name=' '.join(user_name.split()[1:]), user_email=user_email, auth_provider='google')
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
        else:
            login_user(user)
        print("Session data:", session)
        return redirect(url_for("auth.index"))
    except:
        return redirect(url_for('auth.signin'))

@auth_bp.route("/signout")
@login_required
def signout():
    logout_user()
    session.pop("user", None)
    return redirect(url_for("auth.signin"))