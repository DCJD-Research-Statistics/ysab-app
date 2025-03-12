from flask import Blueprint, render_template, session, request, jsonify
from app.utils import admin_required, login_required, get_timestamp
from pymongo import MongoClient
import os
from datetime import datetime
from bson import ObjectId

db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")


admin_dashboard = Blueprint('admin_dashboard', __name__)


@admin_dashboard.route('/dashboard')
@login_required
@admin_required
def dashboard():
    with MongoClient(mongo_uri) as client:
        # use ysab main db
        db = client[db_name]
                
        # Fetch date range from the database
        date_range = db['date-range'].find_one()
        begin_date_str = datetime.strptime(date_range['begin_date'], '%Y-%m-%d').strftime('%m/%d/%Y') if date_range else None
        end_date_str = datetime.strptime(date_range['end_date'], '%Y-%m-%d').strftime('%m/%d/%Y') if date_range else None

        begin_date = datetime.strptime(begin_date_str, '%m/%d/%Y') if begin_date_str and isinstance(begin_date_str, str) else None
        end_date = datetime.strptime(end_date_str, '%m/%d/%Y') if end_date_str and isinstance(end_date_str, str) else None
        
        # Get recent activities
        activities = list(db['activities'].find())
        # Convert timestamps to datetime and sort manually
        activities.sort(key=lambda x: datetime.strptime(x['timestamp'], "%m-%d-%Y %H:%M"), reverse=True)
        # Get the most recent 5 activities
        recent_activities = activities[:5]

        app_submissions_query = {}
        if begin_date and end_date:
            app_submissions_query = {
                'timestamp': {
                    '$gte': begin_date.strftime('%m-%d-%Y %H:%M'),
                    '$lte': end_date.strftime('%m-%d-%Y %H:%M')
                }
            }
        elif begin_date:
            app_submissions_query = {
                'timestamp': {
                    '$gte': begin_date.strftime('%m-%d-%Y %H:%M')
                }
            }
        elif end_date:
            app_submissions_query = {
                'timestamp': {
                    '$lte': end_date.strftime('%m-%d-%Y %H:%M')
                }
            }

        app_submissions_query['application_status'] = 'submitted'

        initial_review_query = app_submissions_query.copy()
        initial_review_query['application_status'] = 'initial-review'

        deputy_review_query = app_submissions_query.copy()
        deputy_review_query['application_status'] = 'deputy-review'

        budget_review_query = app_submissions_query.copy()
        budget_review_query['application_status'] = 'budget-review'

        approved_query = app_submissions_query.copy()
        approved_query['application_status'] = 'approved'

        timeline_stats = {
            'app_submissions': db['ysab-applications'].count_documents(app_submissions_query),
            'initial_review': db['ysab-applications'].count_documents(initial_review_query),
            'deputy_review': db['ysab-applications'].count_documents(deputy_review_query),
            'final_review': db['ysab-applications'].count_documents(budget_review_query),
            'approved': db['ysab-applications'].count_documents(approved_query)
        }

    
        return render_template('admin/admin_dashboard.html',
                             recent_activities=recent_activities,
                             timeline_stats=timeline_stats,
                             begin_date_str=begin_date_str,
                             end_date_str=end_date_str)
    
@admin_dashboard.route('/admin/applications')
@login_required
@admin_required
def all_applications():
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
        return render_template('admin/admin_applications.html', message=message)
    
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

    return render_template('admin/admin_applications.html', applications=applications)

@admin_dashboard.route('/admin/manage-applications')
@login_required
@admin_required
def manage_applications():
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
            'submission_date': datetime.strptime(app['timestamp'], "%m-%d-%Y %H:%M"),
            'name': app.get('name', 'N/A'),
            'title': app.get('title', 'N/A'),
            'type': 'Internal Application' if app in all_internal_applications else 'External Application',
            'application_status': app.get('application_status', 'pending')
        })

    # Sort by submission date (newest first)
    applications.sort(key=lambda x: x['submission_date'], reverse=True)

    return render_template('admin/manage_applications.html', applications=applications)

@admin_dashboard.route('/update_application_status', methods=['POST'])
@login_required
def update_application_status():
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
                'user': session['user']['email'],
                'read': False
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

@admin_dashboard.route('/admin/manage_users')
@login_required
@admin_required
def manage_users():
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        users = list(db['users'].find())
    return render_template('admin/manage_users.html', users=users)

