import hashlib
import logging
import os
import shutil
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

from flask import request
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app import db
from app.modules.auth.services import AuthenticationService
from app.modules.dataset.models import (
    BaseDataset,
    DatasetVersion,
    DSDownloadRecord,
    DSMetaData,
    DSViewRecord,
    GPXDataset,
    GPXDatasetVersion,
    UVLDataset,
    UVLDatasetVersion,
)
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
from core.services.BaseService import BaseService

logger = logging.getLogger(__name__)


def calculate_checksum_and_size(file_path):
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as file:
        content = file.read()
        hash_md5 = hashlib.md5(content).hexdigest()
        return hash_md5, file_size


# === Tipos de dataset (validación por extensión) ===
class DataTypeHandler:
    ext = None
    name = None

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


class VersionService:
    """Servicio para gestionar versiones de datasets"""

    @staticmethod
    def create_version(dataset: BaseDataset, changelog: str, user, bump_type: str = "patch") -> DatasetVersion:
        """
        Crear una nueva versión del dataset.
        Captura el estado actual y lo guarda como snapshot.

        Args:
            dataset: Dataset a versionar
            changelog: Descripción de cambios
            user: Usuario que crea la versión
            bump_type: Tipo de incremento ('major', 'minor', 'patch')
        """
        # Obtener la última versión para incrementar
        last_version = dataset.get_latest_version()

        new_version_number = VersionService._increment_version(
            last_version.version_number if last_version else "0.0.0", bump_type  # Pasar el tipo de incremento
        )

        # Crear snapshot de archivos actuales
        files_snapshot = VersionService._create_files_snapshot(dataset)

        # Determinar la clase de versión según tipo de dataset
        version_class = VersionService._get_version_class(dataset)

        # Crear la versión
        version = version_class(
            dataset_id=dataset.id,
            version_number=new_version_number,
            title=dataset.ds_meta_data.title,
            description=dataset.ds_meta_data.description,
            files_snapshot=files_snapshot,
            changelog=changelog,
            created_by_id=user.id,
        )

        # Calcular métricas específicas según tipo
        if isinstance(dataset, GPXDataset):
            version.total_distance = dataset.calculate_total_distance()
            version.total_elevation_gain = dataset.calculate_total_elevation_gain()
            version.total_elevation_loss = dataset.calculate_total_elevation_loss()
            version.total_points = dataset.count_total_points()
            version.track_count = dataset.count_tracks()

        elif isinstance(dataset, UVLDataset):
            try:
                version.total_features = dataset.calculate_total_features() or 0
                version.total_constraints = dataset.calculate_total_constraints() or 0

                if hasattr(dataset.feature_models, "count"):
                    # Es una query de SQLAlchemy
                    version.model_count = dataset.feature_models.count()
                else:
                    # Es una lista Python
                    version.model_count = len(dataset.feature_models) if dataset.feature_models else 0

            except Exception as e:
                logger.warning(f"Could not calculate UVL metrics for dataset {dataset.id}: {str(e)}")
                version.total_features = 0
                version.total_constraints = 0
                version.model_count = 0

        db.session.add(version)
        db.session.commit()

        return version

    @staticmethod
    def _get_version_class(dataset):
        """Retornar la clase de versión apropiada según tipo de dataset"""
        version_classes = {
            "gpx": GPXDatasetVersion,
            "uvl": UVLDatasetVersion,
        }
        return version_classes.get(dataset.dataset_kind, DatasetVersion)

    @staticmethod
    def _create_files_snapshot(dataset):
        """Crear un snapshot JSON de todos los archivos actuales"""
        snapshot = {}
        for fm in dataset.feature_models:
            if hasattr(fm, "files"):
                for file in fm.files:
                    snapshot[file.name] = {"id": file.id, "checksum": file.checksum, "size": file.size}
        return snapshot

    @staticmethod
    def _increment_version(version_str: str, bump_type: str = "patch") -> str:
        """
        Incrementar versión semántica.
        bump_type: 'major', 'minor', 'patch'
        """

        if version_str == "0.0.0":
            return "1.0.0"

        major, minor, patch = map(int, version_str.split("."))

        if bump_type == "major":
            return f"{major + 1}.0.0"
        elif bump_type == "minor":
            return f"{major}.{minor + 1}.0"
        else:  # patch
            return f"{major}.{minor}.{patch + 1}"

    @staticmethod
    def compare_versions(version1_id: int, version2_id: int):
        """Comparar dos versiones de un dataset"""
        version1 = DatasetVersion.query.get_or_404(version1_id)
        version2 = DatasetVersion.query.get_or_404(version2_id)

        if version1.dataset_id != version2.dataset_id:
            raise ValueError("Versions must belong to the same dataset")

        # La versión más reciente compara con la más antigua
        if version1.created_at > version2.created_at:
            return version1.compare_with(version2)
        else:
            return version2.compare_with(version1)


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

    def create_new_record(self, dataset: BaseDataset, user_cookie: str) -> DSViewRecord:
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


