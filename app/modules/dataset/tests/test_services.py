import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import DSMetaData, PublicationType, UVLDataset
from app.modules.dataset.services import DataSetService, DOIMappingService, DSViewRecordService  # ← Cambio aquí


@pytest.fixture(scope="module")
def test_client(test_client):
    with test_client.application.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(email="test@example.com")
            user.set_password("test1234")
            db.session.add(user)
            db.session.commit()
    yield test_client


@pytest.fixture(scope="function")
def sample_user():
    return User.query.filter_by(email="test@example.com").first()


@pytest.fixture(scope="function")
def sample_metadata(sample_user):
    """Fixture para crear metadata de dataset"""
    metadata = DSMetaData(
        title="Test Dataset",
        description="Dataset for unit testing",
        publication_type=PublicationType.NONE,
        dataset_doi=None,
    )
    db.session.add(metadata)
    db.session.commit()

    yield metadata

    # Cleanup
    try:
        UVLDataset.query.filter_by(ds_meta_data_id=metadata.id).delete()
        db.session.delete(metadata)
        db.session.commit()
    except Exception:
        db.session.rollback()


class TestDataSetService:
    """Tests para DataSetService"""

    def test_service_initialization(self, test_client):
        """Test: Inicializar el servicio correctamente"""
        with test_client.application.app_context():
            service = DataSetService()
            assert service is not None
            assert hasattr(service, "repository")

    def test_count_synchronized_datasets(self, test_client):
        """Test: Contar datasets sincronizados"""
        with test_client.application.app_context():
            service = DataSetService()
            count = service.count_synchronized_datasets()
            assert isinstance(count, int)
            assert count >= 0

    def test_count_authors(self, test_client):
        """Test: Contar autores en el sistema"""
        with test_client.application.app_context():
            service = DataSetService()
            count = service.count_authors()
            assert isinstance(count, int)
            assert count >= 0

    def test_count_dsmetadata(self, test_client):
        """Test: Contar metadata de datasets"""
        with test_client.application.app_context():
            service = DataSetService()
            count = service.count_dsmetadata()
            assert isinstance(count, int)
            assert count >= 0

    def test_total_dataset_downloads(self, test_client):
        """Test: Total de descargas de datasets"""
        with test_client.application.app_context():
            service = DataSetService()
            total = service.total_dataset_downloads()
            assert isinstance(total, int)
            assert total >= 0

    def test_total_dataset_views(self, test_client):
        """Test: Total de vistas de datasets"""
        with test_client.application.app_context():
            service = DataSetService()
            total = service.total_dataset_views()
            assert isinstance(total, int)
            assert total >= 0

    def test_get_synchronized(self, test_client, sample_user):
        """Test: Obtener datasets sincronizados de un usuario"""
        with test_client.application.app_context():
            service = DataSetService()
            datasets = service.get_synchronized(sample_user.id)
            assert datasets is not None

    def test_get_unsynchronized(self, test_client, sample_user):
        """Test: Obtener datasets no sincronizados de un usuario"""
        with test_client.application.app_context():
            service = DataSetService()
            datasets = service.get_unsynchronized(sample_user.id)
            assert datasets is not None

    def test_latest_synchronized(self, test_client):
        """Test: Obtener los últimos datasets sincronizados"""
        with test_client.application.app_context():
            service = DataSetService()
            datasets = service.latest_synchronized()
            assert datasets is not None


class TestAuthorService:
    """Tests para AuthorService"""

    def test_author_service_initialization(self, test_client):
        """Test: Inicializar AuthorService"""
        with test_client.application.app_context():
            from app.modules.dataset.services import AuthorService

            service = AuthorService()
            assert service is not None


