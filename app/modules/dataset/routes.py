import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from zipfile import ZipFile

from flask import abort, flash, jsonify, make_response, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required

from app import db
from app.modules.dataset import dataset_bp
from app.modules.dataset.forms import DataSetForm
from app.modules.dataset.models import BaseDataset, DSDownloadRecord
from app.modules.dataset.services import (
    AuthorService,
    DataSetService,
    DOIMappingService,
    DSDownloadRecordService,
    DSMetaDataService,
    DSViewRecordService,
    calculate_checksum_and_size,
)
from app.modules.recommendation.services import RecommendationService
from app.modules.versioning.services import VersionService
from app.modules.zenodo.services import ZenodoService

logger = logging.getLogger(__name__)


dataset_service = DataSetService()
author_service = AuthorService()
dsmetadata_service = DSMetaDataService()
zenodo_service = ZenodoService()
doi_mapping_service = DOIMappingService()
ds_view_record_service = DSViewRecordService()
recommendation_service = RecommendationService()


@dataset_bp.route("/dataset/upload", methods=["GET", "POST"])
@login_required
def create_dataset():
    form = DataSetForm()

    if request.method == "GET":
        temp_folder = current_user.temp_folder()
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder)
        os.makedirs(temp_folder, exist_ok=True)

    if request.method == "POST":
        dataset = None

        if not form.validate_on_submit():
            return jsonify({"message": form.errors}), 400

        try:
            logger.info("Creating dataset...")
            dataset = dataset_service.create_from_form(form=form, current_user=current_user)
            logger.info(f"Created dataset: {dataset}")
            dataset_service.move_feature_models(dataset)
        except Exception as exc:
            logger.exception(f"Exception while create dataset data in local {exc}")
            return jsonify({"Exception while create dataset data in local: ": str(exc)}), 400

        # send dataset as deposition to Zenodo
        data = {}
        try:
            zenodo_response_json = zenodo_service.create_new_deposition(dataset)
            response_data = json.dumps(zenodo_response_json)
            data = json.loads(response_data)
        except Exception as exc:
            data = {}
            zenodo_response_json = {}
            logger.exception(f"Exception while create dataset data in Zenodo {exc}")

        if data.get("conceptrecid"):
            deposition_id = data.get("id")

            # update dataset with deposition id in Zenodo
            dataset_service.update_dsmetadata(dataset.ds_meta_data_id, deposition_id=deposition_id)

            try:
                # iterate for each feature model (one feature model = one request to Zenodo)
                for feature_model in dataset.feature_models:
                    zenodo_service.upload_file(dataset, deposition_id, feature_model)

                # publish deposition
                zenodo_service.publish_deposition(deposition_id)

                # update DOI
                deposition_doi = zenodo_service.get_doi(deposition_id)
                dataset_service.update_dsmetadata(dataset.ds_meta_data_id, dataset_doi=deposition_doi)
            except Exception as e:
                msg = f"it has not been possible upload feature models in Zenodo and update the DOI: {e}"
                return jsonify({"message": msg}), 200

        # Delete temp folder
        file_path = current_user.temp_folder()
        if os.path.exists(file_path) and os.path.isdir(file_path):
            shutil.rmtree(file_path)

        msg = "Everything works!"
        return jsonify({"message": msg}), 200

    return render_template("dataset/upload_dataset.html", form=form)


@dataset_bp.route("/dataset/list", methods=["GET", "POST"])
@login_required
def list_dataset():
    return render_template(
        "dataset/list_datasets.html",
        datasets=dataset_service.get_synchronized(current_user.id),
        local_datasets=dataset_service.get_unsynchronized(current_user.id),
    )


