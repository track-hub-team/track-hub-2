from app.modules.explore.repositories import ExploreRepository
from core.services.BaseService import BaseService


class ExploreService(BaseService):
    def __init__(self):
        super().__init__(ExploreRepository())

    def filter(
        self,
        query="",
        sorting="newest",
        publication_type="any",
        tags=[],
        **kwargs
    ):
        # Obtener datasets UVL
        uvl_datasets = self.repository.filter(
            query=query,
            sorting=sorting,
            publication_type=publication_type,
            tags=tags,
            **kwargs
        )
        
        # Obtener datasets GPX
        from app.modules.gpx.services import GPXDatasetService
        gpx_service = GPXDatasetService()
        gpx_datasets = gpx_service.get_all()
        
        # Filtrar GPX por query si existe
        if query:
            gpx_datasets = [
                ds for ds in gpx_datasets 
                if query.lower() in ds.gpx_meta_data.name.lower()
            ]
        
        # Combinar datasets
        all_datasets = list(uvl_datasets) + list(gpx_datasets)
        
        # Ordenar según el parámetro
        if sorting == "newest":
            all_datasets.sort(key=lambda x: x.created_at, reverse=True)
        elif sorting == "oldest":
            all_datasets.sort(key=lambda x: x.created_at)
        
        return all_datasets

    def get_all(self):
        """Get all datasets (UVL + GPX)"""
        uvl_datasets = self.repository.get_all()
        
        from app.modules.gpx.services import GPXDatasetService
        gpx_service = GPXDatasetService()
        gpx_datasets = gpx_service.get_all()
        
        all_datasets = list(uvl_datasets) + list(gpx_datasets)
        all_datasets.sort(key=lambda x: x.created_at, reverse=True)
        
        return all_datasets