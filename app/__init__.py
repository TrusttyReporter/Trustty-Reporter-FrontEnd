from flask import Flask, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_session import Session
from authlib.integrations.flask_client import OAuth
from api_analytics.flask import add_middleware
from app.config import appConf
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()
session = Session()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config')

    add_middleware(app, '319ce073-e486-45de-91cc-c42ac0a0ba4d')  # Add middleware

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.signin'
    oauth.init_app(app)
    session.init_app(app)

    oauth.register(
        "myApp",
        client_id=appConf.get("OAUTH2_CLIENT_ID"),
        client_secret=appConf.get("OAUTH2_CLIENT_SECRET"),
        client_kwargs={
            "scope": "openid profile email https://www.googleapis.com/auth/user.birthday.read https://www.googleapis.com/auth/user.gender.read",
            # 'code_challenge_method': 'S256'  # enable PKCE
        },
        server_metadata_url=f'{appConf.get("OAUTH2_META_URL")}',
    )

    @app.route('/')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.index"))
        return render_template('landing.html')
    
    @app.route('/example/sales-report')
    def salesReport():
        return render_template('SalesReport.html')
    
    @app.route('/example/freedom-index-report')
    def freedomIndexReport():
        return render_template('FreedomIndexReport.html')
    
    @app.route('/example/google-play-store-report')
    def googlePlayStoreReport():
        return render_template('GooglePlayStoreReport.html')

    from app.auth import auth_bp
    from app.dashboard import dashboard_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    return app