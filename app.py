from flask import Flask, request, render_template, jsonify, send_file, redirect, url_for, session, flash
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime as dt
import os
import pytz
import pandas as pd
import re
from bs4 import BeautifulSoup
import math
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from functools import wraps
from bson import ObjectId
import requests
from make_pdf_app import make_pdf

admin_mode_switch = False

load_dotenv() 

mongo_uri = os.getenv("MONGO_URI")
if admin_mode_switch==True:
    db_name = os.getenv("DB_NAME_DEV")
    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL_DEV") 
elif admin_mode_switch==False:
    db_name = os.getenv("DB_NAME")
    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL") 

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))

# Get admin emails from environment variable and split into a list
ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',')
DEPUTY_EMAILS = os.getenv('DEPUTY_EMAILS', '').split(',')

def get_timestamp():
    central_timezone = pytz.timezone('America/Chicago')
    current_time = dt.now(central_timezone)
    timestamp = current_time.strftime("%m-%d-%Y %H:%M")
    return timestamp

def get_app_num():
    with MongoClient(mongo_uri) as client:
        db = client[db_name]
        collection = db['ysab-applications']
        # Count all records in the collection
        count = collection.count_documents({})
        app_number = count + 1
        app_number = f"{app_number:03d}"

        # Check if app_number exists in db['metadata_applications']
        with MongoClient(mongo_uri) as client:
            db = client[db_name]
            metadata_collection = db['metadata_applications']
            existing_app = metadata_collection.find_one({'app_number': app_number})

            if existing_app:
                # If yes, set app_number to max(app_metadata.app_number) + 1
                max_app_number = metadata_collection.find_one(sort=[('app_number', -1)])['app_number'] 
                app_number = int(max_app_number) + 1
                app_number = f"{app_number:03d}" # change back to '000' format
            
    return app_number

def app_id(type='A'):
    year = dt.now().year
    application_number = get_app_num()
    project_name = request.form.get('title')
    project_abbreviation = re.sub(r'[^a-zA-Z0-9\s]', '', project_name)
    project_abbreviation = "".join(word[0] for word in project_abbreviation.split())
    # form type - A: application M: progress report mid-term F: progress report final E: external
    if type=='A':
        form_type = 'A'
    if type=='E':
        form_type = 'E'
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
    with open(r'templates/ysab-application.html', 'r', encoding="utf8") as file:
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
        with open(r'templates/ysab-application-record.html', 'w') as file:
            file.write(str(soup))

def make_prog_form(form_data, download_source='submission'):
    # Convert ObjectId to string if present
    if '_id' in form_data and isinstance(form_data['_id'], ObjectId):
        form_data['_id'] = str(form_data['_id'])

    # Determine which template to use based on reporting period
    reporting_period = form_data.get('reporting_period', '')
    if reporting_period == 'q1':
        template_path = 'templates/ysab-progress-report-qt.html'
    elif reporting_period == 'q2':
        template_path = 'templates/ysab-progress-report-qt2.html'
    elif reporting_period == 'q3':
        template_path = 'templates/ysab-progress-report-qt3.html'
    elif reporting_period == 'q4':
        template_path = 'templates/ysab-progress-report-qt4.html'
    elif reporting_period == 'mid_year':
        template_path = 'templates/ysab-progress-report-bi.html'
    elif reporting_period == 'end_year':
        template_path = 'templates/ysab-progress-report-end_year.html'
    else:
        template_path = 'templates/ysab-progress-report-annual.html'

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
    with open('templates/ysab-progress-report-record.html', 'w', encoding="utf8") as file:
        file.write(str(soup))

def make_ext_form(form_data, download_source='submission'):
    # Read the HTML file
    with open(r'templates/ysab-external.html', 'r', encoding="utf8") as file:
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
        with open(r'templates/ysab-external-record.html', 'w') as file:
            file.write(str(soup))

def make_cont_form(form_data):
    # Read the HTML file
    with open(r'templates/ysab-continuation.html', 'r', encoding="utf8") as file:
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
        with open(r'templates/ysab-continuation-record.html', 'w') as file:
            file.write(str(soup))

@app.route("/", methods=['GET', 'POST'])
def index():
    if 'user' in session:
        return render_template('landing.html', user=session['user'], admin_emails=ADMIN_EMAILS, deputy_emails=DEPUTY_EMAILS)
    return render_template('landing.html', admin_emails=ADMIN_EMAILS, deputy_emails=DEPUTY_EMAILS)

