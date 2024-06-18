from flask import Flask, request, render_template, jsonify, send_file
import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
import datetime
import os
import pytz
import pandas as pd
import re
from bs4 import BeautifulSoup
import math

load_dotenv() 

mongo_uri = os.getenv("MONGO_URI")
db_name = os.getenv("DB_NAME")

app = Flask(__name__)


def get_timestamp():
    central_timezone = pytz.timezone('America/Chicago')
    current_time = datetime.datetime.now(central_timezone)
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
def get_app_list():
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]
    collection = db['ysab']
    # Retrieve all records from the collection
    cursor = collection.find()
    # Convert the cursor to a list of dictionaries
    records = list(cursor)
    # Create a Pandas DataFrame
    df = pd.DataFrame(records)
    df['app_record'] = pd.concat([df.timestamp.str[:10], df[['name', 'app_title', 'email', 'phone', 'title', 'amount', 'output1', 'output2', 'output3', 'output4', 'output5', 'target1', 'target2', 'target3', 'target4', 'target5', 'outcome1', 'outcome2', 'outcome3', 'outcome4', 'outcome5', 'target1.1', 'target2.1', 'target3.1', 'target4.1', 'target5.1']].astype(str)], axis=1).apply(lambda row: ' : '.join(row), axis=1)
    cluster.close()
    return df.app_record.to_list()

# pre-populate fields auto - progress report 
def get_prog_list():
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]
    collection = db['progress_reports']
    # Retrieve all records from the collection
    cursor = collection.find()
    # Convert the cursor to a list of dictionaries
    records = list(cursor)
    # Create a Pandas DataFrame
    df = pd.DataFrame(records)
    df['app_record'] = pd.concat([df.timestamp.str[:10], df[['name', 'title', 'midterm_a', 'midterm_b', 'midterm1', 'midterm2', 'midterm3', 'midterm4', 'midterm5', 'midterm6', 
                                                                'midterm1.1', 'midterm2.1', 'midterm3.1', 'midterm4.1', 'midterm5.1', 'midterm6.1']].astype(str)], axis=1).apply(lambda row: ' : '.join(row), axis=1)
    cluster.close()
    return df.app_record.to_list()

def get_app_num():
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

def app_id():
    year = datetime.datetime.now().year
    application_number = get_app_num()
    project_name = request.form.get('title')
    project_abbreviation = re.sub(r'[^a-zA-Z0-9\s]', '', project_name)
    project_abbreviation = "".join(word[0] for word in project_abbreviation.split())
    # form type - A: application M: progress report mid-term F: progress report final E: external
    form_type = 'A'
    # Generate unique ID
    unique_id = f"{year}-{application_number:03d}-{project_abbreviation}-{form_type}"
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
    year = datetime.datetime.now().year
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
    year = datetime.datetime.now().year
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
    year = datetime.datetime.now().year
    application_number = get_cont_num()
    project_name = request.form.get('title')
    project_abbreviation = re.sub(r'[^a-zA-Z0-9\s]', '', project_name)
    project_abbreviation = "".join(word[0] for word in project_abbreviation.split())
    # form type - A: application M: progress report mid-term F: progress report final C: continuation
    form_type = 'C'
    # Generate unique ID
    unique_id = f"{year}-{application_number:03d}-{project_abbreviation}-{form_type}"
    return unique_id

def make_app_form(form_data):
    # Read the HTML file
    with open(r'templates/ysab-application.html', 'r', encoding="utf8") as file:
        html_content = file.read()
    # Parse the HTML content with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find the existing h4 tag and update it with the timestamp
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

def make_ext_form(form_data):
    # Read the HTML file
    with open(r'templates/ysab-external.html', 'r', encoding="utf8") as file:
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
    return render_template('index.html')

@app.route('/application')
def application():
    return render_template('application.html')

@app.route('/progress-report')
def progress_report():
    return render_template('progress-report.html', dropdown_items = get_program_list(), app_list = get_app_list(), prog_list = get_prog_list())

@app.route('/continuation')
def continuation():
    return render_template('continuation.html', app_list = get_app_list())

@app.route('/external')
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

            # Insert data into MongoDB
            cluster = MongoClient(mongo_uri)
            db = cluster[db_name]
            collection = db['ysab']
            collection.insert_one(form_data)
           # make html application w/ user responses
            make_app_form(form_data)

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
            make_prog_form(form_data)

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
            make_ext_form(form_data)

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

@app.route('/download_application')
def download_file_a():
    p = r'templates/ysab-application-record.html'
    return send_file(p, as_attachment=True)

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
    app.run(debug=True)
