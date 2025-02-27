from flask import Blueprint, render_template, session, redirect, url_for, flash, request, send_file, jsonify
from app.utils import admin_required, login_required, get_app_num, get_timestamp, app_id, make_app_form, is_admin, is_deputy, ext_id
from pymongo import MongoClient
import requests
import os

db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")
discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL_DEV")

external = Blueprint('external', __name__)


@external.route('/external')
@login_required
def external_form():
    return render_template('external/external.html')

@external.route('/submit_external_form', methods=['POST'])
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
            return render_template('confirmations/confirmation_e.html', name=name, email=email)
        except Exception as e:
            # return jsonify({'success': False, 'error': str(e)})
             return render_template('main/error.html', error=str(e))

@external.route('/download_external_form')
def download_file_e():
    p = r'templates/ysab-external-record.html'
    return send_file(p, as_attachment=True)