@app.route("/home", methods=['GET', 'POST'])
def home():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('home.html', 
                         user=session.get('user'),
                         admin_emails=ADMIN_EMAILS, 
                         deputy_emails=DEPUTY_EMAILS)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email').lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('signup.html')
        
        # MongoDB connection
        client = MongoClient(mongo_uri)
        db = client[db_name]
        users_collection = db['users']

        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            flash('Email already exists', 'error')
            return render_template('signup.html')

        hashed_password = generate_password_hash(password)
        new_user = {
            'name': name,
            'email': email,
            'password': hashed_password
        }
        users_collection.insert_one(new_user)
        flash('Account created successfully', 'success')

        # Log the status change in activities collection
        db['activities'].insert_one({
            'timestamp': get_timestamp(),
            'type': 'User Signup',
            'description': f'New user account created for {name} ({email})',
            'user': email
        })

        # Send Discord notification
        message = f"📩 New User Signup:\n- Name: {name}\n- Email: {email}"
        requests.post(discord_webhook_url, json={"content": message})

        return redirect(url_for('login'))
    
    # If it's a GET request, just render the signup template
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')

        # MongoDB connection
        client = MongoClient(mongo_uri)
        # main ysab database
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        users_collection = db['users']

        user = users_collection.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            session['user'] = {'name': user['name'], 'email': user['email']}
            flash('Logged in successfully', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

# Protect routes that require authentication
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def is_admin(email):
    return email in ADMIN_EMAILS

def is_deputy(email):
    return email in DEPUTY_EMAILS

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

@app.route('/my-applications')
@login_required
def my_applications(admin_mode=admin_mode_switch):
    if 'user' not in session:
        return redirect(url_for('login'))
    
    # Get admin emails list from environment variable
    admin_emails = os.getenv("ADMIN_EMAILS").split(',')

    if admin_mode==True:
        user_email = os.getenv("EMAIL")
    elif admin_mode==False: 
        user_email = session['user']['email']

    # Connect to MongoDB
    client = MongoClient(mongo_uri)

    # Choose database based on admin status
    if user_email.lower() in [email.lower() for email in admin_emails]:
        db = client[os.getenv("DB_NAME_DEV")]
    else:
        db = client[os.getenv("DB_NAME")]

    collection = db['ysab-applications']

    # Fetch applications for the current user from 'ysab' collection
    user_applications = list(collection.find(
        {'email': {'$regex': f'^{user_email}$', '$options': 'i'}},
        {'_id': 1, 'timestamp': 1, 'title': 1, 'application_status': 1}
    ))

    # Fetch applications for the current user from 'ysab-external' collection
    external_collection = db['ysab-external']
    user_external_applications = list(external_collection.find(
        {'email': {'$regex': f'^{user_email}$', '$options': 'i'}},
        {'_id': 1, 'timestamp': 1, 'title': 1, 'application_status': 1}
    ))

    # Combine both application lists
    all_applications = user_applications + user_external_applications

    if not all_applications:
        message = "No records found."
        return render_template('my_applications.html', message=message)
    
    # Format the data for the template
    applications = []
    for app in all_applications:
        # Check if the application is from user_applications or user_external_applications
        if app in user_applications:
            app_type = 'Internal Application'
        elif app in user_external_applications:
            app_type = 'External Application'
        else:
            app_type = 'Unknown Application'

        applications.append({
            'id': str(app['_id']),
            'submission_date': app['timestamp'],
            'title': app['title'],
            'type': app_type,
            'application_status': app.get('application_status', 'pending')
        })

    client.close()

    return render_template('my_applications.html', applications=applications, admin_emails=ADMIN_EMAILS, deputy_emails=DEPUTY_EMAILS)

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/application')
@login_required
def application():
    # Check if the user's email ends with 'dallascounty.org'
    if not session['user']['email'].endswith('dallascounty.org'):
        flash('Access denied. You must have a dallascounty.org email to access this page.', 'error')
        return redirect(url_for('home'))  # Redirect to home or another appropriate page
    return render_template('application.html')

@app.route('/progress-report-selection', methods=['GET'])
@login_required
def progress_report_selection(admin_mode=admin_mode_switch):
    if admin_mode==True:
        user_email = os.getenv("EMAIL")
    elif admin_mode==False: 
        user_email = session['user']['email']

    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db['ysab-applications']

    # Fetch applications for the current user
    user_applications = list(collection.find(
        {'email': {'$regex': f'^{user_email}$', '$options': 'i'}},
        {'_id': 1, 'timestamp': 1, 'title': 1, 'reporting_interval': 1}
    ))

    # Format the data for the template
    applications = []
    for app in user_applications:
        applications.append({
            'id': str(app['_id']),
            'submission_date': app['timestamp'],
            'title': app['title'],
            'type': 'Internal Application',
            'reporting_interval': app.get('reporting_interval', 'Not specified')
        })

    client.close()

    return render_template('progress_report_selection.html', applications=applications)

@app.route('/progress-report-router/<application_id>/<reporting_interval>')
@login_required
def progress_report_router(application_id, reporting_interval):
    if reporting_interval == 'Quarterly':
        return redirect(url_for('select_quarter', application_id=application_id))
    elif reporting_interval in ['Bi-annually', '>Bi-annually']:
        return redirect(url_for('select_biannual', application_id=application_id))
    elif reporting_interval in ['Annually', '>Annually']:
        return redirect(url_for('progress_report_annual', application_id=application_id))
    else:
        flash('Invalid reporting interval', 'error')
        return redirect(url_for('progress_report_selection'))

@app.route('/select-quarter/<application_id>')
@login_required
def select_quarter(application_id):
    return render_template('select_quarter.html', application_id=application_id)

@app.route('/select-biannual/<application_id>')
@login_required
def select_biannual(application_id):
    return render_template('select_biannual.html', application_id=application_id)

@app.route('/progress-report-qt/<application_id>', methods=['GET', 'POST'])
@login_required
def progress_report_qt(application_id):
    # Fetch the application details from the database based on the reporting period
    client = MongoClient(mongo_uri)
    db = client[db_name]
    reporting_period = request.form.get('reporting_period')
    
    if reporting_period == 'q1':
        collection = db['ysab-applications']
        application = collection.find_one({'_id': application_id})
    else:
        collection = db['progress_reports']
        previous_quarter = 'q' + str(int(reporting_period[-1]) - 1)
        application = collection.find_one({'application_id': application_id, 'reporting_period': previous_quarter})
    
    client.close()

    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('progress_report_selection'))

    # Get user information from the session
    user = session.get('user', {})
    name = user.get('name', '')
    email = user.get('email', '')

    # Determine which template to use based on the reporting period
    if reporting_period == 'q1':
        template = 'progress-report-qt.html'
    elif reporting_period == 'q2':
        template = 'progress-report-qt2.html'
    elif reporting_period == 'q3':
        template = 'progress-report-qt3.html'
    elif reporting_period == 'q4':
        template = 'progress-report-qt4.html'
    else:
        flash('Invalid reporting period', 'error')
        return redirect(url_for('select_quarter', application_id=application_id))

    # Prepare the context dictionary
    context = {
        'application_id': application_id,
        'user_name': name,
        'reporting_period': reporting_period,
        'app_title': application.get('app_title'),
        'user_email': email,
        'phone': application.get('phone'),
        'project_title': application.get('title'),
    }

    # Adjust 'amount_awarded' based on the reporting period
    if reporting_period == 'q1':
        context['amount_awarded'] = application.get('grandTotal')
    else:
        context['amount_awarded'] = application.get('amount_awarded')

    # Add output and outcome fields
    for i in range(1, 6):
        context[f'output{i}'] = application.get(f'output{i}')
        context[f'final_target_output_{i}'] = application.get(f'target_output_{i}')
        context[f'outcome{i}'] = application.get(f'outcome{i}')
        context[f'final_target_outcome_{i}'] = application.get(f'target_outcome_{i}')

    # Add fields specific to q2, q3, q4 reports
    if reporting_period != 'q1':
        for i in range(1, 6):
            for field in ['target', 'aa', 'ontrack']:
                for type in ['', 'outcome_']:
                    for q in range(1, int(reporting_period[-1])):
                        key = f'q{q}_{type}{field}_{i}'
                        context[key] = application.get(key)
        for i in ['a', 'b']:
            for field in ['target', 'aa', 'ontrack']:
                for type in ['']:
                    for q in range(1, int(reporting_period[-1])):
                        key = f'q{q}_{type}{field}_{i}'
                        context[key] = application.get(key)
        # Add final_target_output_a for outputs and outcomes
        for i in range(1, 6):
            context[f'final_target_output_{i}'] = application.get(f'final_target_output_{i}')
            context[f'final_target_outcome_{i}'] = application.get(f'final_target_outcome_{i}')
        for i in ['a', 'b']:
            context[f'final_target_output_{i}'] = application.get(f'final_target_output_{i}')
            context[f'final_target_outcome_{i}'] = application.get(f'final_target_outcome_{i}')
        # Add amount_expended based on the reporting period
        if reporting_period == 'q2':
            context['amount_expended_qt'] = application.get('amount_expended_qt')
        elif reporting_period == 'q3':
            context['amount_expended_qt'] = application.get('amount_expended_qt')
            context['amount_expended_qt2'] = application.get('amount_expended_qt2')
        elif reporting_period == 'q4':
            context['amount_expended_qt'] = application.get('amount_expended_qt')
            context['amount_expended_qt2'] = application.get('amount_expended_qt2')
            context['amount_expended_qt3'] = application.get('amount_expended_qt3')

    # Render the appropriate quarterly progress report template with auto-filled information
    return render_template(template, **context)

