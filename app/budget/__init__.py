from flask import Blueprint

main = Blueprint('budget_dashboard', __name__)

from app.main import routes