@dataset_bp.route("/dataset/file/upload", methods=["POST"])
@login_required
def upload():
    """
    Endpoint unificado para subir archivos de cualquier tipo registrado.
    Valida extensión y contenido según el tipo.
    Además, evita mezclar archivos GPX y UVL en la misma carpeta temporal.
    """
    import os

    from werkzeug.utils import secure_filename

    from app.modules.dataset.registry import (
        get_allowed_extensions,
        get_descriptor,
        infer_kind_from_filename,
    )

    # 1. Verificar que hay archivo
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"message": "No file provided"}), 400

    # 2. Validar extensión contra tipos registrados
    allowed_exts = tuple(get_allowed_extensions())
    filename = file.filename or ""

    if not any(filename.lower().endswith(ext) for ext in allowed_exts):
        return (
            jsonify({"message": f"Invalid file type. Allowed: {', '.join(allowed_exts)}"}),
            400,
        )

    # 3. Carpeta temporal del usuario
    temp_folder = current_user.temp_folder()
    os.makedirs(temp_folder, exist_ok=True)

    # 3.1 NUEVO: comprobar si ya hay archivos y su tipo
    existing_files = [f for f in os.listdir(temp_folder) if any(f.lower().endswith(ext) for ext in allowed_exts)]

    new_file_kind = infer_kind_from_filename(filename)

    if existing_files:
        # Tomamos el primero como referencia del tipo actual del dataset
        first_file_kind = infer_kind_from_filename(existing_files[0])
        if first_file_kind != new_file_kind:
            return (
                jsonify(
                    {
                        "message": (
                            "Este Dataset ya contiene archivos de tipo "
                            f"{first_file_kind.upper()}, no se pueden mezclar "
                            f"con archivos de tipo {new_file_kind.upper()}."
                        )
                    }
                ),
                400,
            )

    # 4. Guardar en carpeta temporal del usuario
    new_filename = secure_filename(filename)
    file_path = os.path.join(temp_folder, new_filename)
    file.save(file_path)

    # 5. Inferir tipo y validar contenido
    kind = infer_kind_from_filename(new_filename)
    descriptor = get_descriptor(kind)

    try:
        descriptor.handler.validate(file_path)
    except Exception as e:
        # Limpieza en caso de error
        if os.path.exists(file_path):
            os.remove(file_path)

        logger.error(f"Validation failed for {new_filename}: {e}")
        return jsonify({"message": f"Validation failed: {str(e)}"}), 400

    # 6. Respuesta exitosa
    return (
        jsonify(
            {
                "message": "File uploaded and validated successfully",
                "filename": new_filename,
                "file_type": kind,
            }
        ),
        200,
    )


@dataset_bp.route("/dataset/file/delete", methods=["POST"])
def delete():
    data = request.get_json()
    filename = data.get("file")
    temp_folder = current_user.temp_folder()
    filepath = os.path.join(temp_folder, filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"message": "File deleted successfully"})

    return jsonify({"error": "Error: File not found"})


@dataset_bp.route("/dataset/download/<int:dataset_id>", methods=["GET"])
def download_dataset(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)

    file_path = f"uploads/user_{dataset.user_id}/dataset_{dataset.id}/"

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, f"dataset_{dataset_id}.zip")

    with ZipFile(zip_path, "w") as zipf:
        for subdir, dirs, files in os.walk(file_path):
            for file in files:
                full_path = os.path.join(subdir, file)

                relative_path = os.path.relpath(full_path, file_path)

                zipf.write(
                    full_path,
                    arcname=os.path.join(os.path.basename(zip_path[:-4]), relative_path),
                )

    user_cookie = request.cookies.get("download_cookie")
    if not user_cookie:
        user_cookie = str(uuid.uuid4())  # Generate a new unique identifier if it does not exist
        # Save the cookie to the user's browser
        resp = make_response(
            send_from_directory(
                temp_dir,
                f"dataset_{dataset_id}.zip",
                as_attachment=True,
                mimetype="application/zip",
            )
        )
        resp.set_cookie("download_cookie", user_cookie)
    else:
        resp = send_from_directory(
            temp_dir,
            f"dataset_{dataset_id}.zip",
            as_attachment=True,
            mimetype="application/zip",
        )

    # Check if the download record already exists for this cookie
    existing_record = DSDownloadRecord.query.filter_by(
        user_id=current_user.id if current_user.is_authenticated else None,
        dataset_id=dataset_id,
        download_cookie=user_cookie,
    ).first()

    if not existing_record:
        # Record the download in your database
        DSDownloadRecordService().create(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset_id,
            download_date=datetime.now(timezone.utc),
            download_cookie=user_cookie,
        )

    return resp


