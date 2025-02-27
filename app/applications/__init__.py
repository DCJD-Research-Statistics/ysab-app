from flask import Blueprint

main = Blueprint('applications', __name__)

from app.main import routes
