import hashlib
import logging
import os
import shutil
import uuid
from typing import Optional

from flask import request
from app.modules.dataset.models import DatasetVersion, UVLVersion, GPXVersion, BaseDataset

from app.modules.auth.services import AuthenticationService
from app.modules.dataset.models import DataSet, DSMetaData, DSViewRecord
from app.modules.dataset.repositories import (
    AuthorRepository,
    DataSetRepository,
    DOIMappingRepository,
    DSDownloadRecordRepository,
    DSMetaDataRepository,
    DSViewRecordRepository,
)
from app.modules.featuremodel.repositories import FeatureModelRepository, FMMetaDataRepository
from app.modules.hubfile.repositories import (
    HubfileDownloadRecordRepository,
    HubfileRepository,
    HubfileViewRecordRepository,
)
from core.services.BaseService import BaseService
from app import db
from flask_login import current_user

logger = logging.getLogger(__name__)


def calculate_checksum_and_size(file_path):
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as file:
        content = file.read()
        hash_md5 = hashlib.md5(content).hexdigest()
        return hash_md5, file_size


class DataSetService(BaseService):
    def __init__(self):
        super().__init__(DataSetRepository())
        self.feature_model_repository = FeatureModelRepository()
        self.author_repository = AuthorRepository()
        self.dsmetadata_repository = DSMetaDataRepository()
        self.fmmetadata_repository = FMMetaDataRepository()
        self.dsdownloadrecord_repository = DSDownloadRecordRepository()
        self.hubfiledownloadrecord_repository = HubfileDownloadRecordRepository()
        self.hubfilerepository = HubfileRepository()
        self.dsviewrecord_repostory = DSViewRecordRepository()
        self.hubfileviewrecord_repository = HubfileViewRecordRepository()

    def move_feature_models(self, dataset: DataSet):
        current_user = AuthenticationService().get_authenticated_user()
        source_dir = current_user.temp_folder()

        working_dir = os.getenv("WORKING_DIR", "")
        dest_dir = os.path.join(working_dir, "uploads", f"user_{current_user.id}", f"dataset_{dataset.id}")

        os.makedirs(dest_dir, exist_ok=True)

        for feature_model in dataset.feature_models:
            uvl_filename = feature_model.fm_meta_data.uvl_filename
            shutil.move(os.path.join(source_dir, uvl_filename), dest_dir)

    def get_synchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_synchronized(current_user_id)

    def get_unsynchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_unsynchronized(current_user_id)

    def get_unsynchronized_dataset(self, current_user_id: int, dataset_id: int) -> DataSet:
        return self.repository.get_unsynchronized_dataset(current_user_id, dataset_id)

    def latest_synchronized(self):
        return self.repository.latest_synchronized()

    def count_synchronized_datasets(self):
        return self.repository.count_synchronized_datasets()

    def count_feature_models(self):
        return self.feature_model_service.count_feature_models()

    def count_authors(self) -> int:
        return self.author_repository.count()

    def count_dsmetadata(self) -> int:
        return self.dsmetadata_repository.count()

    def total_dataset_downloads(self) -> int:
        return self.dsdownloadrecord_repository.total_dataset_downloads()

    def total_dataset_views(self) -> int:
        return self.dsviewrecord_repostory.total_dataset_views()

    def create_from_form(self, form, current_user) -> DataSet:
        main_author = {
            "name": f"{current_user.profile.surname}, {current_user.profile.name}",
            "affiliation": current_user.profile.affiliation,
            "orcid": current_user.profile.orcid,
        }
        try:
            logger.info(f"Creating dsmetadata...: {form.get_dsmetadata()}")
            dsmetadata = self.dsmetadata_repository.create(**form.get_dsmetadata())
            for author_data in [main_author] + form.get_authors():
                author = self.author_repository.create(commit=False, ds_meta_data_id=dsmetadata.id, **author_data)
                dsmetadata.authors.append(author)

            dataset = self.create(commit=False, user_id=current_user.id, ds_meta_data_id=dsmetadata.id)

            for feature_model in form.feature_models:
                uvl_filename = feature_model.uvl_filename.data
                fmmetadata = self.fmmetadata_repository.create(commit=False, **feature_model.get_fmmetadata())
                for author_data in feature_model.get_authors():
                    author = self.author_repository.create(commit=False, fm_meta_data_id=fmmetadata.id, **author_data)
                    fmmetadata.authors.append(author)

                fm = self.feature_model_repository.create(
                    commit=False, data_set_id=dataset.id, fm_meta_data_id=fmmetadata.id
                )

                # associated files in feature model
                file_path = os.path.join(current_user.temp_folder(), uvl_filename)
                checksum, size = calculate_checksum_and_size(file_path)

                file = self.hubfilerepository.create(
                    commit=False, name=uvl_filename, checksum=checksum, size=size, feature_model_id=fm.id
                )
                fm.files.append(file)
            self.repository.session.commit()
        except Exception as exc:
            logger.info(f"Exception creating dataset from form...: {exc}")
            self.repository.session.rollback()
            raise exc
        return dataset

    def update_dsmetadata(self, id, **kwargs):
        return self.dsmetadata_repository.update(id, **kwargs)

    def get_uvlhub_doi(self, dataset: DataSet) -> str:
        domain = os.getenv("DOMAIN", "localhost")
        return f"http://{domain}/doi/{dataset.ds_meta_data.dataset_doi}"


