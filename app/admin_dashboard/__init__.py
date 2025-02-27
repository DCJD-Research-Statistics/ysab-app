from flask import Blueprint

main = Blueprint('admin_dashboard', __name__)

from app.main import routes
