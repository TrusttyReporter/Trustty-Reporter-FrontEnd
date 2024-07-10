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
from flask import render_template, redirect, url_for, request, session, jsonify, Response, render_template_string
from flask_login import current_user, login_required
from flask import stream_with_context, current_app
#from flaskext.markdown import Markdown
from werkzeug.utils import secure_filename
from langserve import RemoteRunnable
from app.dashboard import dashboard_bp
from .utils import convert_csv_to_utf8
from requests.exceptions import RequestException
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

main_url="https://reporting-tool-api.onrender.com"
api_key = 'ca3a94dc-dafd-4878-99a0-a86ebc386c50'  # Replace with your actual API key

@dashboard_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    error_message = None  # Initialize error_message variable

    # Handle form submission
    if request.method == 'POST':
        description = request.form['description']
        if not description:
            error_message = "Description is required."
            return render_template('report-inputs.html', username=current_user.first_name, error_message=error_message)
        resources = request.files.getlist('resources')
        print(f"Resource: {resources}")
        session['description'] = description

        if resources:
            # Create a temporary directory to store the uploaded files
            with tempfile.TemporaryDirectory() as temp_dir:
                # Save each uploaded file to the temporary directory
                file_paths = []
                for resource in resources:
                    if resource.filename:
                        filename = secure_filename(resource.filename)
                        print(f"FileName: {filename}")
                        file_path = os.path.join(temp_dir, filename)
                        resource.save(file_path)
                        file_paths.append(file_path)
                    else:
                        error_message = "No file selected for upload. Please upload a file and try again."
                        return render_template('report-inputs.html', username=current_user.first_name, error_message=error_message)
                    
                for file_path in file_paths:
                    _, file_extension = os.path.splitext(file_path)
                    if file_extension.lower() in ['.xls', '.xlsx']:
                        try:
                            # Load the Excel file
                            workbook = openpyxl.load_workbook(file_path)
                            sheet = workbook.active
                            # Convert the Excel sheet to CSV
                            csv_file_path = os.path.splitext(file_path)[0] + '.csv'
                            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
                                writer = csv.writer(csv_file)
                                for row in sheet.iter_rows(values_only=True):
                                    writer.writerow(row)
                            file_paths.append(csv_file_path)
                        except Exception as e:
                            print(e)
                            error_message = "An error occurred while converting Excel file to CSV. Unable to process the file."
                            return render_template('report-inputs.html', username=current_user.first_name, error_message=error_message)

                # Check the encoding of CSV files and convert to UTF-8 if necessary
                for file_path in file_paths:
                    _, file_extension = os.path.splitext(file_path)
                    if file_extension.lower() == '.csv':
                        with open(file_path, 'rb') as file:
                            file_content = file.read()
                            encoding = chardet.detect(file_content)['encoding']
                            print(encoding)
                            if encoding != 'utf-8':
                                try:
                                    convert_csv_to_utf8(file_path, encoding)
                                except Exception as e:
                                    print("e")
                                    error_message = "An error occurred while converting CSV file encoding. Unable to process CSV due to unsupported encoding."
                                    return render_template('report-inputs.html', username=current_user.first_name, error_message=error_message)

                # Prepare the files for the API request
                files = []
                for file_path in file_paths:
                    with open(file_path, 'rb') as file:
                        files.append(('files', (os.path.basename(file_path), file.read(), 'application/octet-stream')))

                # Make the API request
                api_url = f"{main_url}/api/v1/upload/"  # Replace with your API endpoint
                headers = {
                    'accept': 'application/json',
                    'X-API-KEY': api_key
                }
                try:
                    response = requests.post(api_url, headers=headers, files=files)
                    response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes

                    # API request successful
                    session['api_response'] = response.json()
                    print(response.json())
                    return redirect(url_for("dashboard.result"))
                except requests.exceptions.RequestException as e:
                    print(e)
                    error_message = "Oops! Something went wrong while processing your request. Please try again later."
                except (KeyError, json.JSONDecodeError) as e:
                    print(e)
                    error_message = "Hmm, looks like we received an unexpected response. Don't worry, our team is on it!"

        else:
            error_message = "No files were uploaded. Please upload a file and try again."

    return render_template('report-inputs.html', username=current_user.first_name, error_message=error_message)
    
@dashboard_bp.route('/result')
@login_required
def result():
    description = session['description']
    return render_template('report-results.html',username = current_user.first_name, description = description)

