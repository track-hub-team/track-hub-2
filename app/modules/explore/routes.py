from flask import jsonify, render_template, request

from app.modules.explore import explore_bp
from app.modules.explore.forms import ExploreForm
from app.modules.explore.services import ExploreService


@explore_bp.route("/explore", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        # Obtener parámetros de query string
        query = request.args.get("query", "")
        dataset_type = request.args.get("dataset_type", "all")
        sorting = request.args.get("sorting", "newest")
        publication_type = request.args.get("publication_type", "any")
        tags_str = request.args.get("tags", "")

        # Filtros específicos GPX
        min_distance = request.args.get("min_distance", type=int)
        max_distance = request.args.get("max_distance", type=int)
        activity_type = request.args.get("activity_type", "any")

        tags = [tag.strip() for tag in tags_str.split(",")] if tags_str else []

        # Buscar datasets
        explore_service = ExploreService()
        datasets = explore_service.filter(
            query=query,
            sorting=sorting,
            publication_type=publication_type,
            tags=tags,
            dataset_type=dataset_type,
            min_distance=min_distance,
            max_distance=max_distance,
            activity_type=activity_type,
        )

        # Crear formulario con valores actuales
        form = ExploreForm(
            query=query,
            dataset_type=dataset_type,
            sorting=sorting,
            publication_type=publication_type,
            tags=tags_str,
            min_distance=min_distance,
            max_distance=max_distance,
            activity_type=activity_type,
        )

        return render_template("explore/index.html", form=form, datasets=datasets, dataset_type=dataset_type)

    return jsonify({"message": "Explore index"})