@app.route('/progress-report-bi/<application_id>', methods=['GET', 'POST'])
@login_required
def progress_report_bi(application_id):
    # Fetch the application details from the database based on the reporting period
    client = MongoClient(mongo_uri)
    db = client[db_name]
    reporting_period = request.form.get('reporting_period')
    
    if reporting_period == 'mid_year':
        collection = db['ysab-applications']
        application = collection.find_one({'_id': application_id})
    elif reporting_period == 'end_year':
        collection = db['progress_reports']
        application = collection.find_one({'application_id': application_id, 'reporting_period': 'mid_year'})
    else:
        flash('Invalid reporting period', 'error')
        return redirect(url_for('select_biannual', application_id=application_id))
    
    client.close()

    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('progress_report_selection'))

    # Get user information from the session
    user = session.get('user', {})
    name = user.get('name', '')
    email = user.get('email', '')

    # Determine which template to use based on the reporting period
    if reporting_period == 'mid_year':
        template = 'progress-report-bi.html'
    elif reporting_period == 'end_year':
        template = 'progress-report-end_year.html'
    else:
        flash('Invalid reporting period', 'error')
        return redirect(url_for('select_biannual', application_id=application_id))

    # Prepare the context dictionary
    context = {
        'application_id': application_id,
        'user_name': name,
        'reporting_period': reporting_period,
        'app_title': application.get('app_title'),
        'user_email': email,
        'phone': application.get('phone'),
        'project_title': application.get('title'),
    }

    # Adjust 'amount_awarded' based on the reporting period
    if reporting_period == 'mid_year':
        context['amount_awarded'] = application.get('grandTotal')
    else:
        context['amount_awarded'] = application.get('amount_awarded')

    # Add output and outcome fields
    for i in range(1, 6):
        context[f'output{i}'] = application.get(f'output{i}')
        context[f'final_target_output_{i}'] = application.get(f'target_output_{i}')
        context[f'outcome{i}'] = application.get(f'outcome{i}')
        context[f'final_target_outcome_{i}'] = application.get(f'target_outcome_{i}')

    # Add fields specific to midterm and final reports
    if reporting_period != 'mid_year':
        for i in range(1, 6):
            for field in ['target', 'aa', 'ontrack']:
                for type in ['', 'outcome_']:
                    for q in ['midterm', 'final']:
                        key = f'{q}_{type}{field}_{i}'
                        context[key] = application.get(key)
        for i in ['a', 'b']:
            for field in ['target', 'aa', 'ontrack']:
                for type in ['']:
                    for q in ['midterm', 'final']:
                        key = f'{q}_{type}{field}_{i}'
                        context[key] = application.get(key)
        # Add final_target_output_a for outputs and outcomes
        for i in range(1, 6):
            context[f'final_target_output_{i}'] = application.get(f'final_target_output_{i}')
            context[f'final_target_outcome_{i}'] = application.get(f'final_target_outcome_{i}')
        for i in ['a', 'b']:
            context[f'final_target_output_{i}'] = application.get(f'final_target_output_{i}')
            context[f'final_target_outcome_{i}'] = application.get(f'final_target_outcome_{i}')

        # Add amount_expended_mid field
        context['amount_expended_mid'] = application.get('amount_expended_mid')


    # Render the appropriate bi-annual progress report template with auto-filled information
    return render_template(template, **context)

