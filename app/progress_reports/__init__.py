from flask import Blueprint

main = Blueprint('progress_reports', __name__)

from app.main import routes
