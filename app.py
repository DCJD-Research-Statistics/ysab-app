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
from functools import wraps  # Add this line
from bson import ObjectId
import requests

load_dotenv() 

mongo_uri = os.getenv("MONGO_URI")
db_name = os.getenv("DB_NAME")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))


def get_timestamp():
    central_timezone = pytz.timezone('America/Chicago')
    current_time = dt.now(central_timezone)
    timestamp = current_time.strftime("%m-%d-%Y %H:%M")
    return timestamp

def get_program_list():
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]
    collection = db['ysab']
    # Retrieve all records from the collection
    cursor = collection.find()
    # Convert the cursor to a list of dictionaries
    records = list(cursor)
    # Create a Pandas DataFrame
    df = pd.DataFrame(records)
    cluster.close()
    return df.title.to_list()

# pre-populate fields auto
def get_app_list(user_email):
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]
    collection = db['ysab']
    # Retrieve records from the collection for the specific user
    cursor = collection.find({'email': user_email})
    # Convert the cursor to a list of dictionaries
    records = list(cursor)
    # Create a Pandas DataFrame
    df = pd.DataFrame(records)
    if df.empty:
        cluster.close()
        return []
    df['app_record'] = pd.concat([df.timestamp.str[:10], df[['name', 'app_title', 'email', 'phone', 'title', 'amount', 'output1', 'output2', 'output3', 'output4', 'output5', 'target1', 'target2', 'target3', 'target4', 'target5', 'outcome1', 'outcome2', 'outcome3', 'outcome4', 'outcome5', 'target1.1', 'target2.1', 'target3.1', 'target4.1', 'target5.1']].astype(str)], axis=1).apply(lambda row: ' : '.join(row), axis=1)
    cluster.close()
    return df.app_record.to_list()

prog_report_items = ['name', 
                     'title', 
                     'email', 
                     'phone', 
                     'title', 
                     'how_funds_advanced_goals_of_program', 
                     'project_contact',
                     'fiscal_year',
                     'start_date',
                     'end_date',
                     'amount_awarded',
                     'amount_expended_mid',
                     'target_a',
                     'midterm_a', 
                     'target_b',
                     'midterm_b', 
                     'output1',
                     'output2',
                     'output3',
                     'output4',
                     'output5',
                     'output6',
                     'target1',
                     'target2',
                     'target3',
                     'target4',
                     'target5',
                     'target6',
                     'midterm1', 
                     'midterm2', 
                     'midterm3', 
                     'midterm4', 
                     'midterm5', 
                     'midterm6',
                     'outcome1',
                     'outcome2',
                     'outcome3',
                     'outcome4',
                     'outcome5',
                     'outcome6',
                     'target1.1',
                     'target2.1',
                     'target3.1',
                     'target4.1',
                     'target5.1',
                     'target6.1',
                     'midterm1.1', 
                     'midterm2.1', 
                     'midterm3.1', 
                     'midterm4.1', 
                     'midterm5.1', 
                     'midterm6.1',
                    'funds_explain',
                    'midterm_full_amount_no',
                    'midterm_full_amount_no2']

# pre-populate fields auto - progress report 
def get_prog_list():
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]
    collection = db['progress_reports']
    cursor = collection.find()
    records = list(cursor)

    if len(records) == 0:
        return []

    df = pd.DataFrame(records)
    # Check if the DataFrame is empty after conversion
    if df.empty:
        cluster.close()
        return []
    
    df['app_record'] = pd.concat([df.timestamp.str[:10], df[prog_report_items].astype(str)], axis=1).apply(lambda row: ' : '.join(row), axis=1)
    cluster.close()
    return df.app_record.to_list()

def get_app_num():
    with MongoClient(mongo_uri) as client:
        db = client[db_name]
        collection = db["ysab"]
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
    collection = db['ysab']
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

def make_prog_form(form_data):
    # Read the HTML file
    with open(r'templates/progress-report-copy.html', 'r', encoding="utf8") as file:
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
        with open(r'templates/progress-report-copy-record.html', 'w') as file:
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
        return render_template('landing.html', user=session['user'])
    return render_template('landing.html')

