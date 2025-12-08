import logging

from app import db
from app.modules.dataset.models import BaseDataset, GPXDataset, UVLDataset
from app.modules.versioning.models import DatasetVersion, GPXDatasetVersion, UVLDatasetVersion
from app.modules.versioning.repositories import VersioningRepository

logger = logging.getLogger(__name__)


class VersionService:
    """Servicio para gestionar versiones de datasets"""

    def __init__(self):
        self.repository = VersioningRepository()

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
