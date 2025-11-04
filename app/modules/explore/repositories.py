from sqlalchemy import any_, or_, and_
from app.modules.dataset.models import Author, BaseDataset, DSMetaData, PublicationType
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from core.repositories.BaseRepository import BaseRepository
import logging

logger = logging.getLogger(__name__)


class ExploreRepository(BaseRepository):
    def __init__(self):
        super().__init__(BaseDataset)

    def filter(
        self,
        query="",
        sorting="newest",
        publication_type="any",
        tags=[],
        dataset_type="all",
        **kwargs
    ):
        """Filtra datasets según múltiples criterios."""
        
        # Consulta base
        filters = []
        
        # ✅ FILTRO OBLIGATORIO: Solo datasets con DOI (sincronizados)
        filters.append(DSMetaData.dataset_doi.isnot(None))
        filters.append(DSMetaData.dataset_doi != '')
        
        # Filtro por tipo de dataset
        if dataset_type != "all":
            filters.append(BaseDataset.dataset_kind == dataset_type)
            logger.info(f"Filtering by dataset_kind: {dataset_type}")
        
        # Filtro por texto de búsqueda
        if query:
            search_filter = or_(
                DSMetaData.title.ilike(f"%{query}%"),
                DSMetaData.description.ilike(f"%{query}%")
            )
            filters.append(search_filter)
        
        # Filtro por tipo de publicación
        if publication_type != "any":
            filters.append(DSMetaData.publication_type == publication_type)
        
        # Filtro por tags
        if tags and len(tags) > 0:
            tag_filters = [DSMetaData.tags.ilike(f"%{tag}%") for tag in tags]
            filters.append(or_(*tag_filters))
        
        # Filtros específicos para GPX
        if dataset_type == "gpx":
            if kwargs.get('activity_type') and kwargs.get('activity_type') != 'any':
                activity = kwargs.get('activity_type')
                filters.append(FMMetaData.tags.ilike(f"%{activity}%"))
        
        # Construir query
        datasets_query = (
            self.model.query
            .join(BaseDataset.ds_meta_data)
            .filter(*filters)
        )
        
        # Ordenamiento
        if sorting == "newest":
            datasets_query = datasets_query.order_by(BaseDataset.created_at.desc())
        elif sorting == "oldest":
            datasets_query = datasets_query.order_by(BaseDataset.created_at.asc())
        elif sorting == "title":
            datasets_query = datasets_query.order_by(DSMetaData.title.asc())
        elif sorting == "downloads":
            datasets_query = datasets_query.order_by(BaseDataset.id.desc())
        
        logger.info(f"Query built with {len(filters)} filters")
        return datasets_query.all()