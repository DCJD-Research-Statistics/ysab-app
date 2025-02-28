from functools import wraps
from flask import session, redirect, url_for, flash, request 
from datetime import datetime as dt
import pytz
from pymongo import MongoClient
import os
import random
# from config import db_name, mongo_uri
import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
from bson import ObjectId
import math

db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")

def is_admin(email, admin_emails=os.getenv("ADMIN_EMAILS", "").split(',')):
    return email in admin_emails

def is_deputy(email, deputy_emails=os.getenv("DEPUTY_EMAILS", "").split(',')):
    return email in deputy_emails

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_admin(session['user']['email']):
            flash('Access denied. You must be an admin to access this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def deputy_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_deputy(session['user']['email']):
            flash('Access denied. You must be a deputy to access this page.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# Protect routes that require authentication
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_timestamp():
    central_timezone = pytz.timezone('America/Chicago')
    current_time = dt.now(central_timezone)
    timestamp = current_time.strftime("%m-%d-%Y %H:%M")
    return timestamp

def get_app_num():
    app_number = random.randint(0, 999999)
    return f"{app_number:06d}"

def app_id(type='A'):
    year = dt.now().year
    application_number = get_app_num()
    project_name = request.form.get('title')
    project_abbreviation = re.sub(r'[^a-zA-Z0-9\s]', '', project_name)
    project_abbreviation = "".join(word[0] for word in project_abbreviation.split())
    # form type - A: application M: progress report mid-term F: progress report final E: external
    form_type = 'E' if type == 'E' else 'A'
    # Generate unique ID
    unique_id = f"{year}-{application_number}-{project_abbreviation}-{form_type}"
    return unique_id

def get_prog_report_num():
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]
    collection = db['progress_reports']
    # Retrieve all records from the collection
    cursor = collection.find()
    # Convert the cursor to a list of dictionaries
    records = list(cursor)
    # Create a Pandas DataFrame
    df = pd.DataFrame(records)
    cluster.close()
    return df.shape[0] + 1

def progress_report_id(report_period):
    year = dt.now().year
    application_number = get_prog_report_num()
    project_name = str(request.form.get('title'))
    project_abbreviation = re.sub(r'[^a-zA-Z0-9\s]', '', project_name)
    project_abbreviation = "".join(word[0] for word in project_abbreviation.split())
    # form type - A: application M: progress report mid-term F: progress report final
    form_type = str(report_period)
    # Generate unique ID
    unique_id = f"{year}-{application_number:03d}-{project_abbreviation}-{form_type}"
    return unique_id

def get_ext_num():
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]
    collection = db['ysab-external']
    # Retrieve all records from the collection
    cursor = collection.find()
    # Convert the cursor to a list of dictionaries
    records = list(cursor)
    # Create a Pandas DataFrame
    df = pd.DataFrame(records)
    cluster.close()
    return df.shape[0] + 1

def ext_id():
    year = dt.now().year
    application_number = get_ext_num()
    project_name = request.form.get('title')
    project_abbreviation = re.sub(r'[^a-zA-Z0-9\s]', '', project_name)
    project_abbreviation = "".join(word[0] for word in project_abbreviation.split())
    # form type - A: application M: progress report mid-term F: progress report final E: external application
    form_type = 'E'
    # Generate unique ID
    unique_id = f"{year}-{application_number:03d}-{project_abbreviation}-{form_type}"
    return unique_id

def get_cont_num():
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]
    collection = db['ysab-applications']
    # Retrieve all records from the collection
    cursor = collection.find()
    # Convert the cursor to a list of dictionaries
    records = list(cursor)
    # Create a Pandas DataFrame
    df = pd.DataFrame(records)
    cluster.close()
    return df.shape[0] + 1