@dataset_bp.route("/doi/<path:doi>/", methods=["GET"])
def subdomain_index(doi):

    # Check if the DOI is an old DOI
    new_doi = doi_mapping_service.get_new_doi(doi)
    if new_doi:
        return redirect(url_for("dataset.subdomain_index", doi=new_doi), code=302)

    # Try to search the dataset by the provided DOI
    ds_meta_data = dsmetadata_service.filter_by_doi(doi)

    if not ds_meta_data:
        abort(404)

    # Get dataset
    dataset = ds_meta_data.data_set

    # Sincronizar metadatos desde Zenodo/Fakenodo antes de mostrar
    if dataset.ds_meta_data.deposition_id:
        try:
            logger.info(f"Syncing metadata from Zenodo for dataset {dataset.id}")
            zenodo_data = zenodo_service.get_deposition(dataset.ds_meta_data.deposition_id)

            if zenodo_data and "metadata" in zenodo_data:
                metadata = zenodo_data["metadata"]

                # Actualizar título si cambió
                if metadata.get("title") and metadata["title"] != dataset.ds_meta_data.title:
                    dataset.ds_meta_data.title = metadata["title"]

                # Actualizar descripción si cambió
                if metadata.get("description") and metadata["description"] != dataset.ds_meta_data.description:
                    dataset.ds_meta_data.description = metadata["description"]

                # Actualizar tags si cambiaron
                if metadata.get("keywords"):
                    zenodo_tags = [t for t in metadata["keywords"] if t.lower() != "uvlhub"]
                    new_tags = ", ".join(zenodo_tags)
                    if new_tags != (dataset.ds_meta_data.tags or ""):
                        dataset.ds_meta_data.tags = new_tags

                # NO actualizar el DOI desde Zenodo si ya tenemos uno más reciente
                zenodo_doi = zenodo_data.get("doi")
                local_doi = dataset.ds_meta_data.dataset_doi

                if zenodo_doi and local_doi:
                    zenodo_version = int(zenodo_doi.split(".v")[-1]) if ".v" in zenodo_doi else 1
                    local_version = int(local_doi.split(".v")[-1]) if ".v" in local_doi else 1

                    if zenodo_version > local_version:
                        dataset.ds_meta_data.dataset_doi = zenodo_doi
                elif zenodo_doi and not local_doi:
                    dataset.ds_meta_data.dataset_doi = zenodo_doi

                db.session.commit()
                logger.info("Metadata synced successfully from Zenodo")
        except Exception as e:
            logger.error(f"Failed to sync metadata from Zenodo: {str(e)}")

    # Save the cookie to the user's browser
    user_cookie = ds_view_record_service.create_cookie(dataset=dataset)
    related = recommendation_service.get_related_datasets(dataset, limit=6)

    resp = make_response(
        render_template(
            "dataset/view_dataset.html",
            dataset=dataset,
            related_datasets=related,
        )
    )
    resp.set_cookie("view_cookie", user_cookie)

    return resp


@dataset_bp.route("/dataset/unsynchronized/<int:dataset_id>/", methods=["GET"])
@login_required
def get_unsynchronized_dataset(dataset_id):

    # Get dataset
    dataset = dataset_service.get_unsynchronized_dataset(current_user.id, dataset_id)

    if not dataset:
        abort(404)

    related = recommendation_service.get_related_datasets(dataset, limit=6)

    return render_template(
        "dataset/view_dataset.html",
        dataset=dataset,
        related_datasets=related,
        FLASK_ENV=os.getenv("FLASK_ENV", "development"),
    )


@dataset_bp.route("/dataset/<int:dataset_id>/related", methods=["GET"])
def related_datasets_api(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)
    related = recommendation_service.get_related_datasets(dataset, limit=6)
    return jsonify(
        [
            {
                "id": d.id,
                "title": d.ds_meta_data.title,
                "dataset_doi": d.ds_meta_data.dataset_doi,
                "kind": d.dataset_kind,
            }
            for d in related
        ]
    )