def trending(metric: str = "downloads", period: str = "week", limit: int = 10):
    """
    metric: 'downloads' | 'views' | 'score' | 'score_v2'
    period: 'day' | 'week' | 'month'
    returns: list[{"dataset": BaseDataset, "views": int, "downloads": int, ...}]
    """

    # ventana temporal
    period_days = {"day": 1, "week": 7, "month": 30}.get(period, 7)
    now = datetime.utcnow()
    since_period = now - timedelta(days=period_days)
    since_1d = now - timedelta(days=1)

    # helper de agregaciones
    def agg_subq(model, date_col, since, count_label):
        return (
            db.session.query(
                getattr(model, "dataset_id").label("dataset_id"),
                func.count(getattr(model, "id")).label(count_label),
            )
            .filter(getattr(model, date_col) >= since)
            .group_by(getattr(model, "dataset_id"))
            .subquery()
        )

    # agregados (ventana) y (últimas 24h)
    views_p = agg_subq(DSViewRecord, "view_date", since_period, "views_p")
    dls_p = agg_subq(DSDownloadRecord, "download_date", since_period, "downloads_p")
    views_1d = agg_subq(DSViewRecord, "view_date", since_1d, "views_1d")
    dls_1d = agg_subq(DSDownloadRecord, "download_date", since_1d, "downloads_1d")

    # columnas coalesce
    Vp = func.coalesce(views_p.c.views_p, 0)
    Dp = func.coalesce(dls_p.c.downloads_p, 0)
    Vd = func.coalesce(views_1d.c.views_1d, 0)
    Dd = func.coalesce(dls_1d.c.downloads_1d, 0)

    # Solo datasets sincronizados (con DOI)
    base = (
        db.session.query(
            BaseDataset.id.label("dataset_id"),
            Vp.label("views"),
            Dp.label("downloads"),
            Vd.label("views_1d"),
            Dd.label("downloads_1d"),
        )
        .join(DSMetaData, DSMetaData.id == BaseDataset.ds_meta_data_id)
        .filter(DSMetaData.dataset_doi.isnot(None))
        .outerjoin(views_p, views_p.c.dataset_id == BaseDataset.id)
        .outerjoin(dls_p, dls_p.c.dataset_id == BaseDataset.id)
        .outerjoin(views_1d, views_1d.c.dataset_id == BaseDataset.id)
        .outerjoin(dls_1d, dls_1d.c.dataset_id == BaseDataset.id)
    )

    # orden según métrica
    if metric == "views":
        base = base.filter(Vp > 0).order_by(Vp.desc(), BaseDataset.id.asc())
    elif metric == "downloads":
        base = base.filter(Dp > 0).order_by(Dp.desc(), BaseDataset.id.asc())
    elif metric == "score_v2":
        score_v2 = (Dd * 3.0) + (Dp * 2.0) + (Vd * 1.0) + (Vp * 0.5)
        base = base.filter((Vp + Dp + Vd + Dd) > 0).order_by(score_v2.desc(), BaseDataset.id.asc())
    else:  # 'score' simple
        score = (Dp * 2) + Vp
        base = base.filter((Vp + Dp) > 0).order_by(score.desc(), BaseDataset.id.asc())

    rows = base.limit(limit).all()
    if not rows:
        return []

    # precarga de metadata para títulos/autores en una sola query
    ids = [r.dataset_id for r in rows]
    datasets = BaseDataset.query.options(selectinload(BaseDataset.ds_meta_data)).filter(BaseDataset.id.in_(ids)).all()
    ds_map = {d.id: d for d in datasets}

    results = []
    for r in rows:
        ds = ds_map.get(r.dataset_id)
        if ds:
            results.append(
                {
                    "dataset": ds,
                    "views": int(r.views or 0),
                    "downloads": int(r.downloads or 0),
                    "views_1d": int(r.views_1d or 0),
                    "downloads_1d": int(r.downloads_1d or 0),
                }
            )
    return results
