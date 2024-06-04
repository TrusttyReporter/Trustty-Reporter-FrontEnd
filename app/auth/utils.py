from flask import render_template, request, redirect, url_for, flash
from flask_mail import Message
from app import db, oauth, login_manager, mail

def send_email(subject, recipient, template, **kwargs):
    msg = Message(subject, recipients=[recipient])
    msg.body = render_template(f'email/{template}.txt', **kwargs)
    msg.html = render_template(f'email/{template}.html', **kwargs)
    mail.send(msg)