class AuthorService(BaseService):
    def __init__(self):
        super().__init__(AuthorRepository())


class DSDownloadRecordService(BaseService):
    def __init__(self):
        super().__init__(DSDownloadRecordRepository())


class DSMetaDataService(BaseService):
    def __init__(self):
        super().__init__(DSMetaDataRepository())

    def update(self, id, **kwargs):
        return self.repository.update(id, **kwargs)

    def filter_by_doi(self, doi: str) -> Optional[DSMetaData]:
        return self.repository.filter_by_doi(doi)


class DSViewRecordService(BaseService):
    def __init__(self):
        super().__init__(DSViewRecordRepository())

    def the_record_exists(self, dataset: DataSet, user_cookie: str):
        return self.repository.the_record_exists(dataset, user_cookie)

    def create_new_record(self, dataset: DataSet, user_cookie: str) -> DSViewRecord:
        return self.repository.create_new_record(dataset, user_cookie)

    def create_cookie(self, dataset: DataSet) -> str:

        user_cookie = request.cookies.get("view_cookie")
        if not user_cookie:
            user_cookie = str(uuid.uuid4())

        existing_record = self.the_record_exists(dataset=dataset, user_cookie=user_cookie)

        if not existing_record:
            self.create_new_record(dataset=dataset, user_cookie=user_cookie)

        return user_cookie


class DOIMappingService(BaseService):
    def __init__(self):
        super().__init__(DOIMappingRepository())

    def get_new_doi(self, old_doi: str) -> str:
        doi_mapping = self.repository.get_new_doi(old_doi)
        if doi_mapping:
            return doi_mapping.dataset_doi_new
        else:
            return None


class SizeService:

    def __init__(self):
        pass

    def get_human_readable_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024**2:
            return f"{round(size / 1024, 2)} KB"
        elif size < 1024**3:
            return f"{round(size / (1024 ** 2), 2)} MB"
        else:
            return f"{round(size / (1024 ** 3), 2)} GB"
        
