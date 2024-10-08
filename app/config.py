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

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_REDIS = redis.from_url('redis://localhost:6379')
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres.fnyajpzupimwtjxvuein:H3EsGihRliLpuyRF@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"
    CELERY_BROKER = "rediss://red-cruis6rqf0us73epeu10:TocPDg7slIXSAp82yFDiY4eHZYdP0T82@ohio-redis.render.com:6379"#?ssl_cert_reqs=CERT_NONE"
    CELERY_BACKEND = "rediss://red-cruis6rqf0us73epeu10:TocPDg7slIXSAp82yFDiY4eHZYdP0T82@ohio-redis.render.com:6379"#?ssl_cert_reqs=CERT_NONE"
    CELERY_BROKER_USE_SSL = {
        'ssl_cert_reqs': ssl.CERT_NONE,
        'ssl_ca_certs': None,
    }

class ProductionConfig(Config):
    SESSION_REDIS = redis.from_url(os.environ.get('SESSION_REDIS'))
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI')
    CELERY_BROKER = os.environ.get('CELERY_BROKER')
    CELERY_BACKEND = os.environ.get('CELERY_BACKEND')

config ={
    'development': DevelopmentConfig,
    'production' : ProductionConfig,
    'default' : DevelopmentConfig
}