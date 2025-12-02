from flask import render_template

from app.modules.trending import trending_bp


@trending_bp.route("/trending", methods=["GET"])
def index():
    return render_template("trending/index.html")
