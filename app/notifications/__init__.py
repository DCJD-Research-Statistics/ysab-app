from flask import Blueprint

main = Blueprint('notifications', __name__)

from app.main import routes
