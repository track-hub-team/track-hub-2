from flask import render_template, redirect, url_for, request, jsonify, send_file
from flask_login import login_required, current_user
from app.modules.gpx import gpx_bp
from app.modules.gpx.services import GPXDatasetService
import io

gpx_dataset_service = GPXDatasetService()


@gpx_bp.route('/gpx/list')
def list_gpx():
    """List all GPX datasets"""
    datasets = gpx_dataset_service.get_all()  # ← Usar get_all()
    return render_template('gpx/list.html', datasets=datasets)


@gpx_bp.route('/gpx/<int:dataset_id>')
def show_gpx(dataset_id):
    """Show GPX dataset details"""
    dataset = gpx_dataset_service.get_by_id(dataset_id)
    if not dataset:
        return "GPX dataset not found", 404
    return render_template('gpx/show.html', dataset=dataset)


@gpx_bp.route('/gpx/<int:dataset_id>/download')
def download_gpx(dataset_id):
    """Download GPX file"""
    dataset = gpx_dataset_service.get_by_id(dataset_id)
    if not dataset or not dataset.gpx_meta_data.gpx_content:
        return "GPX file not found", 404
    
    filename = f"{dataset.gpx_meta_data.name}.gpx".replace(' ', '_')
    
    return send_file(
        io.BytesIO(dataset.gpx_meta_data.gpx_content.encode('utf-8')),
        mimetype='application/gpx+xml',
        as_attachment=True,
        download_name=filename
    )