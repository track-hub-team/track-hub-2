from flask import Blueprint

gpx_bp = Blueprint('gpx', __name__, template_folder='templates')

from app.modules.gpx import routes