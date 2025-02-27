from flask import Blueprint, render_template, session, redirect, url_for, flash, url_for, request, send_file
from app.utils import login_required, get_timestamp, progress_report_id, make_prog_form
from app.config import admin_mode_switch
from pymongo import MongoClient
import os
import requests

db_name = os.getenv("DB_NAME_DEV")
mongo_uri = os.getenv("MONGO_URI")
discord_webhook_url = os.getenv("DISCORD_WEBHOOK_URL_DEV")


progress_reports = Blueprint('progress_reports', __name__)


@progress_reports.route('/my_progress_report/<application_id>')
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
    admin_emails = os.getenv("ADMIN_EMAILS").split(',')
    if user_email.lower() in [email.lower() for email in admin_emails]:
        db = client[os.getenv("DB_NAME_DEV")]
    else:
        db = client[os.getenv("DB_NAME")]
    collection = db['progress_reports']

    # Fetch progress reports for the given application_id
    progress_reports = list(collection.find({'application_id': application_id}))

    client.close()

    if not progress_reports:
        message = "No progress reports found for this application."
        return render_template('progress_reports/my_progress_report.html', message=message)

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
    return render_template('progress_reports/my_progress_report.html', progress_reports=progress_reports)


@progress_reports.route('/progress-report-selection', methods=['GET'])
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

    return render_template('progress_reports/progress_report_selection.html', applications=applications)

@progress_reports.route('/progress-report-router/<application_id>/<reporting_interval>')
@login_required
def progress_report_router(application_id, reporting_interval):
    if reporting_interval == 'Quarterly':
        return redirect(url_for('progress_reports.select_quarter', application_id=application_id))
    elif reporting_interval in ['Bi-annually', '>Bi-annually']:
        return redirect(url_for('progress_reports.select_biannual', application_id=application_id))
    elif reporting_interval in ['Annually', '>Annually']:
        return redirect(url_for('progress_reports.progress_report_annual', application_id=application_id))
    else:
        flash('Invalid reporting interval', 'error')
        return redirect(url_for('progress_reports.progress_report_selection'))
    
@progress_reports.route('/select-quarter/<application_id>')
@login_required
def select_quarter(application_id):
    return render_template('progress_reports/select_quarter.html', application_id=application_id)

@progress_reports.route('/select-biannual/<application_id>')
@login_required
def select_biannual(application_id):
    return render_template('progress_reports/select_biannual.html', application_id=application_id)

@progress_reports.route('/progress-report-qt/<application_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('progress_reports.progress_report_selection'))

    # Get user information from the session
    user = session.get('user', {})
    name = user.get('name', '')
    email = user.get('email', '')

    # Determine which template to use based on the reporting period
    if reporting_period == 'q1':
        template = 'progress_reports/progress-report-qt.html'
    elif reporting_period == 'q2':
        template = 'progress_reports/progress-report-qt2.html'
    elif reporting_period == 'q3':
        template = 'progress_reports/progress-report-qt3.html'
    elif reporting_period == 'q4':
        template = 'progress_reports/progress-report-qt4.html'
    else:
        flash('Invalid reporting period', 'error')
        return redirect(url_for('progress_reports.select_quarter', application_id=application_id))

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

@progress_reports.route('/progress-report-bi/<application_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('progress_reports.select_biannual', application_id=application_id))
    
    client.close()

    if not application:
        flash('Application not found', 'error')
        return redirect(url_for('progress_reports.progress_report_selection'))

    # Get user information from the session
    user = session.get('user', {})
    name = user.get('name', '')
    email = user.get('email', '')

    # Determine which template to use based on the reporting period
    if reporting_period == 'mid_year':
        template = 'progress_reports/progress-report-bi.html'
    elif reporting_period == 'end_year':
        template = 'progress_reports/progress-report-end_year.html'
    else:
        flash('Invalid reporting period', 'error')
        return redirect(url_for('progress_reports.select_biannual', application_id=application_id))

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

@progress_reports.route('/progress-report-annual/<application_id>', methods=['GET', 'POST'])
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
        return redirect(url_for('progress_reports.progress_report_selection'))

    # Get user information from the session
    user = session.get('user', {})
    name = user.get('name', '')
    email = user.get('email', '')
    reporting_period = 'Annually'

    # Render the annual progress report template with auto-filled information
    return render_template('progress_reports/progress-report-annual.html',
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

@progress_reports.route('/submit_progress_report', methods=['POST'])
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

        return render_template('comfirmations/confirmation_p.html', name=name, email=email)
    except Exception as e:
        return render_template('main/error.html', error=str(e))
    
@progress_reports.route('/download_progress_report')
def download_file_p():
    p = r'templates/progress-report-copy-record.html'
    return send_file(p, as_attachment=True)

@progress_reports.route('/download_progress_report/<application_id>')
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