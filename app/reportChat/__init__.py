from flask import Blueprint

reportChat_bp = Blueprint('reportChat', __name__, template_folder='templates', static_folder='static')

from app.reportChat import routes