@app.route('/progress-report-annual/<application_id>', methods=['GET', 'POST'])
@login_required
def progress_report_annual(application_id):
    # Fetch the application details from the database
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db['ysab-applications']
    application = collection.find_one({'_id': application_id})
    client.close()
    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('progress_report_selection'))

    # Get user information from the session
    user = session.get('user', {})
    name = user.get('name', '')
    email = user.get('email', '')
    reporting_period = 'Annually'

    # Render the annual progress report template with auto-filled information
    return render_template('progress-report-annual.html',
                           reporting_period=reporting_period,
                           user_name=name,
                           app_title=application['app_title'],
                           user_email=email,
                           phone=application['phone'],
                           project_title=application['title'],
                           output1=application['output1'],
                           output2=application['output2'],
                           output3=application['output3'],
                           output4=application['output4'],
                           output5=application['output5'],
                           target1=application['target_output_1'],
                           target2=application['target_output_2'],
                           target3=application['target_output_3'],
                           target4=application['target_output_4'],
                           target5=application['target_output_5'],
                           outcome1=application['outcome1'],
                           outcome2=application['outcome2'],
                           outcome3=application['outcome3'],
                           outcome4=application['outcome4'],
                           outcome5=application['outcome5'],
                           target1_1=application['target_outcome_1'],
                           target2_1=application['target_outcome_2'],
                           target3_1=application['target_outcome_3'],
                           target4_1=application['target_outcome_4'],
                           target5_1=application['target_outcome_5'],
                           grand_total=application['grandTotal'])

@app.route('/external')
@login_required
def external():
    return render_template('external.html')

@app.route('/submit_application_form', methods=['POST'])
def submit_application_form():
        try:     
            # Get form data
            form_data = request.form.to_dict()
            name = request.form.get('name')
            email = request.form.get('email')
            
            form_data = {'_id': app_id(), 'timestamp': get_timestamp(), **form_data}

            # Create metadata_app_data variable
            metadata_app_data = {
                '_id': form_data['_id'],
                'app_number': get_app_num(),  # Get app_number from get_app_num() function
                'title': form_data['title'],
                'name': form_data['name'],
                'email': form_data['email'],
                'timestamp': form_data['timestamp']
            }

            # Insert data into MongoDB - application
            with MongoClient(mongo_uri) as client:
                db = client[db_name]
                collection = db['ysab-applications']
                collection.insert_one(form_data)

            # insert data into metadata collection
            with MongoClient(mongo_uri) as client:
                db = client[db_name]
                collection = db['metadata_applications']
                collection.insert_one(metadata_app_data)

            # Log the status change in activities collection
            db['activities'].insert_one({
                'timestamp': get_timestamp(),
                'type': 'Application Submission',
                'description': f'New application submitted by {name} ({email})',
                'user': email
            })

            # Send Discord notification
            message = f"🔵 New Application Submitted:\n- ID: {form_data['_id']}\n- Type: {'Internal Application'}\n- Name: {name}\n- Email: {email} \n- Title: {form_data['title']}"
            requests.post(discord_webhook_url, json={"content": message})

            # return jsonify({'success': True, 'message': 'Form data submitted successfully'})
            return render_template('confirmation_a.html', name=name, email=email)
        except Exception as e:
            # return jsonify({'success': False, 'error': str(e)})
             return render_template('error.html', error=str(e))
        
@app.route('/submit_progress_report', methods=['POST'])
def submit_progress_report():
    try:     
        # Get form data
        form_data = request.form.to_dict()
        name = request.form.get('name')
        email = request.form.get('email')
        title = request.form.get('title')
        form_id = progress_report_id(request.form.get('reporting_period'))

        if not title:
            title = form_data.get('project_title', 'Untitled Project')
            print(f"Warning: Title not found in form submission for {form_id}")

        form_data = {'_id': form_id, 'timestamp': get_timestamp(), 'title': title, **form_data}

        # Insert data into MongoDB
        cluster = MongoClient(mongo_uri)
        db = cluster[db_name]
        collection = db['progress_reports']
        collection.insert_one(form_data)

        # Log the status change in activities collection
        db['activities'].insert_one({
            'timestamp': get_timestamp(),
            'type': 'Progress Report Submission',
            'description': f'New progress report submitted by {name} ({email})',
            'user': email
        })

        # Send Discord notification
        message = f"🟢 Progress Report Submitted:\n- ID: {form_data['_id']}\n- Name: {name}\n- Email: {email} \n- Reporting Period: {form_data['reporting_period']}\n- Title: {title}"
        requests.post(discord_webhook_url, json={"content": message})

        return render_template('confirmation_p.html', name=name, email=email)
    except Exception as e:
        return render_template('error.html', error=str(e))
        
