from flask import Blueprint, render_template, session, request, jsonify, redirect, url_for
from app.utils import login_required
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")

notifications = Blueprint('notifications', __name__)

def parse_timestamp(timestamp_str):
    """Parse timestamp string in format 'MM-DD-YYYY HH:MM' to datetime object"""
    try:
        return datetime.strptime(timestamp_str, "%m-%d-%Y %H:%M")
    except ValueError:
        # Return a default old date if parsing fails
        return datetime(1900, 1, 1)


@notifications.route('/notifications')
@login_required
def view_notifications():
    with MongoClient(mongo_uri) as client:
        db = client[db_name]
        # Filter activities for current user
        user_activities = list(db['activities'].find(
            {'user': session['user']['email']},
            {'_id': 1, 'type': 1, 'description': 1, 'timestamp': 1, 'read': 1}
        ))
        
        # Convert ObjectId to string for JSON serialization
        for activity in user_activities:
            activity['_id'] = str(activity['_id'])
        
        # Sort activities by timestamp in descending order (newest first)
        user_activities.sort(key=lambda x: parse_timestamp(x.get('timestamp', '')), reverse=True)
        
    return render_template('main/notifications.html',
                         user_activities=user_activities)


@notifications.route('/notifications/unread')
@login_required
def get_unread_notifications():
    with MongoClient(mongo_uri) as client:
        db = client[db_name]
        # Filter unread activities for current user
        unread_activities = list(db['activities'].find(
            {'user': session['user']['email'], 'read': False},
            {'_id': 1, 'type': 1, 'description': 1, 'timestamp': 1, 'read': 1}
        ))
        
        # Convert ObjectId to string for JSON serialization
        for activity in unread_activities:
            activity['_id'] = str(activity['_id'])
        
        # Sort activities by timestamp in descending order (newest first)
        unread_activities.sort(key=lambda x: parse_timestamp(x.get('timestamp', '')), reverse=True)
        
    return jsonify(unread_activities)


@notifications.route('/notifications/mark-read/<notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    try:
        with MongoClient(mongo_uri) as client:
            db = client[db_name]
            # Mark notification as read
            result = db['activities'].update_one(
                {'_id': ObjectId(notification_id), 'user': session['user']['email']},
                {'$set': {'read': True}}
            )
            
            if result.modified_count > 0:
                return jsonify({'success': True, 'message': 'Notification marked as read'})
            else:
                return jsonify({'success': False, 'message': 'Notification not found or already read'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@notifications.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    try:
        with MongoClient(mongo_uri) as client:
            db = client[db_name]
            # Mark all notifications as read for the current user
            result = db['activities'].update_many(
                {'user': session['user']['email'], 'read': False},
                {'$set': {'read': True}}
            )
            
            if result.modified_count > 0:
                return jsonify({'success': True, 'message': f'{result.modified_count} notifications marked as read'})
            else:
                return jsonify({'success': False, 'message': 'No unread notifications found'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