def cont_id():
    year = dt.now().year
    application_number = get_cont_num()
    project_name = request.form.get('title')
    project_abbreviation = re.sub(r'[^a-zA-Z0-9\s]', '', project_name)
    project_abbreviation = "".join(word[0] for word in project_abbreviation.split())
    # form type - A: application M: progress report mid-term F: progress report final C: continuation
    form_type = 'C'
    # Generate unique ID
    unique_id = f"{year}-{application_number:03d}-{project_abbreviation}-{form_type}"
    return unique_id

def make_app_form(form_data, download_source='submission'):
    # Convert ObjectId to string if present
    if '_id' in form_data and isinstance(form_data['_id'], ObjectId):
        form_data['_id'] = str(form_data['_id'])

    # Read the HTML file
    with open(r'app/templates/html_forms/ysab-application.html', 'r', encoding="utf8") as file:
        html_content = file.read()
    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the existing h4 tag and update it with the timestamp
    if download_source == 'submission':
        h4_tag = soup.find('h4')
        if h4_tag:
            h4_tag.string = f"{get_timestamp()}"
    elif download_source == 'table':
        h4_tag = soup.find('h4')
        if h4_tag:
            h4_tag.string = f"{form_data['timestamp']}"

    # Update the value attribute of input fields based on dictionary keys
    for key, value in form_data.items():
        input_field = soup.find('input', {'id': key})
        if input_field:
            input_field['value'] = value
        select_field = soup.find('select', {'id': key})
        if select_field:  
            # Clear any previously selected option
            for option in select_field.find_all('option'):
                if 'selected' in option.attrs:
                    del option.attrs['selected']
                # Set the selected attribute for the matching option
                if option.get('value') == value:
                    option['selected'] = 'selected'
                    
        # Handle textarea fields
        textarea_field = soup.find('textarea', {'id': key})
        if textarea_field:
            # Calculate required rows for the textarea content
            cols = int(textarea_field.get('cols', 50))
            lines = value.split('\n')
            rows = 0
            for line in lines:
                rows += math.ceil(len(line) / cols)

            textarea_field.string = value
            textarea_field['rows'] = str(rows)
            
        # Handle table input fields
        table_input_field = soup.find('input', {'name': key})
        if table_input_field:
            table_input_field['value'] = value

        # Save the updated HTML content to a file
        with open(r'app/templates/html_forms/ysab-application-record.html', 'w') as file:
            file.write(str(soup))

def make_prog_form(form_data, download_source='submission'):
    # Convert ObjectId to string if present
    if '_id' in form_data and isinstance(form_data['_id'], ObjectId):
        form_data['_id'] = str(form_data['_id'])

    # Determine which template to use based on reporting period
    reporting_period = form_data.get('reporting_period', '')
    if reporting_period == 'q1':
        template_path = 'app/templates/html_forms/ysab-progress-report-qt.html'
    elif reporting_period == 'q2':
        template_path = 'app/templates/html_forms/ysab-progress-report-qt2.html'
    elif reporting_period == 'q3':
        template_path = 'app/templates/html_forms/ysab-progress-report-qt3.html'
    elif reporting_period == 'q4':
        template_path = 'app/templates/html_forms/ysab-progress-report-qt4.html'
    elif reporting_period == 'mid_year':
        template_path = 'app/templates/html_forms/ysab-progress-report-bi.html'
    elif reporting_period == 'end_year':
        template_path = 'app/templates/html_forms/ysab-progress-report-end_year.html'
    else:
        template_path = 'app/templates/html_forms/ysab-progress-report-annual.html'

    # Read the HTML file
    with open(template_path, 'r', encoding="utf8") as file:
        html_content = file.read()
    
    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the existing h4 tag and update it with the timestamp
    if download_source == 'submission':
        h4_tag = soup.find('h4')
        if h4_tag:
            h4_tag.string = f"{get_timestamp()}"
    elif download_source == 'table':
        h4_tag = soup.find('h4')
        if h4_tag:
            h4_tag.string = f"{form_data['timestamp']}"

    # Update values for form fields
    for key, value in form_data.items():
        input_field = soup.find('input', {'id': key})
        if input_field:
            input_field['value'] = value
        select_field = soup.find('select', {'id': key})
        if select_field:  
            # Clear any previously selected option
            for option in select_field.find_all('option'):
                if 'selected' in option.attrs:
                    del option.attrs['selected']
                # Set the selected attribute for the matching option
                if option.get('value') == value:
                    option['selected'] = 'selected'
                    
        # Handle textarea fields
        textarea_field = soup.find('textarea', {'id': key})
        if textarea_field:
            # Calculate required rows for the textarea content
            cols = int(textarea_field.get('cols', 50))
            lines = str(value).split('\n')
            rows = 0
            for line in lines:
                rows += math.ceil(len(line) / cols)

            textarea_field.string = str(value)
            textarea_field['rows'] = str(rows)
            
        # Handle table input fields
        table_input_field = soup.find('input', {'name': key})
        if table_input_field:
            table_input_field['value'] = value

    # Save the updated HTML content to a file
    with open('app/templates/htmlt_forms/ysab-progress-report-record.html', 'w', encoding="utf8") as file:
        file.write(str(soup))

