from flask_restful import Api

from app.modules.dashboard.api import init_blueprint_api
from core.blueprints.base_blueprint import BaseBlueprint

dashboard_bp = BaseBlueprint("dashboard", __name__, template_folder="templates")


api = Api(dashboard_bp)
init_blueprint_api(api)
