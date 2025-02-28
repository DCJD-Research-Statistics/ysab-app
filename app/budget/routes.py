from flask import Blueprint, render_template, session, redirect, url_for, flash, request, send_file, jsonify
from app.utils import is_admin, is_deputy
from pymongo import MongoClient
import requests
import os
from bson import ObjectId
from datetime import datetime


db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")


budget_dashboard = Blueprint('budget_dashboard', __name__)


@budget_dashboard.route('/dashboard')
def dashboard():
        # Check if user is either admin or deputy
    if not (is_admin(session['user']['email']) or is_deputy(session['user']['email'])):
        flash('Access denied. You must be an admin or deputy to access this page.', 'error')
        return redirect(url_for('home'))
    
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]

        # Fetch date range from the database
        date_range = db['date-range'].find_one()
        begin_date_str = datetime.strptime(date_range['begin_date'], '%Y-%m-%d').strftime('%m/%d/%Y') if date_range else None
        end_date_str = datetime.strptime(date_range['end_date'], '%Y-%m-%d').strftime('%m/%d/%Y') if date_range else None

        begin_date = datetime.strptime(begin_date_str, '%m/%d/%Y') if begin_date_str and isinstance(begin_date_str, str) else None
        end_date = datetime.strptime(end_date_str, '%m/%d/%Y') if end_date_str and isinstance(end_date_str, str) else None
        
        # Fetch allocated budgets from the database
        division_allocations = db['division-allocations'].find_one()
        if division_allocations:
            division_allocations.pop('_id', None)
            allocated_budgets = division_allocations
        else:
            # Define default allocated budgets if not found in the database
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
                'Clinical Services': 0
            }
        
        # Helper function to parse timestamp from various formats
        def parse_timestamp(timestamp_str):
            if not timestamp_str or timestamp_str == 'N/A':
                return None
                
            # Try different date formats
            formats_to_try = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d %H:%M:%S',
                '%m/%d/%Y %H:%M:%S',
                '%d-%b-%Y',  # e.g., 15-Jan-2023
                '%b %d, %Y'  # e.g., Jan 15, 2023
            ]
            
            for fmt in formats_to_try:
                try:
                    return datetime.strptime(timestamp_str, fmt)
                except ValueError:
                    continue
            
            # If we can't parse the timestamp, log it for debugging
            print(f"Could not parse timestamp: {timestamp_str}")
            return None
        
        # Create date filter query
        date_filter = {}
        
        # Only apply date filtering if we have valid date range
        if begin_date or end_date:
            # We'll filter applications in Python code since MongoDB timestamp format might vary
            print(f"Filtering by date range: {begin_date} to {end_date}")
        
        # Get all applications from both internal and external collections
        internal_apps = list(db['ysab-applications'].find({}, {
            'amount': 1,
            'service_area': 1,
            'title': 1,
            'timestamp': 1,
            'application_status': 1,
            'facility': 1
        }))
        
        external_apps = list(db['ysab-external'].find({}, {
            'amount': 1,
            'service_area': 1,
            'title': 1,
            'timestamp': 1,
            'application_status': 1,
            'facility': 1
        }))

        # Combine all applications
        all_applications = internal_apps + external_apps
        
        # Apply date filtering in Python if date range is specified
        # This will filter applications based on their timestamp to only include those
        # that fall within the specified date range. Applications with missing or
        # unparseable timestamps will be excluded to ensure accurate reporting.
        if begin_date or end_date:
            print(f"Original applications count: {len(all_applications)}")
            print(f"Date range: {begin_date} to {end_date}")
            
            # Sample a few timestamps to understand the format
            sample_timestamps = [app.get('timestamp') for app in all_applications[:5] if app.get('timestamp')]
            print(f"Sample timestamps: {sample_timestamps}")
            
            filtered_applications = []
            included_count = 0
            excluded_count = 0
            unparseable_count = 0
            
            for app in all_applications:
                timestamp_str = app.get('timestamp')
                if timestamp_str:
                    app_date = parse_timestamp(timestamp_str)
                    
                    # Only include application if it falls within the date range
                    if app_date:
                        include_app = False
                        
                        if begin_date and end_date:
                            if begin_date <= app_date <= end_date:
                                include_app = True
                        elif begin_date:
                            if begin_date <= app_date:
                                include_app = True
                        elif end_date:
                            if app_date <= end_date:
                                include_app = True
                        
                        if include_app:
                            filtered_applications.append(app)
                            included_count += 1
                        else:
                            excluded_count += 1
                            print(f"Excluded app with timestamp {timestamp_str} (parsed as {app_date})")
                    else:
                        # If we can't parse the timestamp, exclude it
                        excluded_count += 1
                        print(f"Excluded app with unparseable timestamp: {timestamp_str}")
                else:
                    # If no timestamp, exclude it
                    excluded_count += 1
                    print(f"Excluded app with no timestamp")
            
            # Replace all_applications with the filtered list
            all_applications = filtered_applications
            
            print(f"Filtered applications count: {len(all_applications)}")
            print(f"Included: {included_count}, Excluded: {excluded_count}, Unparseable: {unparseable_count}")

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
        # Initialize service_area_totals with all service areas from allocated_budgets
        for service_area in allocated_budgets:
            service_area_totals[service_area] = 0

        service_area_details = {}

        # Initialize service_area_details with all service areas from allocated_budgets
        for service_area in allocated_budgets:
            service_area_details[service_area] = {
                'applications': [],
                'total_requested': 0,
                'allocated_budget': allocated_budgets.get(service_area, 0)
            }
        
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
                'timestamp': app.get('timestamp', 'N/A'),
                'facility': app.get('facility', 'N/A')
            })
            service_area_details[service_area]['total_requested'] += amount

        # Get recent applications for the table
        recent_applications = sorted(
            all_applications,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )[:10]  # Get last 10 applications

        return render_template(
            'budget/budget_dashboard.html',
            total_requested=total_requested,
            total_approved=total_approved,
            service_area_totals=service_area_totals,
            service_area_details=service_area_details, 
            begin_date_str=begin_date_str,
            end_date_str=end_date_str
        )