@app.route('/submit_external_form', methods=['POST'])
def submit_external_form():
        try:     
            # Get form data
            form_data = request.form.to_dict()
            name = request.form.get('name')
            email = request.form.get('email')
            
            form_data = {'_id': ext_id(), 'timestamp': get_timestamp(), **form_data}

            # Insert data into MongoDB
            cluster = MongoClient(mongo_uri)
            db = cluster[db_name]
            collection = db['ysab-external']
            collection.insert_one(form_data)
           # make html application w/ user responses
            # make_ext_form(form_data)

            # Log the status change in activities collection
            db['activities'].insert_one({
                'timestamp': get_timestamp(),
                'type': 'External Application Submission',
                'description': f'New external application submitted by {name} ({email})',
                'user': email
            })

            # Send Discord notification
            message = f"🟠 External Application Submitted:\n- ID: {form_data['_id']}\n- Name: {name}\n- Email: {email} \n- Title: {form_data['title']}"
            requests.post(discord_webhook_url, json={"content": message})

            # return jsonify({'success': True, 'message': 'Form data submitted successfully'})
            return render_template('confirmation_e.html', name=name, email=email)
        except Exception as e:
            # return jsonify({'success': False, 'error': str(e)})
             return render_template('error.html', error=str(e))
        
@app.route('/submit_continuation_form', methods=['POST'])
def submit_continuation_form():
        try:     
            # Get form data
            form_data = request.form.to_dict()
            name = request.form.get('name')
            email = request.form.get('email')

            form_data = {'_id': cont_id(), 'timestamp': get_timestamp(), **form_data}

            # Insert data into MongoDB
            cluster = MongoClient(mongo_uri)
            db = cluster[db_name]
            collection = db['ysab-continuation']

            collection.insert_one(form_data)
           # make html application w/ user responses
            make_cont_form(form_data)

            # Log the status change in activities collection
            db['activities'].insert_one({
                'timestamp': get_timestamp(),
                'type': 'Continuation Application Submission',
                'description': f'New continuation application submitted by {name} ({email})',
                'user': email
            })

            # return jsonify({'success': True, 'message': 'Form data submitted successfully'})
            return render_template('confirmation_c.html', name=name, email=email)
        except Exception as e:
            # return jsonify({'success': False, 'error': str(e)})
             return render_template('error.html', error=str(e))


@app.route('/edit-application/<application_id>/<application_type>')
def edit_application(application_id, application_type):
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]

    if application_type == 'Internal Application':
        collection = db['ysab-applications']
    elif application_type == 'External Application':
        collection = db['ysab-external']
    else:
        return render_template('error.html', error='Invalid application type')

    application = collection.find_one({'_id': application_id})

    if application is None:
        return render_template('error.html', error='Application not found')
    else:
        # Render template based on application type
        if application_type == 'External Application':
            return render_template('edit-external-application.html', application=application, application_type=application_type)
        elif application_type == 'Internal Application':    
            return render_template('edit-application.html', application=application, application_type=application_type)
        else:
            return render_template('error.html', error='Invalid application type')

@app.route('/update-application', methods=['POST'])
def update_application():
    try:
        # Get form data
        updated_data = request.form.to_dict()
        name = request.form.get('name')
        email = request.form.get('email')
        application_id = request.form.get('_id')
        application_type = request.form.get('application_type')

        # Update timestamp
        updated_data['timestamp'] = get_timestamp()
        
        cluster = MongoClient(mongo_uri)
        db = cluster[db_name]

        if application_type == 'Internal Application':
            collection = db['ysab-applications']
        elif application_type == 'External Application':
            collection = db['ysab-external']
        else:
            return render_template('error.html', error='Invalid application type')

        # Remove '_id' from updated_data to prevent attempting to modify the immutable field
        updated_data.pop('_id', None)

        # Fetch the current document to check existing values
        current_doc = collection.find_one({'_id': application_id})
        
        if current_doc:
            # Update 'edited' and 'num_edits' fields
            updated_data['edited'] = 'yes'
            updated_data['num_edits'] = current_doc.get('num_edits', 0) + 1
        else:
            # Set initial values for new documents
            updated_data['edited'] = 'no'
            updated_data['num_edits'] = 0

        # Update the existing record
        result = collection.update_one(
            {'_id': application_id},
            {'$set': updated_data},
            upsert=True
        )

        if result.modified_count == 0 and result.upserted_id is None:
            return render_template('error.html', error='No changes made to the application')

        # Log the status change in activities collection
        db['activities'].insert_one({
            'timestamp': get_timestamp(),
            'type': 'Application Update',
            'description': f'Application {application_id} updated by {name} ({email})',
            'user': email
        })

        # Send Discord notification
        message = f"🆙 Application updated:\n- ID: {application_id}\n- Type: {application_type}\n- Name: {name}\n- Email: {email} \n- Title: {updated_data['title']}\n- Number of edits: {updated_data.get('num_edits', 1)}"
        requests.post(discord_webhook_url, json={"content": message})

        if application_type == 'Internal Application':
            return render_template('confirmation_a.html', name=name, email=email)
        elif application_type == 'External Application':
            return render_template('confirmation_e.html', name=name, email=email)

    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/download_application')
