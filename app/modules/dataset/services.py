from __future__ import annotations

import hashlib
import logging
import os
import shutil
import uuid
import xml.etree.ElementTree as ET
from typing import Optional

from flask import request

from app.modules.auth.services import AuthenticationService
from app.modules.dataset.models import BaseDataset, DSMetaData
from app.modules.dataset.registry import get_descriptor, infer_kind_from_filename
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
)
from app.modules.versioning.services import VersionService
from core.services.BaseService import BaseService

# NOTE: func/selectinload were removed from this file because trending logic
# was moved to app.modules.trending.services. Keep imports minimal to satisfy linters.


logger = logging.getLogger(__name__)


def calculate_checksum_and_size(file_path):
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as file:
        content = file.read()
        hash_md5 = hashlib.md5(content).hexdigest()
        return hash_md5, file_size


# === Tipos de dataset (validación por extensión) ===
class DataTypeHandler:
    ext: Optional[str] = None
    name: Optional[str] = None

    def validate(self, filepath: str):
        return True


class UVLHandler(DataTypeHandler):
    ext = ".uvl"
    name = "uvl"


class GPXHandler(DataTypeHandler):
    ext = ".gpx"
    name = "gpx"

    def validate(self, filepath: str):
        # Validación mínima: XML válido y raíz <gpx>
        with open(filepath, "rb") as f:
            tree = ET.parse(f)
        root = tree.getroot()
        if not root.tag.lower().endswith("gpx"):
            raise ValueError("Invalid GPX file: missing <gpx> root")
        return True


