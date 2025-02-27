from flask import Blueprint, render_template, session
from app.utils import login_required
from pymongo import MongoClient
import os

db_name = os.getenv("DB_NAME")
mongo_uri = os.getenv("MONGO_URI")

notifications = Blueprint('notifications', __name__)


@notifications.route('/notifications')
@login_required
def view_notifications():
    with MongoClient(mongo_uri) as client:
        db = client[db_name]
        # Filter activities for current user
        user_activities = list(db['activities'].find(
            {'user': session['user']['email']},
            {'_id': 0}
        ).sort('timestamp', -1))
        
    return render_template('main/notifications.html', 
                         user_activities=user_activities)
