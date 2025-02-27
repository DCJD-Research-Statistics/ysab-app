from flask import Flask, session, g
import secrets
from app.auth.routes import auth
from app.applications.routes import applications
from app.progress_reports.routes import progress_reports
from app.external_form.routes import external
from app.continuation_form.routes import continuation
from app.admin_dashboard.routes import admin_dashboard
from app.main.routes import main as main_blueprint
from app.notifications.routes import notifications
from app.applications_table.routes import applications_table
from app.budget.routes import budget_dashboard
import os
from pymongo import MongoClient
from app.config import DevelopmentConfig, ProductionConfig


def create_app(config_class=None):
    app = Flask(__name__)
    config_class = config_class or (DevelopmentConfig if os.getenv('FLASK_ENV') == 'development' else ProductionConfig)
    app.config.from_object(config_class)
    app.secret_key = os.getenv("SECRET_KEY", secrets.token_hex(16))


    # Register Blueprints
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(applications, url_prefix='/applications')
    app.register_blueprint(progress_reports, url_prefix='/progress-reports')
    app.register_blueprint(admin_dashboard, url_prefix='/admin-dashboard')
    app.register_blueprint(budget_dashboard, url_prefix='/budget-dashboard')
    app.register_blueprint(main_blueprint)
    app.register_blueprint(notifications, url_prefix='/notifications')
    app.register_blueprint(applications_table, url_prefix='/applications_table')
    app.register_blueprint(external, url_prefix='/external')
    app.register_blueprint(continuation, url_prefix='/continuation')

    # Context processor to inject shared data
    @app.context_processor
    def inject_common_data():

        # Get admin emails from environment variable and split into a list
        ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',')
        DEPUTY_EMAILS = os.getenv('DEPUTY_EMAILS', '').split(',')
        user_activities = []

        user_email = session.get('user', {}).get('email')

        if user_email:
            with MongoClient(app.config['MONGO_URI']) as client:
                db = client[app.config['DB_NAME']]
                # Filter activities for current user
                user_activities = list(db['activities'].find(
                    {'user': session['user']['email']},
                    {'_id': 0}
                ).sort('timestamp', -1))


        return {
            "admin_emails": ADMIN_EMAILS,
            "deputy_emails": DEPUTY_EMAILS,
            "user_activities": user_activities,
            "user": session.get('user')
        }

    return app
