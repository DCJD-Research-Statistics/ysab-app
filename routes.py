from flask import render_template, session, redirect, url_for, abort, flash, request
from pymongo import MongoClient
from functools import wraps
import requests

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def register_routes(app):

    def get_db():
        """Get MongoDB connection dynamically based on the app config."""
        client = MongoClient(app.config['MONGO_URI'])
        return client[app.config['DB_NAME']]

    @app.route('/my-applications')
    @login_required
    def my_applications():
        if 'user' not in session:
            return redirect(url_for('login'))

        user_email = app.config.get('EMAIL') if app.config['DB_NAME'] == app.config.get("DB_NAME_DEV") else session['user']['email']
        admin_emails = app.config['ADMIN_EMAILS']
        deputy_emails = app.config['DEPUTY_EMAILS']

        # Check admin access
        if user_email.lower() not in [email.lower() for email in admin_emails]:
            abort(403, description="Unauthorized Access")

        # Connect to MongoDB
        db = get_db()
        collection = db['ysab-applications']
        external_collection = db['ysab-external']

        # Fetch applications
        user_applications = list(collection.find({'email': {'$regex': f'^{user_email}$', '$options': 'i'}}))
        user_external_applications = list(external_collection.find({'email': {'$regex': f'^{user_email}$', '$options': 'i'}}))

        # Combine and format applications
        all_applications = user_applications + user_external_applications
        applications = format_applications(user_applications, user_external_applications, all_applications)

        if not all_applications:
            return render_template('my_applications.html', message="No records found.")
        
        return render_template('my_applications.html', applications=applications, admin_emails=admin_emails, deputy_emails=deputy_emails)

    def format_applications(user_apps, external_apps, all_apps):
        """Format applications for rendering."""
        formatted = []
        for app in all_apps:
            app_type = 'Internal Application' if app in user_apps else 'External Application'
            formatted.append({
                'id': str(app['_id']),
                'submission_date': app['timestamp'],
                'title': app['title'],
                'type': app_type,
                'application_status': app.get('application_status', 'pending')
            })
        return formatted
