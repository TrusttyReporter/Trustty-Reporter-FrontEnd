import os
from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_session import Session
from flask_mail import Mail, Message
from flask_moment import Moment
from celery import Celery
from authlib.integrations.flask_client import OAuth
from api_analytics.flask import add_middleware
from app.config import config
from dotenv import load_dotenv
import ssl
from flask_sse import sse
import redis

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()
session = Session()
mail = Mail()
moment = Moment()

# Initialize Celery
celery = Celery(__name__, 
                broker= os.environ.get('CELERY_BROKER') or 'rediss://red-cs825pq3esus73cp36ag:iyQbpNUzn5cgGHu85uu4YZpMBYB2EdXG@ohio-redis.render.com:6379?ssl_cert_reqs=CERT_NONE', 
                backend=os.environ.get('CELERY_BACKEND') or 'rediss://red-cs825pq3esus73cp36ag:iyQbpNUzn5cgGHu85uu4YZpMBYB2EdXG@ohio-redis.render.com:6379?ssl_cert_reqs=CERT_NONE'
                )

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    add_middleware(app, os.environ.get('ANALYTICS_API_KEY'))  # Add middleware

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.signin'
    oauth.init_app(app)
    session.init_app(app)
    moment.init_app(app)

    app.config["REDIS_URL"] ='rediss://red-cs825pq3esus73cp36ag:iyQbpNUzn5cgGHu85uu4YZpMBYB2EdXG@ohio-redis.render.com:6379'
    #app.config["REDIS_URL"] = os.environ.get('CELERY_BACKEND') or 'rediss://red-cs825pq3esus73cp36ag:iyQbpNUzn5cgGHu85uu4YZpMBYB2EdXG@ohio-redis.render.com:6379'
    # Initialize Redis connection
    #redis_client = redis.Redis.from_url(os.environ.get('CELERY_BACKEND', 'redis://'))
    
    # Configure SSE with Redis
    app.config["SSE_REDIS_URL"] = 'rediss://red-cs825pq3esus73cp36ag:iyQbpNUzn5cgGHu85uu4YZpMBYB2EdXG@ohio-redis.render.com:6379'
    #app.config["SSE_REDIS_URL"] = os.environ.get('CELERY_BACKEND') or 'rediss://red-cs825pq3esus73cp36ag:iyQbpNUzn5cgGHu85uu4YZpMBYB2EdXG@ohio-redis.render.com:6379'
    app.config["SSE_REDIS_KWARGS"] = {
        "ssl": True,
        "ssl_cert_reqs": ssl.CERT_NONE  # Use this only if you can't provide a valid certificate
    }
    app.register_blueprint(sse, url_prefix='/stream')
    
    # # Configure Celery
    # celery.conf.update(
    #     broker=app.config['CELERY_BROKER'],
    #     backend=app.config['CELERY_BACKEND'],
    # )

    # app.config['MAIL_SERVER'] = appConf.get('MAIL_SERVER')
    # app.config['MAIL_PORT'] = appConf.get('MAIL_PORT')
    # app.config['MAIL_USE_TLS'] = appConf.get('MAIL_USE_TLS')
    # app.config['MAIL_USERNAME'] = appConf.get('MAIL_USERNAME')
    # app.config['MAIL_PASSWORD'] = appConf.get('MAIL_PASSWORD')
    # app.config['MAIL_DEFAULT_SENDER'] = appConf.get('MAIL_DEFAULT_SENDER')

    mail.init_app(app)

    # oauth.register(
    #     "myApp",
    #     client_id=appConf.get("OAUTH2_CLIENT_ID"),
    #     client_secret=appConf.get("OAUTH2_CLIENT_SECRET"),
    #     client_kwargs={
    #         "scope": "openid profile email",
    #         #https://www.googleapis.com/auth/user.birthday.read https://www.googleapis.com/auth/user.gender.read",
    #         # 'code_challenge_method': 'S256'  # enable PKCE
    #     },
    #     server_metadata_url=f'{appConf.get("OAUTH2_META_URL")}',
    # )
    
    oauth.register(
        "myApp",
        client_id=app.config["OAUTH2_CLIENT_ID"],
        client_secret=app.config["OAUTH2_CLIENT_SECRET"],
        client_kwargs={
            "scope": "openid profile email",
        },
        server_metadata_url=f'{app.config["OAUTH2_META_URL"]}',
    )

    @app.route('/')
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard_v2.index"))
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
    
    @app.route('/terms-and-conditions')
    def terms_and_conditions():
        return render_template('terms_and_conditions.html')
    
    @app.route('/privacy-policy')
    def privacy_policy():
        return render_template('privacy_policy.html')
    
    @app.route('/cookie-policy')
    def cookie_policy():
        return render_template('cookie_policy.html')
    
    @app.errorhandler(Exception)
    def handle_error(error):
        if hasattr(error, 'code'):
            error_code = error.code
        else:
            error_code = 500
        return render_template('error.html', error_code=error_code), error_code

    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.dashboard_v2 import dashboard_v2_bp
    from app.reportChat import reportChat_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(dashboard_v2_bp, url_prefix='/dashboardv2')
    app.register_blueprint(reportChat_bp, url_prefix='/chat')

    return app