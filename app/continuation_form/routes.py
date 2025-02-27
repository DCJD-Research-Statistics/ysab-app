from flask import Blueprint, render_template, session, redirect, url_for, flash, request, send_file
from app.utils import login_required, get_app_num, get_timestamp, app_id, make_app_form, cont_id, make_cont_form
from pymongo import MongoClient
import requests
import os
from make_pdf_app import make_pdf

db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")


continuation = Blueprint('continuation', __name__)

@continuation.route('/submit_continuation_form', methods=['POST'])
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
            return render_template('continuation_form/confirmation_c.html', name=name, email=email)
        except Exception as e:
            # return jsonify({'success': False, 'error': str(e)})
             return render_template('main/error.html', error=str(e))
        
@continuation.route('/download_continuation_form')
def download_file_c():
    p = r'templates/ysab-continuation-record.html'
    return send_file(p, as_attachment=True)