def download_file_a():
    p = r'templates/ysab-application-record.html'
    return send_file(p, as_attachment=True)

@app.route('/download_application_fromtable/<application_id>/<format>')
def download_file_a_fromtable(application_id, format):
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        collection = db['ysab-applications']
        application = collection.find_one({'_id': application_id})

    if application:
        if format == 'html':
            make_app_form(application, download_source='table')
            p = r'templates/ysab-application-record.html'
            return send_file(p, as_attachment=True, download_name=f"ysab_application_{application_id}.html")
        elif format == 'pdf':
            make_pdf(application, application_id)
            return send_file(f"ysab_application_{application_id}.pdf", 
                           as_attachment=True,
                           download_name=f"ysab_application_{application_id}.pdf",
                           mimetype='application/pdf')
    else:
        return "Application not found", 404
    
@app.route('/download_external_fromtable/<application_id>')
def download_file_e_fromtable(application_id):
    with MongoClient(mongo_uri) as client:
        # use ysab main db
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        collection = db['ysab-external']
        application = collection.find_one({'_id': application_id})

    if application:
        make_ext_form(application, download_source='table')
        p = r'templates/ysab-external-record.html'
        return send_file(p, as_attachment=True, download_name=f"ysab_external_application_{application_id}.html")
    else:
        return "Application not found", 404
    
@app.route('/download_progress_report/<application_id>')
def download_file_p_fromtable(application_id):
    with MongoClient(mongo_uri) as client:
        # use ysab main db
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        collection = db['progress_reports']
        report = collection.find_one({'_id': application_id})

    if report:
        make_prog_form(report, download_source='table')
        
        # Generate filename based on reporting period
        reporting_period = report.get('reporting_period', '')
        period_name = {
            'q1': 'Q1',
            'q2': 'Q2',
            'q3': 'Q3',
            'q4': 'Q4',
            'mid_year': 'Mid_Year',
            'end_year': 'End_Year',
            'annual': 'Annual'
        }.get(reporting_period, '')
        
        filename = f"ysab_progress_report_{period_name}_{application_id}.html"
        
        return send_file(
            'templates/ysab-progress-report-record.html',
            as_attachment=True,
            download_name=filename
        )
    else:
        return "Progress Report not found", 404

@app.route('/download_progress_report')
def download_file_p():
    p = r'templates/progress-report-copy-record.html'
    return send_file(p, as_attachment=True)

@app.route('/download_external_form')
def download_file_e():
    p = r'templates/ysab-external-record.html'
    return send_file(p, as_attachment=True)

@app.route('/download_continuation_form')
def download_file_c():
    p = r'templates/ysab-continuation-record.html'
    return send_file(p, as_attachment=True)

@app.route('/my_progress_report/<application_id>')
@login_required
def my_progress_report(application_id):
    
    # Get user email based on admin mode
    if admin_mode_switch==True:
        user_email = os.getenv("EMAIL")
    elif admin_mode_switch==False: 
        user_email = session['user']['email']

    # Connect to MongoDB
    client = MongoClient(mongo_uri)

    # Choose database based on admin status
    if user_email.lower() in [email.lower() for email in ADMIN_EMAILS]:
        db = client[os.getenv("DB_NAME_DEV")]
    else:
        db = client[os.getenv("DB_NAME")]
    collection = db['progress_reports']

    # Fetch progress reports for the given application_id
    progress_reports = list(collection.find({'application_id': application_id}))

    client.close()

    if not progress_reports:
        message = "No progress reports found for this application."
        return render_template('my_progress_report.html', message=message)

    progress_reports = [
        {
            '_id': report['_id'],
            'timestamp': report['timestamp'],
            'title': report['title'],
            'reporting_interval': (
                'Quarterly' if report.get('reporting_period') in ['q1', 'q2', 'q3', 'q4']
                else 'Bi-annual' if report.get('reporting_period') in ['mid_year', 'end_year']
                else 'Annual' if report.get('reporting_period') == 'annual'
                else 'N/A'
            ),
            'reporting_period':(
                'Q1' if report.get('reporting_period') == 'q1'
                else 'Q2' if report.get('reporting_period') == 'q2'
                else 'Q3' if report.get('reporting_period') == 'q3'
                else 'Q4' if report.get('reporting_period') == 'q4'
                else 'Mid-Year' if report.get('reporting_period') == 'mid_year'
                else 'End-Year' if report.get('reporting_period') == 'end_year'
                else 'Annual' if report.get('reporting_period') == 'annual'
                else 'N/A'
            ),
        }
        for report in progress_reports
    ]
    return render_template('my_progress_report.html', progress_reports=progress_reports, admin_emails=ADMIN_EMAILS, deputy_emails=DEPUTY_EMAILS)

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    # Check if user is admin
    if 'user' not in session or session['user']['email'] not in ADMIN_EMAILS:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))
    
    with MongoClient(mongo_uri) as client:
        # use ysab main db
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        
        # Get total users
        total_users = db['users'].count_documents({})
        
        # Get total applications (both internal and external)
        total_internal = db['ysab-applications'].count_documents({})
        total_external = db['ysab-external'].count_documents({})
        total_applications = total_internal + total_external
        
        # Get pending reviews (you'll need to add a status field to your applications)
        pending_reviews = db['ysab-applications'].count_documents({'application_status': 'pending'})
        
        # Get approved applications
        approved_applications = db['ysab-applications'].count_documents({'application_status': 'approved'})
        
        # Get not approved applications
        not_approved_applications = db['ysab-applications'].count_documents({'application_status': 'not-approved'})
        
        # Get recent activities (you might want to create a new collection for this)
        recent_activities = list(db['activities'].find().sort('timestamp', -1).limit(5))

    return render_template('admin_dashboard.html',
                         admin_emails=ADMIN_EMAILS,
                         deputy_emails=DEPUTY_EMAILS,
                         total_users=total_users,
                         total_applications=total_applications,
                         pending_reviews=pending_reviews,
                         approved_applications=approved_applications,
                         not_approved_applications=not_approved_applications,
                         recent_activities=recent_activities)