def make_ext_form(form_data, download_source='submission'):
    # Read the HTML file
    with open(r'app/templates/html_forms/ysab-external.html', 'r', encoding="utf8") as file:
        html_content = file.read()
    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the existing h3 tag and update it with the timestamp
    if download_source == 'submission':
        h4_tag = soup.find('h4')
        if h4_tag:
            h4_tag.string = f"{get_timestamp()}"
    elif download_source == 'table':
        h4_tag = soup.find('h4')
        if h4_tag:
            h4_tag.string = f"{form_data['timestamp']}"

    # Update the value attribute of input fields based on dictionary keys
    for key, value in form_data.items():
        input_field = soup.find('input', {'id': key})
        if input_field:
            input_field['value'] = value
        select_field = soup.find('select', {'id': key})
        if select_field:  
            # Clear any previously selected option
            for option in select_field.find_all('option'):
                if 'selected' in option.attrs:
                    del option.attrs['selected']
                # Set the selected attribute for the matching option
                if option.get('value') == value:
                    option['selected'] = 'selected'
                    
        # Handle textarea fields
        textarea_field = soup.find('textarea', {'id': key})
        if textarea_field:
            textarea_field.string = value
            
        # Handle table input fields
        table_input_field = soup.find('input', {'name': key})
        if table_input_field:
            table_input_field['value'] = value

        # Save the updated HTML content to a file
        with open(r'app/templates/html_forms/ysab-external-record.html', 'w') as file:
            file.write(str(soup))

def make_cont_form(form_data):
    # Read the HTML file
    with open(r'app/templates/html_forms/ysab-continuation.html', 'r', encoding="utf8") as file:
        html_content = file.read()
    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the existing h3 tag and update it with the timestamp
    h4_tag = soup.find('h4')
    if h4_tag:
        h4_tag.string = f"{get_timestamp()}"

    # Update the value attribute of input fields based on dictionary keys
    for key, value in form_data.items():
        input_field = soup.find('input', {'id': key})
        if input_field:
            input_field['value'] = value
        select_field = soup.find('select', {'id': key})
        if select_field:  
            # Clear any previously selected option
            for option in select_field.find_all('option'):
                if 'selected' in option.attrs:
                    del option.attrs['selected']
                # Set the selected attribute for the matching option
                if option.get('value') == value:
                    option['selected'] = 'selected'
                    
        # Handle textarea fields
        textarea_field = soup.find('textarea', {'id': key})
        if textarea_field:
            textarea_field.string = value
            
        # Handle table input fields
        table_input_field = soup.find('input', {'name': key})
        if table_input_field:
            table_input_field['value'] = value

        # Save the updated HTML content to a file
        with open(r'app/templates/html/forms/ysab-continuation-record.html', 'w') as file:
            file.write(str(soup))