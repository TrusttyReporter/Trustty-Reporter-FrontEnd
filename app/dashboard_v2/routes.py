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
from flask import current_app, render_template, redirect, url_for, request, session, jsonify, Response, render_template_string, make_response
from flask_login import current_user, login_required
from flask import stream_with_context, current_app
from app.config import config
from app.models import Local_users, User_reports, User_chats, User_credits
from app import db, oauth, login_manager, mail
#from flaskext.markdown import Markdown
from werkzeug.utils import secure_filename
from langserve import RemoteRunnable
from app.dashboard_v2 import dashboard_v2_bp
from .utils import handle_post_request, get_checkpointer_response_from_api,get_chat_response,generate_chat_id,render_error,update_credits_session
from .lemonsqueezy_utils import SimpleLemonSqueezy
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from celery.result import AsyncResult
from flask_moment import moment
import hashlib
import hmac
import re
from bs4 import BeautifulSoup
import math
from datetime import datetime, timezone
from flask_sse import sse


main_url = os.environ.get('TRUSTTY_REPORTER_API_END_POINT') or "https://reporting-tool-api-test.onrender.com"
api_key= os.environ.get('TRUSTTY_REPORTER_API_KEY') or "24d7f9b5-8325-47cd-9800-5cae89248e8b"

# Initialize SimpleLemonSqueezy with your API key
lemon_api_key=os.environ.get("LEMONSQUEEZY_API_KEY")
if not lemon_api_key:
    raise ValueError("LEMONSQUEEZY_API_KEY is not set in the environment variables")
webhook_secret=os.getenv('LEMON_SQUEEZY_WEBHOOK_SECRET') or "supersecret"
lemon_squeezy = SimpleLemonSqueezy(api_key=lemon_api_key,webhook_secret=webhook_secret)

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

def get_user_reports(page_num):
    # Get the current user's ID
    user_id = current_user.id
    # Fetch reports using the static method
    reports = User_reports.get_reports_by_user_id(user_id,page_num)
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

def update_session_credits_webhook(user_id):
    """
    Update credits in the user's session stored in Redis and notify client
    """
    print("Starting credit update from webhook")
    try:
        # Get user's session from Redis
        session_interface = current_app.session_interface
        user = Local_users.query.get(user_id)
        print(user.id)
        
        if user:
            # Get all session keys from Redis that belong to this user
            prefix = f"session:"
            all_sessions = session_interface.redis.keys(f"{prefix}*")
            
            for session_key in all_sessions:
                session_data = session_interface.redis.get(session_key)
                if session_data:
                    session_dict = session_interface.serializer.loads(session_data)
                    
                    # Check if this session belongs to our user
                    if session_dict.get('_user_id') == str(user_id):
                        # Get the channel_id from the session
                        channel_id = session_dict.get('channel_id')
                        print(channel_id)
                        
                        # Update credits in session
                        available_credits = user.get_available_credits()
                        session_dict['credits_available'] = "Unlimited" if available_credits == float('inf') else str(available_credits)
                        print(session_dict['credits_available'])
                        if session_dict['credits_available'] == "Unlimited":
                            session_dict['customer_portal_url'] = user.get_customer_portal_url
                        else:
                            session_dict['customer_portal_url'] = None
                            
                        # Save updated session back to Redis
                        session_interface.redis.setex(
                            session_key,
                            current_app.permanent_session_lifetime.total_seconds(),
                            session_interface.serializer.dumps(session_dict)
                        )
                        
                        # Send SSE event using the channel_id from session
                        if channel_id:
                            sse.publish({"type": "reload"}, channel=channel_id)
            
    except Exception as e:
        print(f"Error updating session credits: {str(e)}")


