from flask import Blueprint

main = Blueprint('external_form', __name__)

from app.main import routes
