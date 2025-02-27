from flask import Blueprint

main = Blueprint('continuation_form', __name__)

from app.main import routes