@app.route('/admin/applications')
@login_required
@admin_required
def all_applications():
    # Check if user is admin
    if 'user' not in session or session['user']['email'] not in ADMIN_EMAILS:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))

    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    # use ysab main db
    db_name = os.getenv("DB_NAME")
    db = client[db_name]
    
    # Fetch all applications from both collections
    applications_collection = db['ysab-applications']
    external_collection = db['ysab-external']
    
    # Fetch all applications (without email filter)
    all_internal_applications = list(applications_collection.find(
        {},
        {'_id': 1, 'timestamp': 1, 'title': 1, 'email': 1, 'name': 1, 'application_status': 1}
    ))
    
    all_external_applications = list(external_collection.find(
        {},
        {'_id': 1, 'timestamp': 1, 'title': 1, 'email': 1, 'name': 1, 'application_status': 1}
    ))

    # Combine both application lists
    all_applications = all_internal_applications + all_external_applications

    if not all_applications:
        message = "No applications found in the system."
        return render_template('admin_applications.html', message=message)
    
    # Format the data for the template
    applications = []
    for app in all_applications:
        # Check if the application is internal or external
        if app in all_internal_applications:
            app_type = 'Internal Application'
        elif app in all_external_applications:
            app_type = 'External Application'
        else:
            app_type = 'Unknown Application'

        applications.append({
            'id': str(app['_id']),
            'submission_date': app['timestamp'],
            'title': app['title'],
            'email': app['email'],
            'name': app['name'],
            'type': app_type,
            'application_status': app.get('application_status', 'pending')
        })

    client.close()

    # Sort applications by submission date (newest first)
    applications.sort(key=lambda x: x['submission_date'], reverse=True)

    return render_template('admin_applications.html', applications=applications, admin_emails=ADMIN_EMAILS, deputy_emails=DEPUTY_EMAILS)

@app.route('/admin/manage-applications')
@login_required
def manage_applications():
    # Check if user is admin
    if 'user' not in session or session['user']['email'] not in ADMIN_EMAILS:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('home'))

    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    # use ysab main db
    db_name = os.getenv("DB_NAME")
    db = client[db_name]
    
    # Fetch all applications from both collections
    applications_collection = db['ysab-applications']
    external_collection = db['ysab-external']
    
    # Fetch all applications
    all_internal_applications = list(applications_collection.find(
        {},
        {'_id': 1, 'timestamp': 1, 'title': 1, 'name': 1, 'application_status': 1}
    ))
    
    all_external_applications = list(external_collection.find(
        {},
        {'_id': 1, 'timestamp': 1, 'title': 1, 'name': 1, 'application_status': 1}
    ))

    # Combine and format applications
    applications = []
    for app in all_internal_applications + all_external_applications:
        applications.append({
            'id': str(app['_id']),
            'submission_date': app['timestamp'],
            'name': app.get('name', 'N/A'),
            'title': app.get('title', 'N/A'),
            'type': 'Internal Application' if app in all_internal_applications else 'External Application',
            'application_status': app.get('application_status', 'pending')
        })

    # Sort by submission date (newest first)
    applications.sort(key=lambda x: x['submission_date'], reverse=True)

    return render_template('manage_applications.html', applications=applications, admin_emails=ADMIN_EMAILS, deputy_emails=DEPUTY_EMAILS)