@dashboard_v2_bp.route('/', methods=['GET', 'POST'])
@dashboard_v2_bp.route('/<int:page>', methods=['GET', 'POST'])
@login_required
def index(page=1):
    user_id = current_user.id
    # Get credits information using the user method
    available_credits = current_user.get_available_credits()
    session['credits_available'] = "Unlimited" if available_credits == float('inf') else str(available_credits)
    session['customer_portal_url'] = None
    if session['credits_available'] == "Unlimited":
        session['customer_portal_url']= current_user.get_customer_portal_url
    report_count = User_reports.get_report_count_by_user_id(user_id)
    session['total_report_count'] = report_count
    reports_per_page = current_app.config['REPORTS_PER_PAGE']
    print(reports_per_page)
    total_pages = math.ceil(report_count / reports_per_page)
    # Ensure page is within valid range
    page = max(1, min(page, total_pages))
    print(current_user.user_email)
    channel_id = get_or_create_channel_id()
    
    print(channel_id)

    template = 'dashboard_v2-home-new.html' if report_count == 0 else 'dashboard_v2-home.html'
    return render_template(template, 
                           username=current_user.first_name, 
                           current_user_channel=channel_id, 
                           total_pages=total_pages, 
                           current_page=page, 
                           reports_per_page=reports_per_page, 
                           credits_available= session['credits_available'],
                           customer_portal_url= session['customer_portal_url'])

@dashboard_v2_bp.route('/submit-report', methods=['GET', 'POST'])
@login_required
def submit_report():
    if not current_user.can_use_tool():
        error = 'Not enough credits available. Please purchase credits or subscribe.'
        return render_error(error)
    if request.method == 'POST':
        if not current_user.deduct_credit():
            error = 'Error processing credits. Please try again.'
            return render_error(error)
        update_credits_session()
        return handle_post_request(main_url, api_key)
    return render_template('dashboard_v2-input.html', 
                           username=current_user.first_name, 
                           credits_available= session['credits_available'],
                           customer_portal_url= session['customer_portal_url'])

@dashboard_v2_bp.route('/reports', methods=['GET', 'POST'])
def get_reports():
    # This is where you would typically fetch data from a database
    page_num = request.args.get('page',1,type=int)
    reports = get_user_reports(page_num)
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
                            html_report_status = html_report_status,
                            credits_available= session['credits_available'],
                            customer_portal_url= session['customer_portal_url'])
    except:
        return render_template('dashboard_v2-logs.html', 
                            username=current_user.first_name,
                            credits_available= session['credits_available'],
                            customer_portal_url= session['customer_portal_url'])

@dashboard_v2_bp.route('/chat_report/<report_id>')
@login_required
def chat_report(report_id):
    chat = User_chats.query.filter_by(thread_id=report_id).first()
    if not chat:
        new_chat = User_chats(user_id=current_user.id, 
                                        thread_id=report_id, 
                                        chat_id=generate_chat_id(),)
        db.session.add(new_chat)
        db.session.commit()
    response_json = get_checkpointer_response_from_api(main_url, api_key, report_id)
    html_report = response_json['answer']['channel_values']['messages'][-1]['content']
    # Escape </script> tags
    escaped_report = html_report.replace("</script>",r"<\/script>")
    add_to_chat_script = r"""<script>
        document.addEventListener('selectionchange', function() {
            const selection = window.getSelection();
            if (selection.toString().trim() !== '') {
                const range = selection.getRangeAt(0);
                const rect = range.getBoundingClientRect();
                window.parent.postMessage({
                    type: 'textSelected',
                    text: selection.toString().trim(),
                    rect: {
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height: rect.height
                    }
                }, '*');
            }
        });
    <\/script>"""
    body_close_pos = escaped_report.find("</body>")
    if body_close_pos != -1:
        escaped_report = escaped_report[:body_close_pos] + add_to_chat_script + escaped_report[body_close_pos:]
    return render_template('dashboard_v2-edit.html',
                           username=current_user.first_name, 
                           report = escaped_report,
                           report_id = report_id,
                           credits_available= session['credits_available'],
                           customer_portal_url= session['customer_portal_url'])

