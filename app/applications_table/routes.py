from flask import Blueprint, render_template, session, redirect, url_for, flash, request, send_file, jsonify
from app.utils import admin_required, login_required, get_app_num, get_timestamp, app_id, make_app_form, make_ext_form
from pymongo import MongoClient
import requests
import os
from make_pdf_app import make_pdf
from bson import ObjectId
from app.config import admin_mode_switch

# admin_mode_switch = os.getenv('admin_mode_switch')

db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")


applications_table = Blueprint('applications_table', __name__)

@applications_table.route('/my-applications')
@login_required
def my_applications(admin_mode=admin_mode_switch):
    if 'user' not in session:
        return redirect(url_for('login'))
        
    if admin_mode==True:
        user_email = os.getenv("EMAIL")
    elif admin_mode==False: 
        user_email = session['user']['email']

    # Connect to MongoDB
    client = MongoClient(mongo_uri)

    # Choose database based on admin status
    admin_emails = os.getenv("ADMIN_EMAILS").split(',')
    if user_email.lower() in [email.lower() for email in admin_emails]:
        db = client[os.getenv("DB_NAME_DEV")]
    else:
        db = client[os.getenv("DB_NAME")]

    collection = db['ysab-applications']

    # Fetch applications for the current user from 'ysab' collection
    user_applications = list(collection.find(
        {'$or': [
            {'email': {'$regex': f'^{user_email}$', '$options': 'i'}},
            {'added_collaborator': {'$regex': f'^{user_email}$', '$options': 'i'}}
        ]},
        {'_id': 1, 'timestamp': 1, 'title': 1, 'application_status': 1}
    ))

    # Fetch applications for the current user from 'ysab-external' collection
    external_collection = db['ysab-external']
    user_external_applications = list(external_collection.find(
        {'$or': [
            {'email': {'$regex': f'^{user_email}$', '$options': 'i'}},
            {'added_collaborator': {'$regex': f'^{user_email}$', '$options': 'i'}}
        ]},
        {'_id': 1, 'timestamp': 1, 'title': 1, 'application_status': 1}
    ))

    # Combine both application lists
    all_applications = user_applications + user_external_applications

    if not all_applications:
        message = "No records found."
        return render_template('applications/my_applications.html', message=message)
    
    # Format the data for the template
    applications = []
    for app in all_applications:
        # Check if the application is from user_applications or user_external_applications
        if app in user_applications:
            app_type = 'Internal Application'
        elif app in user_external_applications:
            app_type = 'External Application'
        else:
            app_type = 'Unknown'

        applications.append({
            'id': str(app['_id']),
            'submission_date': app['timestamp'],
            'title': app['title'],
            'type': app_type,
            'application_status': app.get('application_status', 'pending')
        })

    client.close()

    return render_template('applications/my_applications.html', applications=applications)

@applications_table.route('/download_application_fromtable/<application_id>/<format>')
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

@applications_table.route('/download_external_fromtable/<application_id>')
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
    
@applications_table.route('/share-application/<application_id>', methods=['POST'])
@login_required
def share_application(application_id):
    data = request.get_json()
    collaborator_email = data.get('email')
    
    if not collaborator_email:
        return jsonify({'success': False, 'message': 'Email is required'}), 400

    # Connect to MongoDB
    client = MongoClient(mongo_uri)
    db = client[db_name]
    collection = db['ysab-applications']

    # Update the application record with the new collaborator
    result = collection.update_one(
        {'_id': application_id},
        {'$set': {'added_collaborator': collaborator_email}}
    )

    client.close()

    if result.matched_count == 0:
        return jsonify({'success': False, 'message': 'Application not found'}), 404

    flash('Collaborator added successfully.', 'success')
    return jsonify({'success': True})