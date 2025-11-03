from flask import render_template, redirect, url_for, request, jsonify, send_file
from flask_login import login_required, current_user
from app.modules.gpx import gpx_bp
from app.modules.gpx.services import GPXDatasetService
from app.modules.dataset.services import VersionService
from app.modules.gpx.forms import GPXUploadForm, GPXEditForm
from app.modules.gpx.parsers.gpx_parser import parse_gpx_file
from werkzeug.utils import secure_filename
import io
from app import db

gpx_dataset_service = GPXDatasetService()


@gpx_bp.route('/gpx/<int:dataset_id>')
def show_gpx(dataset_id):
    """Show GPX dataset details"""
    dataset = gpx_dataset_service.get_by_id(dataset_id)
    if not dataset:
        return "GPX dataset not found", 404
    
    # Get version history
    versions = VersionService.get_versions(dataset_id)
    
    return render_template('gpx/show.html', dataset=dataset, versions=versions)


@gpx_bp.route('/gpx/<int:dataset_id>/download')
def download_gpx(dataset_id):
    """Download GPX file"""
    version_number = request.args.get('version', type=int)
    
    dataset = gpx_dataset_service.get_by_id(dataset_id)
    if not dataset:
        return "GPX dataset not found", 404
    
    # Download specific version if requested
    if version_number:
        version = VersionService.get_version(dataset_id, version_number)
        if not version:
            return "Version not found", 404
        gpx_content = version.gpx_content
        filename = f"{dataset.gpx_meta_data.name}_v{version_number}.gpx"
    else:
        # Download current version
        gpx_content = dataset.gpx_meta_data.gpx_content
        filename = f"{dataset.gpx_meta_data.name}.gpx"
    
    filename = filename.replace(' ', '_')
    
    return send_file(
        io.BytesIO(gpx_content.encode('utf-8')),
        mimetype='application/gpx+xml',
        as_attachment=True,
        download_name=filename
    )


@gpx_bp.route('/gpx/<int:dataset_id>/versions')
@login_required
def list_versions(dataset_id):
    """Show version history"""
    dataset = gpx_dataset_service.get_by_id(dataset_id)
    if not dataset:
        return "GPX dataset not found", 404
    
    versions = VersionService.get_versions(dataset_id)
    
    return render_template('gpx/versions.html', dataset=dataset, versions=versions)


@gpx_bp.route('/gpx/<int:dataset_id>/versions/<int:version_number>/restore', methods=['POST'])
@login_required
def restore_version(dataset_id, version_number):
    """Restore to a previous version"""
    dataset = gpx_dataset_service.get_by_id(dataset_id)
    
    # Check permissions
    if dataset.user_id != current_user.id:
        return "Unauthorized", 403
    
    try:
        VersionService.restore_version(dataset_id, version_number)
        return redirect(url_for('gpx.show_gpx', dataset_id=dataset_id))
    except ValueError as e:
        return str(e), 404
    
@gpx_bp.route('/gpx/upload', methods=['GET', 'POST'])
@login_required
def upload_gpx():
    """Upload new GPX track"""
    form = GPXUploadForm()
    
    if form.validate_on_submit():
        gpx_file = form.gpx_file.data
        
        try:
            # Read and parse GPX file
            gpx_content = gpx_file.read().decode('utf-8')
            gpx_data = parse_gpx_file(gpx_content)
            
            # Create dataset
            dataset = gpx_dataset_service.create_from_upload(
                user_id=current_user.id,
                name=form.name.data,
                difficulty=form.difficulty.data if form.difficulty.data else None,
                description=form.description.data,
                gpx_content=gpx_content,
                gpx_data=gpx_data
            )
            
            # Create initial version
            VersionService.create_version(dataset, "Initial upload")
            
            return redirect(url_for('gpx.show_gpx', dataset_id=dataset.id))
            
        except Exception as e:
            form.gpx_file.errors.append(f"Error parsing GPX file: {str(e)}")
    
    return render_template('gpx/upload.html', form=form)


@gpx_bp.route('/gpx/<int:dataset_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_gpx(dataset_id):
    """Edit GPX dataset metadata"""
    dataset = gpx_dataset_service.get_by_id(dataset_id)
    if not dataset:
        return "GPX dataset not found", 404
    
    # Check permissions
    if dataset.user_id != current_user.id:
        return "Unauthorized", 403
    
    form = GPXEditForm()
    
    if request.method == 'GET':
        # Pre-fill form with current data
        form.name.data = dataset.gpx_meta_data.name
        form.difficulty.data = dataset.gpx_meta_data.difficulty.value if dataset.gpx_meta_data.difficulty else ''
    
    if form.validate_on_submit():
        # Update metadata
        from app.modules.gpx.models import GPXDifficultyRating
        
        dataset.gpx_meta_data.name = form.name.data
        dataset.gpx_meta_data.difficulty = GPXDifficultyRating[form.difficulty.data] if form.difficulty.data else None
        # ✅ CORRECCIÓN: No guardamos description para GPX
        
        db.session.commit()
        
        # Create new version
        from app.modules.dataset.services import VersionService
        VersionService.create_version(
            dataset,
            form.changelog.data,
            user_id=current_user.id
        )
        
        return redirect(url_for('gpx.show_gpx', dataset_id=dataset.id))
    
    # Contar versiones
    version_count = dataset.versions.count()
    
    return render_template('gpx/edit.html', form=form, dataset=dataset, version_count=version_count)