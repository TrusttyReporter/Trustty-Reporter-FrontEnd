import requests
import tempfile
import os
import chardet
import json
import asyncio
import time
import openpyxl
import csv
import html
from flask import current_app, render_template, redirect, url_for, request, session, jsonify, Response, render_template_string
from flask_login import current_user, login_required
from flask import stream_with_context, current_app
from app.config import config
from app.models import Local_users, User_reports
#from flaskext.markdown import Markdown
from werkzeug.utils import secure_filename
from langserve import RemoteRunnable
from app.dashboard_v2 import dashboard_v2_bp
from .utils import handle_post_request, get_checkpointer_response_from_api
from .lemonsqueezy_utils import SimpleLemonSqueezy
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from celery.result import AsyncResult
from flask_moment import moment
import hashlib
import hmac


main_url = os.environ.get('TRUSTTY_REPORTER_API_END_POINT') or "https://reporting-tool-api-test.onrender.com"
api_key= os.environ.get('TRUSTTY_REPORTER_API_KEY') or "24d7f9b5-8325-47cd-9800-5cae89248e8b"

# Initialize SimpleLemonSqueezy with your API key
api_key=os.environ.get("LEMONSQUEEZY_API_KEY")
if not api_key:
    raise ValueError("LEMONSQUEEZY_API_KEY is not set in the environment variables")
webhook_secret=os.getenv('LEMON_SQUEEZY_WEBHOOK_SECRET') or "supersecret"
lemon_squeezy = SimpleLemonSqueezy(api_key=api_key,webhook_secret=webhook_secret)

def async_action(f):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    wrapper.__name__ = f.__name__
    return wrapper

def get_user_reports():
    # Get the current user's ID
    user_id = current_user.id
    # Fetch reports using the static method
    reports = User_reports.get_reports_by_user_id(user_id)
    # Convert reports to a list of dictionaries
    reports_data = []
    for report in reports:
        reports_data.append({
            'id': report.thread_id,
            'date': report.created_at.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z',
            'name': report.query_text,
            'task_id': report.task_id,
            'status': "unknown" if report.status is None else report.status
        })
    return reports_data

def hash_channel_id(channel_id):
    secret_key = current_app.config['CHANNEL_HASH_SECRET_KEY']
    # Convert secret_key to bytes if it's a string
    if isinstance(secret_key, str):
        secret_key = secret_key.encode('utf-8')   
    # Convert channel_id to bytes if it's a string
    if isinstance(channel_id, str):
        channel_id = channel_id.encode('utf-8')
    return hmac.new(secret_key, channel_id, hashlib.sha256).hexdigest()

def verify_channel_id_hash(channel_id, hashed_id):
    return hmac.compare_digest(hash_channel_id(channel_id), hashed_id)

def get_or_create_channel_id() -> str:
    if 'channel_id' not in session:
        session['channel_id'] = hash_channel_id(current_user.user_email)
    return session['channel_id']

@dashboard_v2_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user_id = current_user.id
    report_count = User_reports.get_report_count_by_user_id(user_id)
    session['total_report_count'] = report_count

    print(current_user.user_email)
    channel_id = get_or_create_channel_id()
    
    print(channel_id)

    template = 'dashboard_v2-home-new.html' if report_count == 0 else 'dashboard_v2-home.html'
    return render_template(template, username=current_user.first_name, current_user_channel=channel_id)

@dashboard_v2_bp.route('/submit-report', methods=['GET', 'POST'])
@login_required
def submit_report():
    if request.method == 'POST':
        return handle_post_request(main_url, api_key)
    return render_template('dashboard_v2-input.html', username=current_user.first_name)

@dashboard_v2_bp.route('/reports', methods=['GET', 'POST'])
def get_reports():
    # This is where you would typically fetch data from a database
    reports = get_user_reports()
    #print(reports)
    return jsonify(reports)

