import logging
from flask import render_template
from flask_login import login_required, current_user

from app.modules.dashboard import dashboard_bp

logger = logging.getLogger(__name__)


@dashboard_bp.route("/dashboard", methods=["GET"])
@login_required
def index():
    """
    Renderiza la página principal del Dashboard.
    Aquí añadiremos métricas o estadísticas personalizadas.
    """
    logger.info(f"User {current_user.id} accessed My Dashboard")

    # 🔹 Datos de ejemplo (luego los obtendremos de la base de datos)
    uploads = 27
    downloads = 1200
    syncs = 83

    weeks = ["Semana 1", "Semana 2", "Semana 3", "Semana 4"]
    downloads_per_week = [320, 400, 280, 500]

    top_datasets = {
        "Dataset 1": 43,
        "Dataset 2": 30,
        "Dataset 3": 16
    }

    return render_template(
        "dashboard/dashboard.html",
        uploads=uploads,
        downloads=downloads,
        syncs=syncs,
        weeks=weeks,
        downloads_per_week=downloads_per_week,
        top_datasets=top_datasets
    )
