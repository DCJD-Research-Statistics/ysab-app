from flask import render_template, redirect, url_for, session
from app.main import main
import os
from pymongo import MongoClient

mongo_uri = os.getenv("MONGO_URI")

@main.route("/", methods=['GET', 'POST'])
def index():
    user = session.get('user') 
    return render_template('main/landing.html', user=user)


@main.route("/home", methods=['GET', 'POST'])
def home():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    
    with MongoClient(mongo_uri) as client:
        db_name = os.getenv("DB_NAME")
        db = client[db_name]
        config = db['config'].find_one({'name': 'application_status'})
        application_enabled = config['value'] if config else False

    return render_template('main/home.html', user=session.get('user'), application_enabled=application_enabled)

@main.route('/help')
def help():
    return render_template('main/help.html', user=session.get('user'))
