from flask import render_template, request, redirect, url_for, session, abort, flash
from flask_mail import Message
from app.auth import auth_bp
from app.models import Local_users
from app import db, oauth, login_manager, mail
from flask_login import login_user, logout_user, login_required, current_user
from .utils import send_email
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

@auth_bp.route('/resetpassword', methods=['GET', 'POST'])
def restPasswordRequest():
    session.pop('_flashes', None)
    if request.method == 'POST':
        user_email = request.form['email']
        user = Local_users.query.filter_by(user_email=user_email, auth_provider='local').first()
        if user:
            token = user.generate_reset_token()
            send_email('Reset Your Password', user_email, 'reset_password', user=user, token=token)
            flash('An email has been sent with instructions to reset your password.')
        else:
            flash('Email not found. Please enter a valid email address.')    
    return render_template("resetPasswordRequest.html")

@auth_bp.route('/reset_password/<email>/<token>', methods=['GET', 'POST'])
def reset_password(email,token):
    session.pop('_flashes', None)
    user = Local_users.verify_reset_token(email,token)
    if not user:
        error = 'Invalid or expired token.'
        return render_template("signin.html", error=error)
    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        if password != confirm_password:
            flash('Passwords do not match.')
            return render_template('reset_password.html', email=email, token=token)

        user = Local_users.verify_reset_token(email,token)
        if user:
            user.set_password(password)
            db.session.commit()
            # Expire the token after successful password reset
            #Local_users.expire_reset_token(token)
            error = 'Your password has been reset.'
            return render_template("signin.html", error=error)
        else:
            error = 'Invalid or expired token.'
            return render_template("signin.html", error=error)
    return render_template('reset_password.html', email=email, token=token)

@auth_bp.route("/google-login")
def googleLogin():
    return oauth.myApp.authorize_redirect(redirect_uri=url_for("auth.googleCallback", _external=True, _scheme='https'))

@auth_bp.route("/signin-google")
def googleCallback():
    try:
        token = oauth.myApp.authorize_access_token()
        #personDataUrl = "https://people.googleapis.com/v1/people/me?personFields=genders,birthdays"
        #personData = requests.get(personDataUrl, headers={"Authorization": f"Bearer {token['access_token']}"}).json()
        #token["personData"] = personData
        #user_name = token["userinfo"]["name"]
        #user_email = token["userinfo"]["email"]
        # Extract user information from the token
        user_info = token.get('userinfo', {})
        user_name = user_info.get('name')
        user_email = user_info.get('email')
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