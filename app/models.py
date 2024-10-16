from flask import current_app
from app import db
from flask_login import UserMixin
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import func
from typing import List
from app.config import config
import bcrypt
import json

class Local_users(UserMixin, db.Model):
    __tablename__ = 'Users'
    id = db.Column('id', db.Integer, primary_key=True)
    first_name = db.Column('first_name', db.Text, nullable=False)
    last_name = db.Column('last_name', db.Text, nullable=False)
    user_email = db.Column('user_email', db.Text, unique=True, nullable=False)
    password = db.Column('password', db.Text, nullable=True)
    auth_provider = db.Column('auth_provider', db.Text, nullable=False, default='local')

    # Relationship with User_reports
    reports = db.relationship('User_reports', backref='user', lazy='dynamic')
    #credits = db.relationship('User_credits', backref='user', lazy='dynamic')

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
        s = Serializer(current_app.config['FLASK_SECRET'].encode('utf-8'), salt=self.password.encode('utf-8'))
        return s.dumps({'reset': self.id})

    @staticmethod
    def verify_reset_token(email, token):
        user = Local_users.query.filter_by(user_email=email).first()

        if user:
            s = Serializer(current_app.config['FLASK_SECRET'].encode('utf-8'), salt=user.password.encode('utf-8'))
            
            try:
                data = s.loads(token, max_age=1800)  # Token expires in 30 minutes
                return user
            except:
                return None
        
        return None
    
    @staticmethod
    def expire_reset_token(token):
        s = Serializer(current_app.config['FLASK_SECRET'].encode('utf-8'), salt=bcrypt.gensalt())
        try:
            data = s.loads(token, max_age=0)
        except:
            pass
        token = 'EXPIRED_TOKEN'
        return token
    

class User_reports(db.Model):
    __tablename__ = 'Reports'
    id = db.Column('id', db.Integer, primary_key=True)
    created_at = db.Column('created_at',db.DateTime(timezone=True),server_default=func.now(), nullable=False)
    user_id = db.Column('user_id',db.Integer,db.ForeignKey('Users.id'), nullable = False)
    thread_id = db.Column('thread_id',db.Text, nullable=False)
    query_text = db.Column('query_text',db.Text,nullable=False)
    task_id = db.Column('task_id', db.Text, nullable=True)
    status = db.Column('status',db.Text, nullable=True)

    def __init__(self, user_id, thread_id, query_text, task_id=None, status=None):
        self.user_id = user_id
        self.thread_id = thread_id
        self.query_text = query_text
        self.task_id = task_id
        self.status = status

    def __repr__(self):
        return f'<User_reports {self.id}: User {self.user_id}, Thread {self.thread_id}, Task {self.task_id}, Status {self.status}>'
    
    @staticmethod
    def get_reports_by_user_id(user_id: int) -> List['User_reports']:
        try:
            reports =  User_reports.query.filter_by(user_id=user_id).order_by(User_reports.created_at.desc()).all()
        except Exception as e:
            print(e)
            reports = None
        
        return reports
    
    @staticmethod
    def get_report_count_by_user_id(user_id: int) -> int:
        try:
            count = User_reports.query.filter_by(user_id=user_id).count()
        except Exception as e:
            print(e)
            count = 0
        return count
    
    @staticmethod
    def add_report(user_id, thread_id, query_text, task_id=None, status=None):
        try:
            new_report = User_reports(user_id=user_id, 
                                      thread_id=thread_id, 
                                      query_text=query_text, 
                                      task_id=task_id, 
                                      status=status)
            db.session.add(new_report)
            db.session.commit()
            return new_report
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error adding report: {str(e)}")
            return None
        
    @staticmethod
    def update_task_id(thread_id, new_task_id):
        try:
            report = User_reports.query.filter_by(thread_id=thread_id).first()
            if report:
                report.task_id = new_task_id
                db.session.commit()
                return report
            else:
                print(f"No report found with thread_id {thread_id}")
                return None
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error updating task_id: {str(e)}")
            return None
        

# class credit_orders(db.Model):
#     _tablename__ = 'Orders'
#     id = db.Column('id')

# class User_credits(db.Model):
#     __tablename__ = 'Credits'
#     id = db.Column('id', db.Integer, primary_key=True)
#     user_id = db.Column('user_id',db.Integer,db.ForeignKey('Users.id'), nullable = False)
#     credits_remaining = db.Column('credits_remaining',db.Integer,nullable = False)
#     subscription_status = db.Column('status',db.Text,nullable=False)
#     subscription_start_date = db.Column('start_date',db.DateTime(timezone=True), nullable=False)
#     subscription_end_date = db.Column('end_date',db.DateTime(timezone=True), nullable=False)