@app.route('/update_application_status', methods=['POST'])
@login_required
def update_application_status():
    if 'user' not in session or session['user']['email'] not in ADMIN_EMAILS:
        return jsonify({'success': False, 'error': 'Unauthorized'})

    try:
        application_id = request.form.get('application_id')
        # Convert string ID to ObjectId if needed
        if ObjectId.is_valid(application_id):
            application_id = ObjectId(application_id)
        
        new_status = request.form.get('application_status')

        client = MongoClient(mongo_uri)
        # use ysab main db
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        
        # Try updating in internal applications first
        result = db['ysab-applications'].update_one(
            {'_id': application_id},
            {'$set': {'application_status': new_status}}
        )

        # If not found in internal, try external applications
        if result.modified_count == 0:
            result = db['ysab-external'].update_one(
                {'_id': application_id},
                {'$set': {'application_status': new_status}}
            )

        if result.modified_count > 0:
            # Log the status change in activities collection
            db['activities'].insert_one({
                'timestamp': get_timestamp(),
                'type': 'Status Update',
                'description': f'Application {application_id} status changed to {new_status}',
                'user': session['user']['email']
            })
            
            return jsonify({'success': True})
        else:
            # Add debug information
            internal_app = db['ysab-applications'].find_one({'_id': application_id})
            external_app = db['ysab-external'].find_one({'_id': application_id})
            if not internal_app and not external_app:
                return jsonify({'success': False, 'error': f'Application not found with ID: {application_id}'})
            else:
                return jsonify({'success': False, 'error': 'Application found but update failed'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        client.close()

@app.route('/admin/manage_users')
@login_required
@admin_required
def manage_users():
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        users = list(db['users'].find())
    return render_template('manage_users.html', users=users, admin_emails=ADMIN_EMAILS, deputy_emails=DEPUTY_EMAILS)

@app.route('/delete_user', methods=['POST'])
@login_required
@admin_required
def delete_user():
    user_id = request.form.get('user_id')
    
    try:
        with MongoClient(mongo_uri) as client:
            db = client[db_name]
            result = db['users'].delete_one({'_id': ObjectId(user_id)})
            return jsonify({'success': result.deleted_count > 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/activity-dashboard')
@login_required
@admin_required
def activity_dashboard():
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        
        # Get all activities
        activities = list(db['activities'].find().sort('timestamp', -1))
        
        # Calculate activity metrics
        total_activities = len(activities)
        
        # Get activity counts by type
        activity_types = {}
        for activity in activities:
            activity_type = activity.get('type', 'Unknown')
            activity_types[activity_type] = activity_types.get(activity_type, 0) + 1
        
        # Get user engagement metrics
        unique_users = len(set(activity['user'] for activity in activities))
        
        # Get daily activity counts for the last 30 days
        from datetime import datetime, timedelta
        today = datetime.now()
        thirty_days_ago = today - timedelta(days=30)
        
        daily_activities = {}
        for activity in activities:
            try:
                date = datetime.strptime(activity['timestamp'], '%m-%d-%Y %H:%M').date()
                if date >= thirty_days_ago.date():
                    daily_activities[date] = daily_activities.get(date, 0) + 1
            except (ValueError, KeyError):
                continue
        
        # Format dates for chart
        dates = sorted(daily_activities.keys())
        activity_counts = [daily_activities[date] for date in dates]
        formatted_dates = [date.strftime('%Y-%m-%d') for date in dates]
        
        return render_template(
            'activity_dashboard.html',
            activities=activities[:100],  # Show last 100 activities
            total_activities=total_activities,
            activity_types=activity_types,
            unique_users=unique_users,
            daily_activity_data={
                'dates': formatted_dates,
                'counts': activity_counts
            },
            admin_emails=ADMIN_EMAILS,
            deputy_emails=DEPUTY_EMAILS
        )

@app.route('/budget-dashboard')
def budget_dashboard():
        # Check if user is either admin or deputy
    if not (is_admin(session['user']['email']) or is_deputy(session['user']['email'])):
        flash('Access denied. You must be an admin or deputy to access this page.', 'error')
        return redirect(url_for('home'))
    
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        
        # Define allocated budgets for each service area (you can modify these values)
        allocated_budgets = {
            'Residential Services': 26000,
            'Detention Services': 27000,
            'Probation Services': 27000,
            'Crane Fund': 25000,
            'Black History Committee': 10000,
            'Hispanic Committee': 10000,
            'Holiday': 30000,
            'Food Pantry': 20000,
            'GED': 4000,
            'Education': 0, 
            'Clinical': 0  
        }
        
        # Get all applications from both internal and external collections
        internal_apps = list(db['ysab-applications'].find({}, {
            'amount': 1, 
            'service_area': 1,
            'title': 1,
            'timestamp': 1,
            'application_status': 1
        }))
        
        external_apps = list(db['ysab-external'].find({}, {
            'amount': 1,
            'service_area': 1,
            'title': 1,
            'timestamp': 1,
            'application_status': 1
        }))

        all_applications = internal_apps + external_apps

        # Helper function to safely convert amount to float
        def safe_float(value):
            try:
                if value and isinstance(value, (str, int, float)):
                    # Remove any currency symbols and commas
                    if isinstance(value, str):
                        value = value.replace('$', '').replace(',', '').strip()
                    return float(value)
                return 0.0
            except (ValueError, TypeError):
                return 0.0

        # Calculate total budget metrics with safe conversion
        total_requested = sum(safe_float(app.get('amount')) for app in all_applications)
        total_approved = sum(
            safe_float(app.get('amount'))
            for app in all_applications 
            if app.get('application_status') == 'approved'
        )
        
        # Group amounts by service area with safe conversion
        service_area_totals = {}
        service_area_details = {}
        
        for app in all_applications:
            service_area = app.get('service_area', 'Unspecified')
            amount = safe_float(app.get('amount'))
            
            # Update service_area_totals
            if service_area not in service_area_totals:
                service_area_totals[service_area] = 0
            service_area_totals[service_area] += amount
            
            # Initialize the service area if it doesn't exist in details
            if service_area not in service_area_details:
                service_area_details[service_area] = {
                    'applications': [],
                    'total_requested': 0,
                    'allocated_budget': allocated_budgets.get(service_area, 0)
                }
            
            # Add the application details
            service_area_details[service_area]['applications'].append({
                'title': app.get('title', 'Untitled'),
                'amount': amount,
                'status': app.get('application_status', 'pending'),
                'timestamp': app.get('timestamp', 'N/A')
            })
            service_area_details[service_area]['total_requested'] += amount

        # Get recent applications for the table
        recent_applications = sorted(
            all_applications,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )[:10]  # Get last 10 applications

        return render_template(
            'budget_dashboard.html',
            total_requested=total_requested,
            total_approved=total_approved,
            service_area_totals=service_area_totals,
            service_area_details=service_area_details,
            admin_emails=ADMIN_EMAILS,
            deputy_emails=DEPUTY_EMAILS
        )


if __name__ == '__main__':
    app.run(debug=admin_mode_switch)

