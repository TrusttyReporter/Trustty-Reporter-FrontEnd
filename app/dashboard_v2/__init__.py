from flask import Blueprint

dashboard_v2_bp = Blueprint('dashboard_v2', __name__, template_folder='templates', static_folder='static')

from app.dashboard_v2 import routes