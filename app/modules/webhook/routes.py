import os

from dotenv import load_dotenv
from flask import abort, request

from app.modules.webhook import webhook_bp
from app.modules.webhook.services import WebhookService

load_dotenv()

WEBHOOK_TOKEN = os.getenv("WEBHOOK_TOKEN")


@webhook_bp.route("/webhook/deploy", methods=["POST"])
def deploy():

    token = request.headers.get("Authorization")
    if token != f"Bearer {WEBHOOK_TOKEN}":
        abort(403, description="Unauthorized")

    service = WebhookService()

    web_container = service.get_web_container()

    service.execute_container_command(web_container, "/app/scripts/git_update.sh")

    service.execute_container_command(web_container, "pip install -r requirements.txt")

    service.execute_container_command(web_container, "flask db upgrade")

    service.log_deployment(web_container)

    service.restart_container(web_container)

    return "Deployment successful", 200
