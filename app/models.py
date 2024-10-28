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
from datetime import datetime, timedelta, timezone

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
    credits = db.relationship('User_credits', backref='user', lazy='dynamic')
    chats = db.relationship('User_chats', backref='user', lazy='dynamic')

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

    def get_available_credits(self):
        """Get available credits or check subscription status"""
        credits = User_credits.get_active_credits(self.id)
        if not credits:
            return 0
        if credits.credit_type == CreditType.SUBSCRIPTION:
            return float('inf') if credits.has_credits else 0
        return credits.credits_remaining if credits.has_credits else 0

    def get_customer_portal_url(self):
        """Get customer portal url"""
        credits = User_credits.get_active_credits(self.id)
        url = None
        if credits.credit_type == CreditType.SUBSCRIPTION:
            url = credits.customer_portal_url
        return url

    def can_use_tool(self):
        """Check if user has enough credits to use the tool"""
        credits = User_credits.get_active_credits(self.id)
        return credits and credits.has_credits

    def deduct_credit(self):
        """Attempt to deduct a credit"""
        credits = User_credits.get_active_credits(self.id)
        return credits.deduct_credit() if credits else False  

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
    def get_reports_by_user_id(user_id: int, page_num: int) -> List['User_reports']:
        try:
            #reports =  User_reports.query.filter_by(user_id=user_id).order_by(User_reports.created_at.desc()).all()
            reports =  User_reports.query.filter_by(user_id=user_id).order_by(User_reports.created_at.desc()).paginate(page=page_num,per_page=current_app.config['REPORTS_PER_PAGE'],error_out=False)
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
        
class User_chats(db.Model):
    __tablename__ = 'Chats'
    id = db.Column('id', db.Integer, primary_key=True)
    user_id = db.Column('user_id',db.Integer,db.ForeignKey('Users.id'), nullable = False)
    thread_id = db.Column('thread_id',db.Text, nullable=False)
    chat_id = db.Column('chat_id',db.Text,nullable=False)

class CreditType():
    FREE_TRIAL = 'free_trial'
    PAY_AS_YOU_GO = 'pay_as_you_go'
    SUBSCRIPTION = 'subscription'

