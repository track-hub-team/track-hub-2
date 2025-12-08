from app.modules.versioning.models import DatasetVersion
from core.repositories.BaseRepository import BaseRepository


class VersioningRepository(BaseRepository):
    def __init__(self):
        super().__init__(DatasetVersion)

    def get_versions_by_dataset(self, dataset_id: int):
        """Obtener todas las versiones de un dataset"""
        return self.model.query.filter_by(dataset_id=dataset_id).order_by(DatasetVersion.created_at.desc()).all()

    def get_latest_version(self, dataset_id: int):
        """Obtener la última versión"""
        return self.model.query.filter_by(dataset_id=dataset_id).order_by(DatasetVersion.created_at.desc()).first()

    def get_version_by_number(self, dataset_id: int, version_number: str):
        """Obtener versión específica por número"""
        return self.model.query.filter_by(dataset_id=dataset_id, version_number=version_number).first()
