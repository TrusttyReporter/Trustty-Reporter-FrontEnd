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
from .utils import handle_post_request
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from celery.result import AsyncResult


main_url = os.environ.get('TRUSTTY_REPORTER_API_END_POINT') or "https://reporting-tool-api-test.onrender.com"
api_key= os.environ.get('TRUSTTY_REPORTER_API_KEY') or "24d7f9b5-8325-47cd-9800-5cae89248e8b"


@dashboard_v2_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    user_id = current_user.id
    report_count = User_reports.get_report_count_by_user_id(user_id)
    session['total_report_count'] = report_count

    template = 'dashboard_v2-home-new.html' if report_count == 0 else 'dashboard_v2-home.html'
    return render_template(template, username=current_user.first_name)

@dashboard_v2_bp.route('/submit-report', methods=['GET', 'POST'])
@login_required
def submit_report():
    if request.method == 'POST':
        return handle_post_request(main_url, api_key)
    return render_template('dashboard_v2-input.html', username=current_user.first_name)


def get_user_reports():
    # Get the current user's ID
    user_id = current_user.id
    print(user_id)

    # Fetch reports using the static method
    reports = User_reports.get_reports_by_user_id(user_id)

    print(reports)

    # Convert reports to a list of dictionaries
    reports_data = []
    for report in reports:
        reports_data.append({
            'id': report.thread_id,
            #'created_at': report.created_at.isoformat(),
            #'thread_id': report.thread_id,
            'name': report.query_text,
            #'task_id': report.task_id,
            'status': "success" if report.status is None else report.status
        })
    return reports_data


@dashboard_v2_bp.route('/reports', methods=['GET', 'POST'])
def get_reports():
    # This is where you would typically fetch data from a database
    reports = get_user_reports()
    print(reports)
    # reports = [
    # {"id": 1, "name": "Monthly Sales", "status": "success"},
    # {"id": 2, "name": "Inventory", "status": "processing"},
    # {"id": 3, "name": "Customer Feedback dddddddddddddddddddddddddddddddddddd", "status": "failed"},
    # {"id": 4, "name": "Employee Performance", "status": "success"},
    # {"id": 5, "name": "Website Traffic", "status": "processing"}
    # ]
    return jsonify(reports)