@dataset_bp.route("/api/gpx/<int:file_id>")
def get_gpx_data(file_id):
    """Retorna datos parseados de un archivo GPX."""
    import logging
    import os

    from flask import current_app, jsonify

    from app.modules.dataset.handlers.gpx_handler import GPXHandler

    logger = logging.getLogger(__name__)

    try:
        from app import db

        # Obtener todo en una query
        result = db.session.execute(
            db.text(
                """
                SELECT
                    ds.user_id,
                    ds.id as dataset_id,
                    dsm.dataset_doi,
                    f.id as file_id,
                    f.name as file_name
                FROM feature_model fm
                JOIN data_set ds ON fm.data_set_id = ds.id
                LEFT JOIN ds_meta_data dsm ON ds.ds_meta_data_id = dsm.id
                LEFT JOIN file f ON f.feature_model_id = fm.id
                WHERE fm.fm_meta_data_id = :file_id
                LIMIT 1
            """
            ),
            {"file_id": file_id},
        ).first()

        if not result:
            return jsonify({"error": "File not found"}), 404

        user_id, dataset_id, dataset_doi, gpx_file_id, gpx_file_name = result

        # Verificar que sea GPX
        if not gpx_file_name or not gpx_file_name.lower().endswith(".gpx"):
            return jsonify({"error": "File is not a GPX file"}), 400

        # Verificar permisos
        if not dataset_doi:
            if not current_user.is_authenticated or user_id != current_user.id:
                return jsonify({"error": "Unauthorized"}), 403

        # ✅ Construir la ruta desde el directorio raíz del proyecto (sin /app)
        # current_app.root_path = /path/to/project/app
        # Necesitamos: /path/to/project/uploads
        project_root = os.path.dirname(current_app.root_path)

        file_path = os.path.join(project_root, "uploads", f"user_{user_id}", f"dataset_{dataset_id}", gpx_file_name)

        if not os.path.exists(file_path):
            logger.error(f"File not found at: {file_path}")
            return jsonify({"error": "File not found on disk"}), 404

        # Parsear el GPX
        handler = GPXHandler()
        gpx_data = handler.parse_gpx(file_path)

        if gpx_data is None:
            return jsonify({"error": "Invalid GPX file"}), 500

        return jsonify(gpx_data)

    except Exception as e:
        logger.error(f"Error parsing GPX {file_id}: {str(e)}")
        return jsonify({"error": f"Error processing GPX file: {str(e)}"}), 500


