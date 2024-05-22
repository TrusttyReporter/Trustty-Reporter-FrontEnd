from app import db
from flask_login import UserMixin
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