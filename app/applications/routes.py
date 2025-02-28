from flask import Blueprint, render_template, session, redirect, url_for, flash, request, send_file
from app.utils import login_required, get_app_num, get_timestamp, app_id, make_app_form
from pymongo import MongoClient
import requests
import os
from make_pdf_app import make_pdf

db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")


applications = Blueprint('applications', __name__)


@applications.route('/application')
@login_required
def application():
    # Check if the user's email ends with 'dallascounty.org'
    if not session['user']['email'].endswith('dallascounty.org'):
        flash('Access denied. You must have a dallascounty.org email to access this page.', 'error')
        return redirect(url_for('home'))  # Redirect to home or another appropriate page
    return render_template('applications/application.html')

@applications.route('/submit_application_form', methods=['POST'])
def submit_application_form():
        try:     
            # Get form data
            form_data = request.form.to_dict()
            name = request.form.get('name')
            email = request.form.get('email')
            
            form_data = {'_id': app_id(), 'timestamp': get_timestamp(), **form_data}

            # Insert data into MongoDB - application
            with MongoClient(mongo_uri) as client:
                db = client[db_name]
                collection = db['ysab-applications']
                collection.insert_one(form_data)

                # Log the status change in activities collection
                db['activities'].insert_one({
                    'timestamp': get_timestamp(),
                    'type': 'Application Submission',
                    'description': f'New application submitted by {name} ({email})',
                    'user': email
                })

            # return jsonify({'success': True, 'message': 'Form data submitted successfully'})
            return render_template('confirmations/confirmation_a.html', name=name, email=email)
        except Exception as e:
            # return jsonify({'success': False, 'error': str(e)})
            return render_template('main/error.html', error=str(e))
        
@applications.route('/edit-application/<application_id>/<application_type>')
def edit_application(application_id, application_type):
    cluster = MongoClient(mongo_uri)
    db = cluster[db_name]

    if application_type == 'Internal Application':
        collection = db['ysab-applications']
    elif application_type == 'External Application':
        collection = db['ysab-external']
    else:
        return render_template('main/error.html', error='Invalid application type')

    application = collection.find_one({'_id': application_id})

    if application is None:
        return render_template('main/error.html', error='Application not found')
    else:
        # Render template based on application type
        if application_type == 'External Application':
            return render_template('applications/edit-external-application.html', application=application, application_type=application_type, edit_mode=True)
        elif application_type == 'Internal Application':
            return render_template('applications/edit-application.html', application=application, application_type=application_type, edit_mode=True)
        else:
            return render_template('main/error.html', error='Invalid application type')

@applications.route('/update_application', methods=['POST'])
def update_application():
    try:
        # Get form data
        updated_data = request.form.to_dict()
        name = request.form.get('name')
        email = request.form.get('email')
        application_id = request.form.get('_id')
        application_type = request.form.get('application_type')

        # Convert numeric fields to appropriate types
        numeric_fields = ['amount', 'cost1', 'cost2', 'cost3', 'cost4', 'cost5', 'cost6', 'cost7',
                         'items1', 'items2', 'items3', 'items4', 'items5', 'items6', 'items7',
                         'total1', 'total2', 'total3', 'total4', 'total5', 'total6', 'total7',
                         'grandTotal', 'youth_total', 'benefit_per_youth']

        # Update timestamp
        updated_data['timestamp'] = get_timestamp()
        
        cluster = MongoClient(mongo_uri)
        db = cluster[db_name]

        if application_type == 'Internal Application':
            collection = db['ysab-applications']
        elif application_type == 'External Application':
            collection = db['ysab-external']
        else:
            return render_template('main/error.html', error='Invalid application type')

        # Remove '_id' from updated_data to prevent attempting to modify the immutable field
        updated_data.pop('_id', None)

        # Fetch the current document to check existing values
        current_doc = collection.find_one({'_id': application_id})
        print(f"Found document with ID {application_id}: {current_doc is not None}")
        
        if current_doc:
            # Update 'edited' and 'num_edits' fields
            updated_data['edited'] = 'yes'
            current_edits = current_doc.get('num_edits', 0)
            print(f"Current num_edits: {current_edits} (type: {type(current_edits)})")
            # Ensure current_edits is an integer before adding 1
            current_edits = int(current_edits) if current_edits else 0
            updated_data['num_edits'] = current_edits + 1
            print(f"New num_edits: {updated_data['num_edits']} (type: {type(updated_data['num_edits'])})")
        else:
            # Set initial values for new documents
            updated_data['edited'] = 'no'
            updated_data['num_edits'] = 0
            print("New document, setting initial values")

        # Debug: Print final data before update
        print("Final data to be saved:")
        for key, value in updated_data.items():
            if key in numeric_fields:
                print(f"{key}: {value} (type: {type(value)})")

        # Update the existing record
        try:
            result = collection.update_one(
                {'_id': application_id},
                {'$set': updated_data},
                upsert=True
            )
            print(f"Update result: modified_count={result.modified_count}, upserted_id={result.upserted_id}")
        except Exception as e:
            print(f"Error during database update: {str(e)}")
            raise

        if result.modified_count == 0 and result.upserted_id is None:
            print("No changes made to the application")
            return render_template('main/error.html', error='No changes made to the application')

        # Log the status change in activities collection
        try:
            activity_log = {
                'timestamp': get_timestamp(),
                'type': 'Application Update',
                'description': f'Application {application_id} updated by {name} ({email})',
                'user': email
            }
            print(f"Logging activity: {activity_log}")
            db['activities'].insert_one(activity_log)
            print("Activity logged successfully")
        except Exception as e:
            print(f"Error logging activity: {str(e)}")
            # Continue even if activity logging fails

        print(f"Returning confirmation template for {application_type}")
        if application_type == 'Internal Application':
            return render_template('confirmations/confirmation_a.html', name=name, email=email)
        elif application_type == 'External Application':
            return render_template('confirmations/confirmation_e.html', name=name, email=email)

    except Exception as e:
        # Ensure the error is converted to string before passing to template
        error_message = str(e)
        print(f"Exception caught: {error_message}")
        print(f"Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return render_template('main/error.html', error=error_message)

@applications.route('/download_application')
def download_file_a():
    p = r'templates/ysab-application-record.html'
    return send_file(p, as_attachment=True)
