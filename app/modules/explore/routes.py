from flask import render_template, request, jsonify
from app.modules.explore import explore_bp
from app.modules.explore.forms import ExploreForm
from app.modules.explore.services import ExploreService

explore_service = ExploreService()


@explore_bp.route('/explore', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        query = request.args.get('query', '')
        form = ExploreForm()
        return render_template('explore/index.html', form=form, query=query)

    if request.method == 'POST':
        criteria = request.get_json()
        
        # ✨ NUEVO: Paginación
        page = criteria.get('page', 1)
        per_page = criteria.get('per_page', 20)  # 20 datasets por página
        
        # Obtener datasets filtrados
        datasets = explore_service.filter(**criteria)
        
        # Calcular paginación
        total = len(datasets)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_datasets = datasets[start:end]
        
        # Serializar datasets
        serialized_datasets = [
            serialize_dataset(dataset) 
            for dataset in paginated_datasets
        ]
        
        return jsonify({
            'datasets': serialized_datasets,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        })


def serialize_dataset(dataset):
    """Serialize dataset for JSON response - works for both UVL and GPX"""
    
    if dataset.dataset_type == 'gpx':
        # GPX dataset
        return {
            'id': dataset.id,
            'dataset_type': 'gpx',
            'title': dataset.gpx_meta_data.name,  # ← GPX usa .name
            'created_at': dataset.created_at.strftime('%Y-%m-%d'),
            'user_id': dataset.user_id,
            
            # GPX specific fields
            'difficulty': dataset.gpx_meta_data.difficulty.value if dataset.gpx_meta_data.difficulty else None,
            'length_3d': dataset.gpx_meta_data.length_3d,
            'uphill': dataset.gpx_meta_data.uphill,
            'downhill': dataset.gpx_meta_data.downhill,
            'moving_time': dataset.gpx_meta_data.moving_time,
            'max_elevation': dataset.gpx_meta_data.max_elevation,
            'hikr_user': dataset.gpx_meta_data.hikr_user,
            'hikr_url': dataset.gpx_meta_data.hikr_url,
        }
    
    elif dataset.dataset_type == 'uvl':
        # UVL dataset
        return {
            'id': dataset.id,
            'dataset_type': 'uvl',
            'title': dataset.ds_meta_data.title,  # ← UVL usa .title
            'created_at': dataset.created_at.strftime('%Y-%m-%d'),
            'user_id': dataset.user_id,
            
            # UVL specific fields
            'description': dataset.ds_meta_data.description,
            'publication_type': dataset.ds_meta_data.publication_type.value if dataset.ds_meta_data.publication_type else None,
            'tags': dataset.ds_meta_data.tags,
            'authors': [
                {
                    'name': author.name,
                    'affiliation': author.affiliation,
                    'orcid': author.orcid
                }
                for author in dataset.ds_meta_data.authors
            ] if dataset.ds_meta_data.authors else [],
        }
    
    else:
        # Fallback for unknown types
        return {
            'id': dataset.id,
            'dataset_type': dataset.dataset_type,
            'title': 'Unknown Dataset',
            'created_at': dataset.created_at.strftime('%Y-%m-%d'),
            'user_id': dataset.user_id,
        }