class TestDSMetaDataService:
    """Tests para DSMetaDataService"""

    def test_dsmetadata_service_initialization(self, test_client):
        """Test: Inicializar DSMetaDataService"""
        with test_client.application.app_context():
            from app.modules.dataset.services import DSMetaDataService

            service = DSMetaDataService()
            assert service is not None

    def test_filter_by_doi(self, test_client):
        """Test: Buscar metadata por DOI"""
        with test_client.application.app_context():
            from app.modules.dataset.services import DSMetaDataService

            # Crear metadata con DOI
            metadata = DSMetaData(
                title="Test DOI",
                description="Test",
                publication_type=PublicationType.NONE,
                dataset_doi="10.1234/test.filter",
            )
            db.session.add(metadata)
            db.session.commit()

            service = DSMetaDataService()
            result = service.filter_by_doi("10.1234/test.filter")

            assert result is not None
            assert result.dataset_doi == "10.1234/test.filter"

            # Cleanup
            db.session.delete(metadata)
            db.session.commit()


class TestSizeService:
    """Tests para SizeService"""

    def test_size_service_human_readable_bytes(self, test_client):
        """Test: Convertir bytes a formato legible"""
        with test_client.application.app_context():
            from app.modules.dataset.services import SizeService

            service = SizeService()

            assert "bytes" in service.get_human_readable_size(500)

    def test_size_service_human_readable_kb(self, test_client):
        """Test: Convertir KB a formato legible"""
        with test_client.application.app_context():
            from app.modules.dataset.services import SizeService

            service = SizeService()

            assert "KB" in service.get_human_readable_size(2048)

    def test_size_service_human_readable_mb(self, test_client):
        """Test: Convertir MB a formato legible"""
        with test_client.application.app_context():
            from app.modules.dataset.services import SizeService

            service = SizeService()

            assert "MB" in service.get_human_readable_size(2 * 1024 * 1024)

    def test_size_service_human_readable_gb(self, test_client):
        """Test: Convertir GB a formato legible"""
        with test_client.application.app_context():
            from app.modules.dataset.services import SizeService

            service = SizeService()

            assert "GB" in service.get_human_readable_size(2 * 1024 * 1024 * 1024)


# ============================================
# Tests adicionales de Services
# ============================================


class TestDataSetServiceMethods:
    """Tests para métodos sin cubrir"""

    def test_count_feature_models(self, test_client):
        """Cubre método count_feature_models()"""
        with test_client.application.app_context():
            service = DataSetService()
            count = service.count_feature_models()
            assert isinstance(count, int)
            assert count >= 0

    def test_move_feature_models_no_files(self, test_client, sample_user):
        """Cubre move_feature_models() sin archivos"""
        with test_client.application.app_context():
            from app.modules.dataset.models import DSMetaData, PublicationType, UVLDataset

            metadata = DSMetaData(title="Test Move", description="Test", publication_type=PublicationType.NONE)
            db.session.add(metadata)
            db.session.commit()

            dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=metadata.id)
            db.session.add(dataset)
            db.session.commit()

            service = DataSetService()

            # No debe fallar aunque no haya archivos
            try:
                service.move_feature_models(dataset)
                assert True
            except Exception as e:
                # Es OK si falla por archivos no encontrados
                assert "not found" in str(e).lower() or len(dataset.feature_models) == 0


class TestDOIMappingServiceMethods:
    """Tests para DOIMappingService"""

    def test_get_new_doi_nonexistent(self, test_client):
        """Cubre get_new_doi() con DOI inexistente"""
        with test_client.application.app_context():
            service = DOIMappingService()
            result = service.get_new_doi("10.9999/old.fake.doi")
            assert result is None


class TestDSViewRecordServiceMethods:
    """Tests para DSViewRecordService"""

    def test_create_cookie_generates_uuid(self, test_client, sample_user, sample_metadata):
        """Cubre create_cookie()"""
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            service = DSViewRecordService()

            # Debe generar un UUID válido
            with test_client.application.test_request_context():
                cookie = service.create_cookie(dataset)

                assert cookie is not None
                assert isinstance(cookie, str)
                assert len(cookie) > 0
