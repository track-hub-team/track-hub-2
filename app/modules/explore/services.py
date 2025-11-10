import logging

from app.modules.explore.repositories import ExploreRepository
from core.services.BaseService import BaseService

logger = logging.getLogger(__name__)


class ExploreService(BaseService):
    def __init__(self):
        super().__init__(ExploreRepository())

    def filter(self, query="", sorting="newest", publication_type="any", tags=[], dataset_type="all", **kwargs):
        """
        Filtra datasets según criterios.

        Args:
            query: Texto de búsqueda
            sorting: Criterio de ordenamiento
            publication_type: Tipo de publicación
            tags: Lista de tags
            dataset_type: Tipo de dataset (all, uvl, gpx, etc.)
            **kwargs: Filtros específicos por tipo
        """
        logger.info(f"Filtering datasets: type={dataset_type}, query={query}")

        return self.repository.filter(
            query=query,
            sorting=sorting,
            publication_type=publication_type,
            tags=tags,
            dataset_type=dataset_type,
            **kwargs,
        )
