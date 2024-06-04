import requests
import tempfile
import os
import chardet
import json
import asyncio
import time
from flask import render_template, redirect, url_for, request, session, jsonify, Response
from flask_login import current_user, login_required
from flask import stream_with_context, current_app
#from flaskext.markdown import Markdown
from werkzeug.utils import secure_filename
from langserve import RemoteRunnable
from app.reportChat import reportChat_bp

main_url="https://reporting-tool-api.onrender.com"
api_key = 'ca3a94dc-dafd-4878-99a0-a86ebc386c50'  # Replace with your actual API key

@reportChat_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    return render_template('comingsoon.html')