class VersionService:
    """Universal versioning service for all dataset types"""
    
    @staticmethod
    def create_version(dataset, changelog="Initial version", user_id=None):
        """Create a new version for any dataset type"""
        
        # Get current version number
        last_version = dataset.versions.order_by(DatasetVersion.version_number.desc()).first()
        new_version_number = (last_version.version_number + 1) if last_version else 1
        
        # Create version based on dataset type
        if dataset.dataset_type == 'gpx':
            return VersionService._create_gpx_version(dataset, new_version_number, changelog, user_id)
        elif dataset.dataset_type == 'uvl':
            return VersionService._create_uvl_version(dataset, new_version_number, changelog, user_id)
        else:
            raise ValueError(f"Unsupported dataset type: {dataset.dataset_type}")
    
    @staticmethod
    def _create_gpx_version(dataset, version_number, changelog, user_id=None):
        """Create version for GPX dataset"""
        
        # Determine user_id
        if user_id is None:
            # Try to get from current_user if available
            try:
                if current_user.is_authenticated:
                    user_id = current_user.id
            except:
                # Flask shell or no user context
                user_id = None
        
        # Create snapshot of current state
        metadata_snapshot = {
            'name': dataset.gpx_meta_data.name,
            'difficulty': dataset.gpx_meta_data.difficulty.value if dataset.gpx_meta_data.difficulty else None,
            'length_3d': dataset.gpx_meta_data.length_3d,
            'uphill': dataset.gpx_meta_data.uphill,
            'downhill': dataset.gpx_meta_data.downhill,
            'moving_time': dataset.gpx_meta_data.moving_time,
            'max_elevation': dataset.gpx_meta_data.max_elevation,
            'max_speed': dataset.gpx_meta_data.max_speed,
            'hikr_user': dataset.gpx_meta_data.hikr_user,
            'hikr_url': dataset.gpx_meta_data.hikr_url,
        }
        
        version = GPXVersion(
            dataset_id=dataset.id,
            version_number=version_number,
            changelog=changelog,
            created_by_id=user_id,  # ← Ahora puede ser None
            gpx_content=dataset.gpx_meta_data.gpx_content,
            metadata_snapshot=metadata_snapshot
        )
        
        db.session.add(version)
        db.session.commit()
        
        return version
    
    @staticmethod
    def _create_uvl_version(dataset, version_number, changelog, user_id=None):
        """Create version for UVL dataset"""
        # TODO: Implement UVL versioning
        pass
    
    @staticmethod
    def get_versions(dataset_id):
        """Get all versions of a dataset"""
        return DatasetVersion.query.filter_by(
            dataset_id=dataset_id
        ).order_by(DatasetVersion.version_number.desc()).all()
    
    @staticmethod
    def get_version(dataset_id, version_number):
        """Get specific version"""
        return DatasetVersion.query.filter_by(
            dataset_id=dataset_id,
            version_number=version_number
        ).first()
    
    @staticmethod
    def restore_version(dataset_id, version_number):
        """Restore dataset to a previous version"""
        version = VersionService.get_version(dataset_id, version_number)
        
        if not version:
            raise ValueError(f"Version {version_number} not found")
        
        dataset = BaseDataset.query.get(dataset_id)
        
        if dataset.dataset_type == 'gpx':
            return VersionService._restore_gpx_version(dataset, version)
        elif dataset.dataset_type == 'uvl':
            return VersionService._restore_uvl_version(dataset, version)
    
    @staticmethod
    def _restore_gpx_version(dataset, version):
        """Restore GPX dataset to previous version"""
        # Restore GPX content
        dataset.gpx_meta_data.gpx_content = version.gpx_content
        
        # Restore metadata
        metadata = version.metadata_snapshot
        dataset.gpx_meta_data.name = metadata.get('name')
        dataset.gpx_meta_data.length_3d = metadata.get('length_3d')
        dataset.gpx_meta_data.uphill = metadata.get('uphill')
        
        db.session.commit()
        
        # Create new version marking restoration
        return VersionService.create_version(
            dataset, 
            f"Restored to version {version.version_number}"
        )
    
    @staticmethod
    def _restore_uvl_version(dataset, version):
        """Restore UVL dataset to previous version"""
        # TODO: Implement UVL restoration
        pass
