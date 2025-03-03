import os
import tempfile
import csv
import chardet
import requests
import json
import asyncio
import aiofiles
import httpx
from werkzeug.utils import secure_filename
import openpyxl
import uuid
import pandas as pd
import kombu
from flask import render_template, request, session, redirect, url_for, jsonify, abort
from flask_login import login_required, current_user
from celery.result import AsyncResult
from celery import signature
from app import celery
from app.models import Local_users, User_reports, User_credits

async def convert_csv_to_utf8(file_path, encoding):
    """
    Convert csv to utf8 asynchronously
    """
    def _convert():
        try:
            df = pd.read_csv(file_path, sep=',', encoding=encoding, low_memory=False)
            df.to_csv(file_path, index=False, encoding='utf-8')
            return True
        except Exception as e:
            #return f"Error converting CSV to UTF-8: {str(e)}"
            return f"Error converting CSV to UTF-8:"

    return await asyncio.to_thread(_convert)

def handle_post_request(main_url, api_key):
    description = request.form['description']
    if not description:
        return handle_error_with_refund("Description is required.")
    
    resources = request.files.getlist('resources')
    if not resources:
        return handle_error_with_refund("No files were uploaded. Please upload a file and try again.")

    session['description'] = description

    with tempfile.TemporaryDirectory() as temp_dir:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            file_paths = loop.run_until_complete(process_files(resources, temp_dir))
            if isinstance(file_paths, str):  # Error occurred
                return handle_error_with_refund(file_paths)
            
            api_response = loop.run_until_complete(make_api_request(main_url, api_key, file_paths))
            if isinstance(api_response, str):  # Error occurred
                return handle_error_with_refund(api_response)
            
            #print(api_response)
            session['api_response'] = api_response
            query_id = generate_query_id()
            user_id = current_user.id
            query_text = description
            new_report = add_record_to_db(user_id, query_id, query_text)
            temp_dir_name = api_response['temp_dir_name']
            pdf_files = api_response['pdf_files']
            csv_file = api_response['csv_file']
            channel_id = session['channel_id']
            task = call_celery_task(query_text, query_id, channel_id, temp_dir_name, pdf_files, csv_file)
            User_reports.update_task_id(query_id, str(task.id))
            return redirect(url_for("dashboard_v2.index"))
        except Exception as e:
            print("Full error:", str(e))
            return handle_error_with_refund(f"An error occurred: {str(e)}")
            #return handle_error_with_refund(f"An error occurred, please try again.")
        finally:
            loop.close()

def update_credits_session():
    """Update the session with current credit information."""
    available_credits = current_user.get_available_credits()
    session['credits_available'] = "Unlimited" if available_credits == float('inf') else str(available_credits)


def handle_error_with_refund(error_message):
    """Handle error with credit refund and session update."""
    if credits := User_credits.get_active_credits(current_user.id):
        credits.refund_credit()
        update_credits_session()
    return render_error(error_message)

def render_error(message):
    return render_template('dashboard_v2-input.html', 
                           username=current_user.first_name, 
                           error_message=message,
                           credits_available= session['credits_available'],
                           customer_portal_url= session['customer_portal_url'])

async def process_files(resources, temp_dir):
    file_paths = await save_uploaded_files(resources, temp_dir)
    if isinstance(file_paths, str):  # Error occurred
        return file_paths
    
    processed_paths = await process_excel_files(file_paths)
    if isinstance(processed_paths, str):  # Error occurred
        return processed_paths
    
    error = await convert_csv_encodings(processed_paths)
    if error:
        return error
    
    return processed_paths

async def save_uploaded_files(resources, temp_dir):
    file_paths = []
    for resource in resources:
        if not resource.filename:
            return "No file selected for upload. Please upload a file and try again."
        filename = secure_filename(resource.filename)
        file_path = os.path.join(temp_dir, filename)
        async with aiofiles.open(file_path, 'wb') as async_file:
            await async_file.write(resource.read())
        file_paths.append(file_path)
    return file_paths

async def process_excel_files(file_paths):
    tasks = []
    for file_path in file_paths:
        _, file_extension = os.path.splitext(file_path)
        if file_extension.lower() in ['.xls', '.xlsx']:
            tasks.append(asyncio.create_task(convert_excel_to_csv(file_path)))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    new_file_paths = file_paths.copy()
    
    for result in results:
        if isinstance(result, Exception):
            return f"An error occurred while converting Excel file to CSV: {str(result)}"
        if result:
            new_file_paths.append(result)
    
    return new_file_paths

async def convert_excel_to_csv(file_path):
    def _convert():
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
        csv_file_path = os.path.splitext(file_path)[0] + '.csv'
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
            writer = csv.writer(csv_file)
            for row in sheet.iter_rows(values_only=True):
                writer.writerow(row)
        return csv_file_path

    return await asyncio.to_thread(_convert)

