import os
import redis
from dotenv import load_dotenv
import ssl

load_dotenv()

class Config:
    FLASK_SECRET = os.environ.get('FLASK_SECRET') or 'verysecretsecret'
    OAUTH2_CLIENT_ID = os.environ.get('OAUTH2_CLIENT_ID')
    OAUTH2_CLIENT_SECRET = os.environ.get('OAUTH2_CLIENT_SECRET')
    OAUTH2_META_URL = os.environ.get('OAUTH2_META_URL')
    FLASK_PORT = 5000
    PREFERRED_URL_SCHEME = "https"
    MAIL_SERVER = "smtp.sendgrid.net"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = "apikey"
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = "no-reply@trusttyreporter.com"
    SESSION_TYPE = "redis"
    SQLALCHEMY_POOL_SIZE = 5
    REPORTS_PER_PAGE = 10
    RECAPTCHA_SITE_KEY = os.environ.get('RECAPTCHA_SITE_KEY')  # Get this from Google reCAPTCHA admin
    RECAPTCHA_SECRET_KEY = os.environ.get('RECAPTCHA_SECRET_KEY')

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_REDIS = redis.from_url('redis://localhost:6379')
    #REDIS_URL = redis.from_url('rediss://red-cs825pq3esus73cp36ag:iyQbpNUzn5cgGHu85uu4YZpMBYB2EdXG@ohio-redis.render.com:6379')
    #SSE_REDIS_URL = 'rediss://red-cs825pq3esus73cp36ag:iyQbpNUzn5cgGHu85uu4YZpMBYB2EdXG@ohio-redis.render.com:6379'
    CHANNEL_HASH_SECRET_KEY = "secret"
    #SQLALCHEMY_DATABASE_URI = "postgresql://postgres.fnyajpzupimwtjxvuein:H3EsGihRliLpuyRF@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres.howsiamcgeqqpwmjmoph:9!P6rKThL*7UaNY@aws-0-us-east-2.pooler.supabase.com:6543/postgres"
    # SSE_REDIS_KWARGS = {
    #     "ssl": True,
    #     "ssl_cert_reqs": ssl.CERT_NONE  # Use this only if you can't provide a valid certificate
    # }

class ProductionConfig(Config):
    SESSION_REDIS = redis.from_url(os.environ.get('SESSION_REDIS'))
    #REDIS_URL = redis.from_url(os.environ.get('CELERY_BACKEND_SSE'))
    #SSE_REDIS_URL = os.environ.get('CELERY_BACKEND_SSE')
    CHANNEL_HASH_SECRET_KEY = os.environ.get('CHANNEL_HASH_SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')

config ={
    'development': DevelopmentConfig,
    'production' : ProductionConfig,
    'default' : DevelopmentConfig
}