@dashboard_v2_bp.route('/view_report/<report_id>')
@login_required
def view_report(report_id):
    response_json = get_checkpointer_response_from_api(main_url, api_key, report_id)
    html_report = response_json['answer']['channel_values']['messages'][-1]['content']
    jinja_content = """{% from "download_buttons.jinja" import download_buttons %}
    {{ download_buttons() }}"""
    head_close_pos = html_report.find("</head>")
    if head_close_pos != -1:
        html_report = html_report[:head_close_pos] + jinja_content + html_report[head_close_pos:]
    return render_template_string(html_report)

@dashboard_v2_bp.route('/view_logs/<report_id>')
@login_required
def view_logs(report_id):
    try:
        response_json = get_checkpointer_response_from_api(main_url, api_key, report_id)
        report_description = response_json.get('answer', {}).get('channel_values', {}).get('messages', [])[0]['content']
        print(report_description)
        document_summaries = response_json.get('answer', {}).get('channel_values', {}).get('documents')
        csv_summaries = response_json.get('answer', {}).get('channel_values', {}).get('data')
        generating_plan = True if document_summaries is not None and csv_summaries is not None else False
        plan = response_json.get('answer', {}).get('channel_values', {}).get('original_plan')
        past_steps = response_json.get('answer', {}).get('channel_values', {}).get('past_steps')
        prelimary_report_status = True if response_json.get('answer', {}).get('channel_versions', {}).get('Report Writer') else False
        print(prelimary_report_status)
        html_report_status = True if response_json.get('answer', {}).get('channel_versions', {}).get('HTML Report Convertor') else False
        print(html_report_status)

        if prelimary_report_status == True and html_report_status == True:
            messages = response_json.get('answer', {}).get('channel_values', {}).get('messages', [])
            preliminary_report = messages[-2]['content']
        elif prelimary_report_status == True and html_report_status == False:
            messages = response_json.get('answer', {}).get('channel_values', {}).get('messages', [])
            preliminary_report = messages[-1]['content']
        else:
            preliminary_report = None
        
        return render_template('dashboard_v2-logs.html', 
                            username=current_user.first_name,
                            report_id = report_id,
                            report_description = report_description, 
                            document_summaries=document_summaries,
                            csv_summaries=csv_summaries,
                            generating_plan = generating_plan,
                            plan=plan,
                            past_steps=past_steps,
                            preliminary_report=preliminary_report,
                            html_report_status = html_report_status)
    except:
        return render_template('dashboard_v2-logs.html', 
                            username=current_user.first_name)

@dashboard_v2_bp.route('/edit_report/<report_id>')
@login_required
def edit_report(report_id):
    return "<h1>Hello World</h1>"

@dashboard_v2_bp.route('/getlsproducts')
@login_required
@async_action
async def get_ls_products():
    try:
        products = await lemon_squeezy.get_products()
        return jsonify({"products": products})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@dashboard_v2_bp.route('/webhook', methods=['POST'])
@async_action
async def handle_webhook():
    # Get the signature from the headers
    signature = request.headers.get('X-Signature')
    
    if not signature:
        return jsonify({"error": "No signature provided"}), 400

    # Get the raw payload
    payload = request.data

    try:
        # Process the webhook
        event_data = await lemon_squeezy.process_webhook(payload, signature)
        
        # Handle different event types
        event_name = event_data.get('meta', {}).get('event_name')
        
        if event_name == 'order_created':
            # Handle new order
            order_data = event_data.get('data', {}).get('attributes', {})
            print(f"New order received: {order_data.get('identifier')}")
            # Add your custom logic here
        
        elif event_name == 'subscription_created':
            # Handle new subscription
            subscription_data = event_data.get('data', {}).get('attributes', {})
            print(f"New subscription created: {subscription_data.get('id')}")
            # Add your custom logic here
        
        # Add more event handlers as needed
        
        return jsonify({"status": "success"}), 200
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500