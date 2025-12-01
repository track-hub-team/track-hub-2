from flask import render_template

from app.modules.recommendation import recommendation_bp


@recommendation_bp.route("/recommendation", methods=["GET"])
def index():
    return render_template("recommendation/index.html")
