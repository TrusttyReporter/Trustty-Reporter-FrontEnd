from app import db
from flask_login import UserMixin
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from app.config import appConf
import bcrypt

class Local_users(UserMixin, db.Model):
    __tablename__ = 'Users'
    id = db.Column('id', db.Integer, primary_key=True)
    first_name = db.Column('first_name', db.Text, nullable=False)
    last_name = db.Column('last_name', db.Text, nullable=False)
    user_email = db.Column('user_email', db.Text, unique=True, nullable=False)
    password = db.Column('password', db.Text, nullable=True)
    auth_provider = db.Column('auth_provider', db.Text, nullable=False, default='local')

    def __init__(self, first_name, last_name, user_email, password=None, auth_provider='local'):
        self.first_name = first_name
        self.last_name = last_name
        self.user_email = user_email
        if password:
            self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        self.auth_provider = auth_provider

    def __repr__(self):
        return f"<Local_users '{self.user_email}'>"

    def check_password(self, password):
        if self.password:
            return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))
        return False
    
    def set_password(self, password):
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def generate_reset_token(self, expiration=300):
        s = Serializer(appConf.get('FLASK_SECRET').encode('utf-8'), salt=self.password.encode('utf-8'))
        return s.dumps({'reset': self.id})

    @staticmethod
    def verify_reset_token(email, token):
        user = Local_users.query.filter_by(user_email=email).first()

        if user:
            s = Serializer(appConf.get('FLASK_SECRET').encode('utf-8'), salt=user.password.encode('utf-8'))
            
            try:
                data = s.loads(token, max_age=1800)  # Token expires in 30 minutes
                return user
            except:
                return None
        
        return None
    
    @staticmethod
    def expire_reset_token(token):
        s = Serializer(appConf.get('FLASK_SECRET').encode('utf-8'), salt=bcrypt.gensalt())
        try:
            data = s.loads(token, max_age=0)
        except:
            pass
        token = 'EXPIRED_TOKEN'
        return token