class User_credits(db.Model):
    __tablename__ = 'Credits'
    id = db.Column('id', db.Integer, primary_key=True)
    created_at = db.Column('created_at',db.DateTime(timezone=True),server_default=func.now(), nullable=False)
    user_id = db.Column('user_id',db.Integer,db.ForeignKey('Users.id'), nullable = False)
    credits_remaining = db.Column('credits_remaining', db.Integer, default = CreditType.FREE_TRIAL)
    credit_type = db.Column('credit_type',db.Text, nullable = False)
    subscription_start_date = db.Column('subscription_start_date',db.DateTime(timezone=True), nullable=True)   
    subscription_end_date = db.Column('subscription_end_date',db.DateTime(timezone=True), nullable=True)
    updated_at = db.Column('updated_at',db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = db.Column('is_active',db.Boolean, nullable=False, default=True)
    subscription_id = db.Column('subscription_id',db.Text)
    customer_portal_url = db.Column('customer_portal_url',db.Text)


    def __init__(self, user_id, credits_remaining=None, credit_type=None, 
                 subscription_start_date=None, subscription_end_date=None, 
                 is_active=True, subscription_id=None,customer_portal_url=None):
        self.user_id = user_id
        self.credits_remaining = credits_remaining
        self.credit_type = credit_type
        self.subscription_start_date = subscription_start_date
        self.subscription_end_date = subscription_end_date
        self.is_active = is_active
        self.subscription_id=subscription_id
        self.customer_portal_url=customer_portal_url


    @property
    def has_credits(self):
        """Check if user has available credits or active subscription."""
        now = datetime.now(timezone.utc)
        
        if self.credit_type == CreditType.SUBSCRIPTION:
            return (self.is_active and 
                   self.subscription_start_date <= now <= self.subscription_end_date)
        
        return self.is_active and self.credits_remaining > 0

    def deduct_credit(self):
        """
        Deduct one credit if available.
        Returns:
            bool: True if credit was successfully deducted, False otherwise
        """
        if not self.has_credits:
            return False

        if self.credit_type == CreditType.SUBSCRIPTION:
            return True

        if self.credits_remaining > 0:
            self.credits_remaining -= 1
            try:
                db.session.commit()
                return True
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"Error deducting credit: {str(e)}")
                return False

        return False

    @classmethod
    def add_free_trial(cls, user_id):
        """Add free trial credits for new user. Only if user has no active credits."""
        try:
            #Check if user already has any credits
            current_credits = cls.get_active_credits(user_id)
            if current_credits:
                print(f"User {user_id} already has active credits")
                return None
                
            # Create free trial credits
            new_credits = cls(
                user_id=user_id,
                credits_remaining=5,
                credit_type=CreditType.FREE_TRIAL,
                is_active=True
            )
            db.session.add(new_credits)
            #db.session.flush()
            db.session.commit()
            return new_credits
            
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error adding free trial: {str(e)}")
            return None

    @classmethod
    def add_pay_as_you_go_credits(cls, user_id, credit_amount):
        """
        Add pay-as-you-go credits. Update existing entry or create new one.
        """
        try:
            # Get current active credits
            current_credits = cls.get_active_credits(user_id)
            
            if current_credits:
                if current_credits.credit_type == CreditType.PAY_AS_YOU_GO:
                    # Update existing pay-as-you-go credits
                    current_credits.credits_remaining += credit_amount
                else:
                    # Update existing record to new type
                    current_credits.credits_remaining = credit_amount
                    current_credits.credit_type = CreditType.PAY_AS_YOU_GO
                    current_credits.subscription_start_date = None
                    current_credits.subscription_end_date = None
                    current_credits.subscription_id = None
                    current_credits.customer_portal_url = None
                
                db.session.commit()
                return current_credits
            else:
                # Create new record if no active credits exist
                new_credits = cls(
                    user_id=user_id,
                    credits_remaining=credit_amount,
                    credit_type=CreditType.PAY_AS_YOU_GO,
                    is_active=True
                )
                db.session.add(new_credits)
                db.session.commit()
                return new_credits
    
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error adding pay-as-you-go credits: {str(e)}")
            return None

    @classmethod
    def add_subscription(cls, user_id, start_date, subscription_id=None, customer_portal_url=None):
        """
        Add subscription for user. Update existing entry or create new one.
        """
        try:
            end_date = start_date + timedelta(days=30)
            current_credits = cls.get_active_credits(user_id)
            
            if current_credits:
                # Update existing record
                current_credits.credit_type = CreditType.SUBSCRIPTION
                current_credits.credits_remaining = None
                current_credits.subscription_start_date = start_date
                current_credits.subscription_end_date = end_date
                current_credits.subscription_id = subscription_id
                current_credits.customer_portal_url = customer_portal_url
            else:
                # Create new subscription record
                current_credits = cls(
                    user_id=user_id,
                    credit_type=CreditType.SUBSCRIPTION,
                    credits_remaining=None,
                    subscription_start_date=start_date,
                    subscription_end_date=end_date,
                    is_active=True,
                    subscription_id=subscription_id,
                    customer_portal_url=customer_portal_url
                )
                db.session.add(current_credits)
                
            db.session.commit()
            return current_credits
            
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error adding subscription: {str(e)}")
            return None

    @classmethod
    def handle_subscription_renewal(cls, user_id, current_date):
        """
        Handle subscription renewal for a user.
        Updates end date to current_date + 30 days, keeps original start date.
        Args:
            user_id: The user's ID
            current_date: The current date from which to calculate new end date
        Returns:
            Updated User_credits object or None if failed
        """
        try:
            current_credits = cls.get_active_credits(user_id)
            new_end_date = current_date + timedelta(days=30)
            
            if current_credits and current_credits.credit_type == CreditType.SUBSCRIPTION:
                current_credits.subscription_end_date = new_end_date
                current_credits.is_active = True  # Ensure subscription is active
                db.session.commit()
                return current_credits
            else:
                print(f"No active subscription found for user {user_id}")
                return None
                
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error handling subscription renewal: {str(e)}")
            return None

    @staticmethod
    def get_active_credits(user_id):
        """Get current active credits record for a user."""
        return User_credits.query.filter_by(
            user_id=user_id,
            is_active=True
        ).order_by(User_credits.created_at.desc()).first()
    
    def refund_credit(self):
        """
        Refund one credit if applicable.
        Does nothing for subscription users.
        Returns:
            bool: True if credit was successfully refunded, False otherwise
        """
        try:
            if self.credit_type != CreditType.SUBSCRIPTION and self.is_active:
                self.credits_remaining += 1
                db.session.commit()
                return True
            return False
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Error refunding credit: {str(e)}")
            return False

    def __repr__(self):
        return f'<UserCredits user_id={self.user_id} type={self.credit_type}>'