@dashboard_bp.route('/api/result')
@login_required
def api_result():
    # Retrieve the API response from the session
    api_response = session.get('api_response')
    print(api_response)
    url = f"{main_url}/api/v1/preprocessing/"
    payload = {
        "tmp_dir": api_response['temp_dir_name'],
        "pdf_files": api_response['pdf_files'],
        "csv_file": api_response['csv_file']
    }
    headers = {
        'accept': 'application/json',
        "X-API-KEY": api_key
    }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10), retry=retry_if_exception_type(RequestException))
    def make_api_request():
        response = requests.request("POST", url, headers=headers, json=payload, timeout=5*60)
        response.raise_for_status()  # This will raise an exception for HTTP error codes
        return response.json()


    #response = requests.request("POST", url, headers=headers, json=payload, timeout=5*60)

    #response_json = json.loads(response.text)
    try:
        response_json = make_api_request()
    
        #if response.status_code == 200:
        doc_chunks = response_json['doc_chunks']
        session['csv_summary'] = response_json['csv_summary']
        session['doc_summaries'] = [] if response_json['doc_chunks'] == "" else [f"### Document Name: {source}\n\n{doc_chunks[source]['doc_summary']}" for source in doc_chunks]
        session['event_stream_status'] = True
        # Create a dictionary with the extracted values
        result_data = {
            'doc_summaries': session['doc_summaries'],
            'csv_summary': "" if session['csv_summary'] == "" else session['csv_summary']['summary']
        }
        #print(result_data)
        return jsonify(result_data)
        #else:
            #return jsonify("No API response found.")
    except Exception as e:
        return jsonify(f"An unexpected error occurred: {str(e)}")


@dashboard_bp.route('/stream')
@login_required
def stream():
    
    event_stream_status = session.get('event_stream_status')
    if event_stream_status == True:
        api_response = session.get('api_response')
        doc_summaries = session.get('doc_summaries')
        csv_summary = session.get('csv_summary')
        description = session.get('description')
        inputs = {
            "query": description,
            "tmp_dir": api_response['temp_dir_name'],
            "csv_file": "" if csv_summary == "" else api_response['csv_file'],
            "summary_list": doc_summaries,
            "csv_summary": "" if csv_summary == "" else csv_summary['summary'],
            "doc_num": 0 if doc_summaries == [] else len(doc_summaries),
            "data_num": 0 if csv_summary == "" else 1
        }
        url = f"{main_url}/api/v1/report/"
        headers = {"X-API-KEY": api_key}
        remote_runnable = RemoteRunnable(url,headers=headers)        

        @stream_with_context
        def event_stream():
            with current_app.app_context():
                for chunk in remote_runnable.stream(input=inputs):
                    if chunk.get('html_report'):
                        print('complete')
                        yield f"data: {json.dumps({'chunk': {'complete': True, 'html_report': chunk['html_report']}})}\n\n"

                    else:
                        #print(chunk, end='|', flush=True)
                        yield f"data: {json.dumps({'chunk':chunk})}\n\n"
                
                print("Sending complete message")  # Log the complete message   
        
        session['event_stream_status'] = False
        return Response(event_stream(), mimetype='text/event-stream')
    else:
        return "data: {json.dumps({'complete:True})}\n\n"
    
@dashboard_bp.route('/report')
@login_required
def report():
    #print(session['html_report'])
    html_report = session['html_report']
    jinja_content = """{% from "download_buttons.jinja" import download_buttons %}
    {{ download_buttons() }}"""
    head_close_pos = html_report.find("</head>")
    if head_close_pos != -1:
        html_report = html_report[:head_close_pos] + jinja_content + html_report[head_close_pos:]
    return render_template_string(html_report)

@dashboard_bp.route('/report-input', methods=['GET', 'POST'])
@login_required
def report_input():
    if request.method == 'POST':
        session['html_report']=request.json.get('html_report', 'No report')
        session['final_report']=request.json.get('final_report','No report')
        #print(session['html_report'])
        #print(f"FINAL REPORT IN MARKDOWN: {session['final_report']}")
        return 'OK'
    else:
        return 'Method Not Allowed', 405

@dashboard_bp.route('/report/edit', methods=['GET', 'POST'])
@login_required
def report_edit():
    final_report = session.get('final_report', '')
    #print(final_report)
    return render_template('report-edits.html', username = current_user.first_name, report = final_report)

@dashboard_bp.route('/report/generate_report', methods=['GET', 'POST'])
@login_required
def report_new():
    if request.method == 'POST':
        final_report = request.json.get('report', 'No report')
        url = f"{main_url}/api/v1/htmlreport/invoke/"
        headers = {
            'accept': 'application/json',
            "X-API-KEY": api_key
        }
        response = requests.request("POST", url, headers=headers, json={"input": final_report})
        if response.status_code == 200:
            response_json = json.loads(response.text)
            session['new_html_report'] = response_json['output']['content']
            #print(session['new_html_report'])
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "No API response found."})
        
@dashboard_bp.route('/new_report')
@login_required
def new_report():
    new_html_report = session['new_html_report']
    jinja_content = """{% from "download_buttons.jinja" import download_buttons %}
    {{ download_buttons() }}"""
    head_close_pos = new_html_report.find("</head>")
    if head_close_pos != -1:
        new_html_report = new_html_report[:head_close_pos] + jinja_content + new_html_report[head_close_pos:]
    return render_template_string(new_html_report)