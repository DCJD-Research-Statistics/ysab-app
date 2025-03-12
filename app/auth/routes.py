from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils import login_required, get_timestamp
from pymongo import MongoClient
import requests
import os

db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').lower()
        password = request.form.get('password')

        # MongoDB connection
        client = MongoClient(mongo_uri)
        db = client[db_name]
        users_collection = db['users']

        user = users_collection.find_one({'email': email})
        
        if user:
            if check_password_hash(user['password'], password):
                if user.get('approved', False):  # Check if the account is approved
                    session['user'] = {'name': user['name'], 'email': user['email']}
                    flash('Logged in successfully', 'success')
                    return redirect(url_for('main.home'))
                else:
                    flash('Your account is pending approval.', 'error')
            else:
                flash('Invalid email or password', 'error')
        else:
            flash('Invalid email or password', 'error')

    return render_template('auth/login.html')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email').lower()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/signup.html')
        
        # MongoDB connection
        client = MongoClient(mongo_uri)
        db = client[db_name]
        users_collection = db['users']

        existing_user = users_collection.find_one({'email': email})
        if existing_user:
            flash('Email already exists', 'error')
            return render_template('auth/signup.html')

        hashed_password = generate_password_hash(password)
        
        # Determine approval status based on email domain
        is_approved = email.endswith('@dallascounty.org')

        new_user = {
            'name': name,
            'email': email,
            'password': hashed_password,
            'approved': is_approved
        }
        users_collection.insert_one(new_user)

        # Log the status change in activities collection
        db['activities'].insert_one({
            'timestamp': get_timestamp(),
            'type': 'User Signup',
            'description': f'New user account created for {name} ({email}) - Approved: {is_approved}',
            'user': email,
            'read': False
        })

        # Redirect based on approval status
        if is_approved:
            flash('Account created successfully. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Your account is pending review. Please check back after one business day.', 'info')
            return redirect(url_for('auth.signup_pending'))

    # If it's a GET request, just render the signup template
    return render_template('auth/signup.html')

@auth.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('main.index'))

@auth.route('/signup_pending')
def signup_pending():
    return render_template('auth/signup_pending.html')
