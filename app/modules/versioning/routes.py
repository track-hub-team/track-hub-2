import logging
from flask import jsonify, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from app.modules.versioning import versioning_bp
from app.modules.versioning.services import VersionService
from app.modules.versioning.models import DatasetVersion
from app.modules.dataset.models import BaseDataset
from app.modules.zenodo.services import ZenodoService

logger = logging.getLogger(__name__)
zenodo_service = ZenodoService()


@versioning_bp.route("/dataset/<int:dataset_id>/versions")
def list_versions(dataset_id):
    """Ver historial de versiones de un dataset"""
    dataset = BaseDataset.query.get_or_404(dataset_id)
    
    versions = dataset.versions.order_by(DatasetVersion.created_at.desc()).all()
    
    return render_template("versioning/list_versions.html", dataset=dataset, versions=versions)


@versioning_bp.route("/versions/<int:version1_id>/compare/<int:version2_id>")
def compare_versions(version1_id, version2_id):
    """Comparar dos versiones de un dataset"""
    version1 = DatasetVersion.query.get_or_404(version1_id)
    version2 = DatasetVersion.query.get_or_404(version2_id)
    
    if version1.dataset_id != version2.dataset_id:
        flash("Versions must belong to the same dataset", "danger")
        abort(400)
    
    dataset = version1.dataset
    all_versions = (
        DatasetVersion.query.filter_by(dataset_id=dataset.id)
        .order_by(DatasetVersion.created_at.desc())
        .all()
    )
    
    # Asegurar orden correcto (más reciente primero)
    if version1.created_at < version2.created_at:
        version1, version2 = version2, version1
    
    comparison = VersionService.compare_versions(version1.id, version2.id)
    
    return render_template(
        "versioning/compare_versions.html",
        dataset=dataset,
        version1=version1,
        version2=version2,
        comparison=comparison,
        all_versions=all_versions,
    )


@versioning_bp.route("/dataset/<int:dataset_id>/create_version", methods=["POST"])
@login_required
def create_version(dataset_id):
    """Crear una nueva versión manualmente (solo propietario)"""
    dataset = BaseDataset.query.get_or_404(dataset_id)
    
    if dataset.user_id != current_user.id:
        abort(403)
    
    changelog = request.form.get("changelog", "").strip()
    bump_type = request.form.get("bump_type", "patch")
    
    if not changelog:
        flash("Changelog is required", "warning")
        if dataset.ds_meta_data.dataset_doi:
            return redirect(url_for("dataset.subdomain_index", doi=dataset.ds_meta_data.dataset_doi))
        else:
            return redirect(url_for("dataset.get_unsynchronized_dataset", dataset_id=dataset_id))
    
    if bump_type not in ["major", "minor", "patch"]:
        bump_type = "patch"
    
    try:
        version = VersionService.create_version(dataset, changelog, current_user, bump_type)
        
        # Sincronizar con Zenodo si está publicado
        if dataset.ds_meta_data.dataset_doi and dataset.ds_meta_data.deposition_id:
            try:
                zenodo_service.create_new_version(dataset.ds_meta_data.deposition_id, dataset, version)
                flash(f"Version {version.version_number} created in local and Zenodo! 🎉", "success")
            except Exception as ze:
                logger.error(f"Zenodo version creation failed: {str(ze)}")
                flash(
                    f"Version {version.version_number} created locally, but Zenodo sync failed",
                    "warning"
                )
        else:
            flash(f"Version {version.version_number} created successfully! 🎉", "success")
    
    except Exception as e:
        flash(f"Error creating version: {str(e)}", "danger")
        logger.error(f"Error creating version for dataset {dataset_id}: {str(e)}")
    
    return redirect(url_for("versioning.list_versions", dataset_id=dataset_id))


@versioning_bp.route("/api/dataset/<int:dataset_id>/versions")
def api_list_versions(dataset_id):
    """API para obtener versiones de un dataset (JSON)"""
    dataset = BaseDataset.query.get_or_404(dataset_id)
    
    versions = [v.to_dict() for v in dataset.versions.all()]
    
    return jsonify({
        "dataset_id": dataset_id,
        "version_count": len(versions),
        "versions": versions
    })


@versioning_bp.route("/api/version/<int:version_id>")
def api_get_version(version_id):
    """Obtener detalles de una versión específica (JSON)"""
    version = DatasetVersion.query.get_or_404(version_id)
    
    return jsonify(version.to_dict())