DATA_TYPE_REGISTRY = {
    ".uvl": UVLHandler(),
    ".gpx": GPXHandler(),
}


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

    def move_feature_models(self, dataset: BaseDataset):
        """Mueve los archivos de feature models desde la carpeta temporal a la definitiva."""
        current_user = AuthenticationService().get_authenticated_user()
        source_dir = current_user.temp_folder()

        working_dir = os.getenv("WORKING_DIR", "")
        dest_dir = os.path.join(working_dir, "uploads", f"user_{current_user.id}", f"dataset_{dataset.id}")
        os.makedirs(dest_dir, exist_ok=True)

        for feature_model in dataset.feature_models:
            filename = feature_model.fm_meta_data.filename
            source_path = os.path.join(source_dir, filename)

            if os.path.exists(source_path):
                shutil.move(source_path, dest_dir)
            else:
                logger.warning(f"File not found: {source_path}")

    def get_synchronized(self, current_user_id: int) -> BaseDataset:
        return self.repository.get_synchronized(current_user_id)

    def get_unsynchronized(self, current_user_id: int) -> BaseDataset:
        return self.repository.get_unsynchronized(current_user_id)

    def get_unsynchronized_dataset(self, current_user_id: int, dataset_id: int) -> BaseDataset:
        return self.repository.get_unsynchronized_dataset(current_user_id, dataset_id)

    def latest_synchronized(self):
        return self.repository.latest_synchronized()

    def count_synchronized_datasets(self):
        return self.repository.count_synchronized_datasets()

    # (si no existe en tu código base, puedes eliminar este método)
    def count_feature_models(self):
        # Evita referenciar un servicio no definido; usa el repo directamente si lo necesitas
        return self.feature_model_repository.count()

    def count_authors(self) -> int:
        return self.author_repository.count()

    def count_dsmetadata(self) -> int:
        return self.dsmetadata_repository.count()

    def total_dataset_downloads(self) -> int:
        return self.dsdownloadrecord_repository.total_dataset_downloads()

    def total_dataset_views(self) -> int:
        return self.dsviewrecord_repostory.total_dataset_views()

    def _infer_dataset_kind_from_form(self, form) -> str:
        # 1) si el usuario indicó el tipo, úsalo
        if getattr(form, "dataset_type", None) and form.dataset_type.data:
            return (form.dataset_type.data or "").strip().lower() or "base"

        # 2) si no, infiere por extensión del PRIMER archivo
        if form.feature_models and len(form.feature_models) > 0:
            first = form.feature_models[0]
            filename = (first.uvl_filename.data or "").strip()
            _, ext = os.path.splitext(filename.lower())
            handler = DATA_TYPE_REGISTRY.get(ext)
            if handler:
                return handler.name

        # 3) fallback
        return "base"

    def create_from_form(self, form, current_user) -> BaseDataset:
        """Crea un dataset desde el formulario."""
        logger.info("Creating dataset from form...")

        if not form.feature_models or len(form.feature_models) == 0:
            raise ValueError("At least one file is required to create a dataset")

        # 1. Crear DSMetaData
        dsmetadata_dict = form.get_dsmetadata()
        dsmetadata = self.dsmetadata_repository.create(**dsmetadata_dict)

        # 2. Inferir tipo de dataset según archivos subidos
        dataset_kind = "base"
        if form.feature_models:
            first_file = form.feature_models[0].filename.data
            dataset_kind = infer_kind_from_filename(first_file)

        # 3. Obtener descriptor y crear instancia del tipo correcto
        descriptor = get_descriptor(dataset_kind)

        try:
            dataset = descriptor.model_class(
                user_id=current_user.id, ds_meta_data_id=dsmetadata.id, dataset_kind=dataset_kind
            )

            # Añadir a la sesión y hacer flush para obtener el ID
            self.repository.session.add(dataset)
            self.repository.session.flush()

        except Exception as exc:
            logger.error(f"Error creating dataset: {exc}")
            self.dsmetadata_repository.session.rollback()
            raise exc

        # 4. Crear autores
        for author_data in form.get_authors():
            author = self.author_repository.create(commit=False, ds_meta_data_id=dsmetadata.id, **author_data)
            dsmetadata.authors.append(author)

        # 5. Procesar feature models (archivos)
        for feature_model_form in form.feature_models:
            filename = feature_model_form.filename.data

            # ✅ Validar que el filename no esté vacío
            if not filename:
                logger.warning("Skipping feature model with empty filename")
                continue

            # Crear FM metadata
            fmmetadata_dict = feature_model_form.get_fmmetadata()
            fmmetadata = self.fmmetadata_repository.create(commit=False, **fmmetadata_dict)

            # Crear feature model
            fm = self.feature_model_repository.create(
                commit=False, data_set_id=dataset.id, fm_meta_data_id=fmmetadata.id
            )

            # Crear autores del feature model
            for author_data in feature_model_form.get_authors():
                author = self.author_repository.create(commit=False, fm_meta_data_id=fmmetadata.id, **author_data)
                fmmetadata.authors.append(author)

            # Validar archivo según su tipo
            file_path = os.path.join(current_user.temp_folder(), filename)
            descriptor_for_file = get_descriptor(infer_kind_from_filename(filename))

            try:
                descriptor_for_file.handler.validate(file_path)
            except Exception as e:
                logger.error(f"Validation failed for {filename}: {e}")
                self.repository.session.rollback()
                raise ValueError(f"File validation failed: {str(e)}")

            # Calcular checksum y tamaño
            checksum, size = calculate_checksum_and_size(file_path)

            # Crear registro de archivo
            file = self.hubfilerepository.create(
                commit=False, name=filename, checksum=checksum, size=size, feature_model_id=fm.id
            )
            fm.files.append(file)

        # Commit final
        self.repository.session.commit()

        try:
            version = VersionService.create_version(
                dataset=dataset,
                changelog="Initial version (automatically generated)",
                user=current_user,
                bump_type="patch",
            )
            logger.info(f"Created initial version {version.version_number} for dataset {dataset.id}")
        except Exception as e:
            logger.error(f"Could not create initial version for dataset {dataset.id}: {str(e)}")
            # No hacer rollback, el dataset ya está creado

        return dataset

    def update_dsmetadata(self, id, **kwargs):
        return self.dsmetadata_repository.update(id, **kwargs)

    def get_uvlhub_doi(self, dataset: BaseDataset) -> str:
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

    def the_record_exists(self, dataset: BaseDataset, user_cookie: str):
        return self.repository.the_record_exists(dataset, user_cookie)

    def create_new_record(self, dataset: BaseDataset, user_cookie: str):
        return self.repository.create_new_record(dataset, user_cookie)

    def create_cookie(self, dataset: BaseDataset) -> str:
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