@dataset_bp.route("/dataset/<int:dataset_id>/edit", methods=["GET", "POST"])
@login_required
def edit_dataset(dataset_id):
    """Editar un dataset (synchronized o unsynchronized)"""
    dataset = BaseDataset.query.get_or_404(dataset_id)

    # Solo el propietario puede editar
    if dataset.user_id != current_user.id:
        abort(403)

    # Si es POST, procesar cambios
    if request.method == "POST":
        changes = []

        # 1. Actualizar título
        new_title = request.form.get("title", "").strip()
        if new_title and new_title != dataset.ds_meta_data.title:
            old_title = dataset.ds_meta_data.title
            dataset.ds_meta_data.title = new_title
            changes.append(f"Changed title from '{old_title}' to '{new_title}'")

        # 2. Actualizar descripción
        new_description = request.form.get("description", "").strip()
        if new_description and new_description != dataset.ds_meta_data.description:
            dataset.ds_meta_data.description = new_description
            changes.append("Updated description")

        # 3. Actualizar tags
        new_tags = request.form.get("tags", "").strip()
        if new_tags != (dataset.ds_meta_data.tags or ""):
            dataset.ds_meta_data.tags = new_tags
            changes.append("Updated tags")

        # 4. Subir nuevos archivos
        uploaded_files = request.files.getlist("files")
        if uploaded_files and uploaded_files[0].filename:
            from werkzeug.utils import secure_filename

            from app.modules.dataset.registry import get_descriptor, infer_kind_from_filename

            for file in uploaded_files:
                if not file.filename:
                    continue

                filename = secure_filename(file.filename)

                # Validar que el tipo coincida con el dataset
                file_kind = infer_kind_from_filename(filename)
                if file_kind != dataset.dataset_kind:
                    flash(
                        f"File type mismatch: {filename} is {file_kind.upper()} "
                        f"but dataset is {dataset.dataset_kind.upper()}",
                        "danger",
                    )
                    continue

                # Guardar archivo
                working_dir = os.getenv("WORKING_DIR", "")
                dest_dir = os.path.join(working_dir, "uploads", f"user_{current_user.id}", f"dataset_{dataset.id}")
                os.makedirs(dest_dir, exist_ok=True)

                file_path = os.path.join(dest_dir, filename)
                file.save(file_path)

                # Validar archivo
                descriptor = get_descriptor(file_kind)

                try:
                    descriptor.handler.validate(file_path)
                except Exception as e:
                    os.remove(file_path)
                    flash(f"File validation failed for {filename}: {str(e)}", "danger")
                    continue

                # Crear FMMetaData con publication_type obligatorio
                from app.modules.featuremodel.repositories import FeatureModelRepository, FMMetaDataRepository
                from app.modules.hubfile.repositories import HubfileRepository

                fmmetadata = FMMetaDataRepository().create(
                    commit=False,
                    filename=filename,
                    title=filename,
                    description="Added via edit",
                    publication_type="none",
                )

                fm = FeatureModelRepository().create(
                    commit=False, data_set_id=dataset.id, fm_meta_data_id=fmmetadata.id
                )

                checksum, size = calculate_checksum_and_size(file_path)

                HubfileRepository().create(
                    commit=False, name=filename, checksum=checksum, size=size, feature_model_id=fm.id
                )

                changes.append(f"Added file: {filename}")

                # Guardar cambios
        if changes:
            try:
                db.session.commit()

                # AUTO-VERSIONADO: Crear nueva versión automáticamente (PARA TODOS)
                try:
                    changelog = "Automatic version after edit:\n" + "\n".join(f"- {c}" for c in changes)

                    # Detectar tipo de cambio automáticamente
                    bump_type = "patch"

                    file_changes = [
                        c for c in changes if "Added file:" in c or "Removed file:" in c or "Modified file:" in c
                    ]
                    if file_changes:
                        bump_type = "major"
                    else:
                        metadata_changes = [c for c in changes if "title" in c.lower() or "description" in c.lower()]
                        if metadata_changes:
                            bump_type = "minor"

                    version = VersionService.create_version(
                        dataset=dataset, changelog=changelog, user=current_user, bump_type=bump_type
                    )

                    # Si está sincronizado con Zenodo, actualizar también allí
                    if dataset.ds_meta_data.dataset_doi and dataset.ds_meta_data.deposition_id:
                        try:
                            zenodo_service.create_new_version(dataset.ds_meta_data.deposition_id, dataset, version)
                            flash(f"Dataset and Zenodo updated! New version: v{version.version_number} 🎉", "success")
                        except Exception as ze:
                            logger.error(f"Zenodo sync failed: {str(ze)}")
                            flash(f"Dataset updated (v{version.version_number}), but Zenodo sync failed", "warning")
                    else:
                        flash(f"Dataset updated successfully! New version: v{version.version_number} 🎉", "success")

                except Exception as e:
                    logger.error(f"Could not create automatic version: {str(e)}")
                    flash("Dataset updated but version creation failed", "warning")

                # Redirigir según tipo
                if dataset.ds_meta_data.dataset_doi:
                    return redirect(url_for("dataset.subdomain_index", doi=dataset.ds_meta_data.dataset_doi))
                else:
                    return redirect(url_for("dataset.get_unsynchronized_dataset", dataset_id=dataset.id))

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating dataset {dataset_id}: {str(e)}")
                flash(f"Error updating dataset: {str(e)}", "danger")
        else:
            flash("No changes detected", "info")

    # GET: Mostrar formulario
    return render_template("dataset/edit_dataset.html", dataset=dataset)