async def convert_csv_encodings(file_paths):
    tasks = []
    for file_path in file_paths:
        _, file_extension = os.path.splitext(file_path)
        if file_extension.lower() == '.csv':
            tasks.append(asyncio.create_task(convert_csv_encoding(file_path)))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    errors = []
    for result in results:
        if isinstance(result, Exception) or result is not True:
            errors.append(str(result))
    
    if errors:
        return f"Errors occurred while converting CSV file encoding: {'; '.join(errors)}"
    
    return None  # Indicates success (no errors)

async def convert_csv_encoding(file_path):
    try:
        async with aiofiles.open(file_path, 'rb') as file:
            content = await file.read()
            encoding = chardet.detect(content)['encoding']
        
        if encoding != 'utf-8':
            result = await convert_csv_to_utf8(file_path, encoding)
            if result is not True:
                return result  # This will be an error message if conversion failed
        return True
    except Exception as e:
        #return f"Error in convert_csv_encoding: {str(e)}"
        return f"Error in convert_csv_encoding."

async def make_api_request(main_url, api_key, file_paths):
    api_url = f"{main_url}/api/v1/upload/"
    headers = {
        'accept': 'application/json',
        'X-API-KEY': api_key
    }
    files = await prepare_files_for_api(file_paths)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, headers=headers, files=files)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            #return f"Oops! Something went wrong while processing your request: {str(e)}"
            return f"Oops! Something went wrong while processing your request, please try again!"
        except (KeyError, json.JSONDecodeError) as e:
            #return f"Hmm, looks like we received an unexpected response: {str(e)}"
            return f"Hmm, looks like we received an unexpected response, we apologise. We would appreciate if you could report the issue at support@trusttyreporter.com"

async def prepare_files_for_api(file_paths):
    files = []
    for file_path in file_paths:
        async with aiofiles.open(file_path, 'rb') as file:
            content = await file.read()
            files.append(('files', (os.path.basename(file_path), content, 'application/octet-stream')))
    return files

def generate_query_id():
    thread_uuid = uuid.uuid4()
    return str(thread_uuid)

def add_record_to_db(user_id, thread_id, query_text):
    new_report = User_reports.add_report(user_id, thread_id, query_text)
    return new_report

def call_celery_task(query_text: str, query_id: str,channel_id: str, temp_dir_name, pdf_files, csv_file):
    try:
        task = celery.send_task('generate_report', 
                            args=[query_text, query_id, channel_id, temp_dir_name, pdf_files, csv_file],
                            queue='high_priority',
                            time_limit=3600,
                            soft_time_limit=3500)
        #print(f"Celery Task ID : {task.id}")
        return task
    except kombu.exceptions.OperationalError as e:
        print(f"Celery task creation failed: {e}")
        raise

def get_task_status(task_id):
    result = celery.AsyncResult(task_id)
    return result

def get_checkpointer_response_from_api(main_url, api_key, report_id):
    url = f"{main_url}/api/v1/getresponse"
    headers = {
        'accept': 'application/json',
        "X-API-KEY": api_key
    }
    payload = {
        "thread_id": str(report_id),
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        return response.json()
    except httpx.TimeoutException as e:
        print(f"Timeout error occurred: {e}")
        abort(504, description="Request timed out while fetching data")  # 504 is Gateway Timeout
    except httpx.HTTPError as e:
        # Log the error here if you have a logging system set up
        print(f"HTTP error occurred: {e}")
        abort(500, description="Error fetching data from API")
    except json.JSONDecodeError as e:
        print(f"JSON decode error occurred: {e}")
        abort(500, description="Error parsing API response")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        abort(500, description="An unexpected error occurred")

def generate_chat_id():
    thread_uuid = uuid.uuid4()
    return str(thread_uuid)


def get_chat_response(main_url, api_key, query, report_id, chat_id):
    url = f"{main_url}/api/v1/reportchat/invoke/"
    headers = {
        'accept': 'application/json',
        "X-API-KEY": api_key
    }
    inputs = {
        "query": query,
        "thread_id": chat_id,
        "report_id": report_id,
    }
    
    try:
        response = requests.post(url, headers=headers, json={"input": inputs})
        
        # Check response status
        response.raise_for_status()
        
        return response.json()

    except requests.exceptions.RequestException as e:
        # Handle different types of request errors
        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 429:
            return "Rate limit exceeded. Please try again later."
        elif isinstance(e, requests.exceptions.ConnectionError):
            return "Unable to connect to the server. Please check your connection."
        else:
            return "You have exhausted your chat length limit. Please start a new chat."
            
    except json.JSONDecodeError:
        return "Invalid response from server"