@dashboard_v2_bp.route('/chatresponse', methods=['POST'])
def chat_response():
    try:
        # Get data from request body
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        query = data.get('query')
        report_id = data.get('report_id')
        
        if not query or not report_id:
            return jsonify({'error': 'Missing query or report_id'}), 400
            
        chat = User_chats.query.filter_by(thread_id=report_id).first()
        chat_id = chat.chat_id
        response = get_chat_response(main_url, api_key, query, report_id, chat_id)
        
        # Check if response is dictionary (parsed JSON)
        if isinstance(response, dict) and 'output' in response:
            try:
                # Extract text between explanation tags
                extracted_text = re.search(
                    r'<explanation>(.*?)</explanation>', 
                    response['output']['content'], 
                    re.DOTALL
                )
                if extracted_text:
                    return jsonify(extracted_text.group(1).strip())
                else:
                    return jsonify(response['output']['content'])
            except (KeyError, AttributeError) as e:
                return jsonify({'error': f'Invalid response format: {str(e)}'}), 500
        else:
            # Return the error message
            return jsonify({'message': response}), 400
            
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

#Lemon Squeezy Implementation

@dashboard_v2_bp.route('/getlsproducts')
@login_required
@async_action
async def get_ls_products():
    try:
        products = await lemon_squeezy.get_products()
        return jsonify({"products": products})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@dashboard_v2_bp.route('/checkout',methods=['POST'])
@login_required
@async_action
async def ls_checkout():
    # Create a checkout
    if request.method == 'POST':
        data = request.get_json()
        print(data)
        product_id = data.get('product_id')
        store_id = data.get('store_id')
        variants = await lemon_squeezy.get_variants(product_id)
        variant_id = variants[0]['id']
        print(variant_id)
        checkout = await lemon_squeezy.create_checkout(
            user_email = current_user.user_email,
            user_id = current_user.id,
            store_id=store_id,
            variant_id=variant_id,
        )
        checkout_url = checkout['attributes']['url']
        print(checkout_url)
        return jsonify({"checkout_url": checkout_url})

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
        user_id = event_data.get('meta', {}).get('custom_data', {}).get('user_id')
        
        if event_name == 'order_created':
            # Handle new order
            order_data = event_data.get('data', {}).get('attributes', {})
            total_amount = order_data.get('total')
            if total_amount == 500:
                credit_amount=5
            elif total_amount == 1000:
                credit_amount=10
            print(f"New order received: {order_data.get('identifier')}")
            User_credits.add_pay_as_you_go_credits(
                    user_id=int(user_id),
                    credit_amount=credit_amount
                )
            update_session_credits_webhook(user_id)  # Update session
        
        elif event_name == 'order_refunded':
            order_data = event_data.get('data', {}).get('attributes', {})
            total_amount = order_data.get('total')
            if total_amount == 500:
                credit_amount=-5
            elif total_amount == 1000:
                credit_amount=-10
            User_credits.add_pay_as_you_go_credits(
                    user_id=int(user_id),
                    credit_amount=credit_amount
                )
            update_session_credits_webhook(user_id)  # Update session

        elif event_name == 'subscription_created':
            # Handle new subscription
            subscription_data = event_data.get('data', {})
            print(f"New subscription created: {subscription_data.get('id')}")
            subscription_id = subscription_data.get('id')
            customer_portal_url = subscription_data.get('attributes', {}).get('urls', {}).get('customer_portal')
            created_at_str = subscription_data.get('attributes', {}).get('created_at').replace('Z', '+00:00')
            User_credits.add_subscription(user_id=int(user_id),
                                          subscription_id=subscription_id,
                                          customer_portal_url=customer_portal_url, 
                                          start_date=datetime.fromisoformat(created_at_str)
                                          )
            update_session_credits_webhook(user_id)  # Update session

        elif event_name == 'subscription_cancelled':
            print(event_name)
        
        elif event_name == 'subscription_resumed':
            print(event_name)

        elif event_name == 'subscription_payment_success':
            print(event_name)
            User_credits.handle_subscription_renewal(user_id=int(user_id), current_date=datetime.utcnow())
            update_session_credits_webhook(user_id)  # Update session
        
        # Add more event handlers as needed
        
        return jsonify({"status": "success"}), 200
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500