@app.route("/home", methods=['GET', 'POST'])
def home():
    if 'user' in session:
        return render_template('home.html', user=session['user'])
    return render_template('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
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
        return redirect(url_for('login'))
    
    # Send Discord notification
    discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL") 
    message = f"📩 New User Signup:\n- Name: {name}\n- Email: {email}"
    requests.post(discord_webhook_url, json={"content": message})

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        # MongoDB connection
        client = MongoClient(mongo_uri)
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

@app.route('/my-applications')
@login_required
def my_applications(admin_mode=False):
    if 'user' not in session:
        return redirect(url_for('login'))

    if admin_mode==True:
        user_email = 'daniel.pacheco@dallascounty.org'
    elif admin_mode==False: 
        user_email = session['user']['email']

    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db['ysab']

    # Fetch applications for the current user from 'ysab' collection
    user_applications = list(collection.find(
        {'email': {'$regex': f'^{user_email}$', '$options': 'i'}},
        {'_id': 1, 'timestamp': 1, 'title': 1}
    ))

    # Fetch applications for the current user from 'ysab-external' collection
    external_collection = db['ysab-external']
    user_external_applications = list(external_collection.find(
        {'email': {'$regex': f'^{user_email}$', '$options': 'i'}},
        {'_id': 1, 'timestamp': 1, 'title': 1}
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
            app_type = 'Unknown Application'  # Fallback in case of unexpected data

        applications.append({
            'id': str(app['_id']),
            'submission_date': app['timestamp'],
            'title': app['title'],
            'type': app_type  # Use the determined app_type
        })

    client.close()

    return render_template('my_applications.html', applications=applications)

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/application')
@login_required
def application():
    return render_template('application.html')

@app.route('/progress-report')
@login_required
def progress_report(admin_mode=False):
    if admin_mode==True:
        user_email = 'daniel.pacheco@dallascounty.org'
        return render_template('progress-report.html', dropdown_items=get_program_list(), app_list=get_app_list(user_email), prog_list=get_prog_list())   
    if admin_mode==False:
        user_email = session['user']['email']
        return render_template('progress-report.html', dropdown_items=get_program_list(), app_list=get_app_list(user_email), prog_list=get_prog_list())

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
                collection = db['ysab']
                collection.insert_one(form_data)

            # insert data into metadata collection
            with MongoClient(mongo_uri) as client:
                db = client[db_name]
                collection = db['metadata_applications']
                collection.insert_one(metadata_app_data)

           # make html application w/ user responses
            # make_app_form(form_data)

            # Send Discord notification
            discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL") 
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
            form_id = progress_report_id(request.form.get('reporting_period'))

            form_data = {'_id': form_id, 'timestamp': get_timestamp(), **form_data}

            # Insert data into MongoDB
            cluster = MongoClient(mongo_uri)
            db = cluster[db_name]
            collection = db['progress_reports']
            collection.insert_one(form_data)

           # make html application w/ user responses
            # make_prog_form(form_data)

            # Send Discord notification
            discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL") 
            message = f"🟢 Progress Report Submitted:\n- ID: {form_data['_id']}\n- Name: {name}\n- Email: {email} \n- Reporting Period: {form_data['reporting_period']}"
            requests.post(discord_webhook_url, json={"content": message})

            # return jsonify({'success': True, 'message': 'Form data submitted successfully'})
            return render_template('confirmation_p.html', name=name, email=email)
        except Exception as e:
            # return jsonify({'success': False, 'error': str(e)})
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

            # Send Discord notification
            discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")  # Ensure you have this in your .env
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

            # return jsonify({'success': True, 'message': 'Form data submitted successfully'})
            return render_template('confirmation_c.html', name=name, email=email)
        except Exception as e:
            # return jsonify({'success': False, 'error': str(e)})
             return render_template('error.html', error=str(e))

@app.route('/edit')
def edit():
    return render_template('edit.html')

@app.route('/edit-application/<application_id>/<application_type>')
def edit_application(application_id, application_type):
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]

    if application_type == 'Internal Application':
        collection = db['ysab']
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
        # make new id, timestamp
        updated_data['timestamp'] = get_timestamp()
        
        cluster = MongoClient(mongo_uri)
        db = cluster[db_name]

        if application_type == 'Internal Application':
            collection = db['ysab']
            updated_data['_id'] = app_id()
        elif application_type == 'External Application':
            collection = db['ysab-external']
            updated_data['_id'] = ext_id()
        else:
            return render_template('error.html', error='Invalid application type')

        # delete og record, insert new edited record
        collection.delete_one({'_id': application_id})
        collection.insert_one(updated_data)

        # Send Discord notification
        discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL")  # Ensure you have this in your .env
        message = f"Application updated:\n- ID: {application_id}\n- Type: {application_type}\n- Name: {name}\n- Email: {email} \n- Title: {updated_data['title']}"
        requests.post(discord_webhook_url, json={"content": message})

        # make html application w/ user responses
        if application_type == 'Internal Application':
            make_app_form(updated_data)
            return render_template('confirmation_a.html', name=name, email=email)
        elif application_type == 'External Application':
            make_ext_form(updated_data)
            return render_template('confirmation_e.html', name=name, email=email)

    except Exception as e:
        return render_template('error.html', error=str(e))

@app.route('/download_application')
def download_file_a():
    p = r'templates/ysab-application-record.html'
    return send_file(p, as_attachment=True)

@app.route('/download_application_fromtable/<application_id>')
def download_file_a_fromtable(application_id):
    with MongoClient(mongo_uri) as client:
        db = client[db_name]
        collection = db['ysab']
        application = collection.find_one({'_id': application_id})

    if application:
        make_app_form(application, download_source='table')
        p = r'templates/ysab-application-record.html'
        return send_file(p, as_attachment=True, download_name=f"ysab_application_{application_id}.html")
    else:
        return "Application not found", 404
    
@app.route('/download_external_fromtable/<application_id>')
def download_file_e_fromtable(application_id):
    with MongoClient(mongo_uri) as client:
        db = client[db_name]
        collection = db['ysab-external']
        application = collection.find_one({'_id': application_id})

    if application:
        make_ext_form(application, download_source='table')
        p = r'templates/ysab-external-record.html'
        return send_file(p, as_attachment=True, download_name=f"ysab_external_application_{application_id}.html")
    else:
        return "Application not found", 404

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

if __name__ == '__main__':
    app.run(debug=False)