@admin_dashboard.route('/delete_user', methods=['POST'])
@login_required
@admin_required
def delete_user():
    user_email = request.form.get('user_email')
    
    try:
        with MongoClient(mongo_uri) as client:
            db = client[db_name]
            result = db['users'].delete_one({'email': user_email})
            return jsonify({'success': result.deleted_count > 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_dashboard.route('/update_user_status', methods=['POST'])
@login_required
@admin_required
def update_user_status():
    user_id = request.form.get('user_id')
    approved = request.form.get('approved') == 'true'

    try:
        with MongoClient(mongo_uri) as client:
            db = client[db_name]
            result = db['users'].update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'approved': approved}}
            )
            return jsonify({'success': result.modified_count > 0})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def sort_by_timestamp(activity):
    from datetime import datetime
    return datetime.strptime(activity['timestamp'], "%m-%d-%Y %H:%M")

@admin_dashboard.route('/admin/activity-dashboard')
@login_required
@admin_required
def activity_dashboard():
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        
        # Get all activities
        activities = list(db['activities'].find())
        # Convert timestamps to datetime and sort manually
        activities.sort(key=sort_by_timestamp, reverse=True)
        
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
        
        # Get count of application submissions instead of the list
        application_submissions_count = db['activities'].count_documents({'type': 'Application Submission'})
        
        return render_template(
            'admin/activity_dashboard.html',
            activities=activities[:100],  # Show last 100 activities
            total_activities=total_activities,
            activity_types=activity_types,
            unique_users=unique_users,
            daily_activity_data={
                'dates': formatted_dates,
                'counts': activity_counts
            },
            application_submissions=application_submissions_count  # Now just the count value
        )
    
@admin_dashboard.route('/admin/manage_application_status')
@login_required
@admin_required
def manage_application_status():
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        # Fetch the current application status from the database
        # Assuming you have a collection named 'config' with a document like {'application_status': True/False}
        config = db['config'].find_one({'name': 'application_status'})
        application_enabled = config['value'] if config else False

    return render_template('admin/manage_application_status.html', application_enabled=application_enabled)

@admin_dashboard.route('/update_application_status_config', methods=['POST'])
@login_required
@admin_required
def update_application_status_config():
    try:
        print("Received request to update application status")
        application_enabled = request.form.get('application_enabled')
        print(f"application_enabled: {application_enabled}")
        application_enabled = application_enabled == 'true'
        client = MongoClient(mongo_uri)
        db_name = os.getenv("DB_NAME")
        db = client[db_name]

        # Update the application status in the config collection
        result = db['config'].update_one(
            {'name': 'application_status'},
            {'$set': {'value': application_enabled}},
            upsert=True  # Creates the document if it doesn't exist
        )

        if result.modified_count > 0 or result.upserted_id:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Application status update failed'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        client.close()

@admin_dashboard.route('/admin/manage_date_range')
@login_required
@admin_required
def manage_date_range():
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        date_range = db['date-range'].find_one()
        begin_date = date_range['begin_date'] if date_range else None
        end_date = date_range['end_date'] if date_range else None
        text = date_range['text'] if date_range else None

    return render_template('admin/manage_date_range.html', begin_date=begin_date, end_date=end_date, text=text)

@admin_dashboard.route('/update_date_range', methods=['POST'])
@login_required
@admin_required
def update_date_range():
    try:
        begin_date = request.form.get('begin_date')
        end_date = request.form.get('end_date')
        text = request.form.get('text')

        client = MongoClient(mongo_uri)
        db_name = os.getenv("DB_NAME")
        db = client[db_name]

        db['date-range'].update_one(
            {},
            {'$set': {'begin_date': begin_date, 'end_date': end_date, 'text': text}},
            upsert=True
        )

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@admin_dashboard.route('/admin/adjust_division_allocations')
@login_required
@admin_required
def adjust_division_allocations():
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        allocations = db['division-allocations'].find_one()
        if allocations:
            allocations.pop('_id', None)
        else:
            allocations = {
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
                'Clinical Services': 0
            }

    total = sum(int(value) for value in allocations.values())
    return render_template('admin/adjust_division_allocations.html', allocations=allocations, total=total)

@admin_dashboard.route('/update_division_allocations', methods=['POST'])
@login_required
def update_division_allocations():
    try:
        client = MongoClient(mongo_uri)
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        allocations = request.form.to_dict()

        # Update the division allocations in the database
        result = db['division-allocations'].update_one(
            {},
            {'$set': allocations},
            upsert=True
        )

        if result.modified_count > 0 or result.upserted_id:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Division allocations update failed'})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        client.close()
        client.close()