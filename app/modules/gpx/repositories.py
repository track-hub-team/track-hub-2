from app.modules.gpx.models import GPXDataset, GPXMetaData
from app.modules.dataset.models import Author
from core.repositories.BaseRepository import BaseRepository


class GPXMetaDataRepository(BaseRepository):
    def __init__(self):
        super().__init__(GPXMetaData)
    
    def get_by_hikr_id(self, hikr_id: str):
        """Get GPX metadata by hikr.org ID"""
        return self.model.query.filter_by(hikr_id=hikr_id).first()
    
    def get_all_with_dataset(self):
        """Get all GPX metadata with their datasets"""
        from app.modules.gpx.models import GPXDataset
        return self.model.query.join(GPXDataset).all()


class GPXDatasetRepository(BaseRepository):
    def __init__(self):
        super().__init__(GPXDataset)
    
    def get_all_with_metadata(self):
        """Get all GPX datasets with their metadata"""
        return self.model.query.join(GPXMetaData).all()
    
    def get_by_user(self, user_id: int):
        """Get GPX datasets by user"""
        from app.modules.dataset.models import BaseDataset
        return self.model.query.join(BaseDataset).filter(
            BaseDataset.user_id == user_id
        ).all()


class AuthorRepository(BaseRepository):
    def __init__(self):
        super().__init__(Author)
    
    def get_by_gpx_metadata(self, gpx_meta_data_id: int):
        """Get authors by GPX metadata ID"""
        return self.model.query.filter_by(gpx_meta_data_id=gpx_meta_data_id).all()