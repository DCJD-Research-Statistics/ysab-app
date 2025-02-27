from flask import Blueprint

main = Blueprint('applications_table', __name__)

from app.main import routes
