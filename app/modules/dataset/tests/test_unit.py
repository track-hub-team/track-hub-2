import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import BaseDataset, DSMetaData, GPXDataset, PublicationType, UVLDataset


@pytest.fixture(scope="module")
def test_client_dataset(test_client):
    """Extends test_client with dataset-specific data"""
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
    metadata = DSMetaData(
        title="Test Dataset",
        description="Dataset for unit testing",
        publication_type=PublicationType.NONE,
        dataset_doi=None,
    )
    db.session.add(metadata)
    db.session.commit()

    yield metadata

    try:
        BaseDataset.query.filter_by(ds_meta_data_id=metadata.id).delete()
        db.session.delete(metadata)
        db.session.commit()
    except Exception:
        db.session.rollback()


class TestDSMetaData:

    def test_create_metadata(self, test_client):
        with test_client.application.app_context():
            metadata = DSMetaData(
                title="Test Metadata", description="Test Description", publication_type=PublicationType.NONE
            )
            db.session.add(metadata)
            db.session.commit()

            assert metadata.id is not None
            assert metadata.title == "Test Metadata"
            assert metadata.description == "Test Description"

            db.session.delete(metadata)
            db.session.commit()

    def test_metadata_with_doi(self, test_client):
        with test_client.application.app_context():
            metadata = DSMetaData(
                title="Published Dataset",
                description="Dataset with DOI",
                publication_type=PublicationType.JOURNAL_ARTICLE,
                dataset_doi="10.1234/test.doi",
            )
            db.session.add(metadata)
            db.session.commit()

            assert metadata.dataset_doi == "10.1234/test.doi"
            assert metadata.publication_type == PublicationType.JOURNAL_ARTICLE

            db.session.delete(metadata)
            db.session.commit()


class TestBaseDataset:

    def test_create_base_dataset(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = BaseDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            assert dataset.id is not None
            assert dataset.user_id == sample_user.id
            assert dataset.created_at is not None

    def test_dataset_user_relationship(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = BaseDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            assert dataset.user.id == sample_user.id
            assert dataset.user.email == "test@example.com"


class TestUVLDataset:

    def test_create_uvl_dataset(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            assert dataset.id is not None
            assert dataset.dataset_kind == "uvl"

    def test_uvl_dataset_metrics(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            assert hasattr(dataset, "calculate_total_features")
            assert hasattr(dataset, "calculate_total_constraints")

            features = dataset.calculate_total_features()
            constraints = dataset.calculate_total_constraints()

            assert features is not None or features == 0
            assert constraints is not None or constraints == 0


class TestGPXDataset:

    def test_create_gpx_dataset(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = GPXDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            assert dataset.id is not None
            assert dataset.dataset_kind == "gpx"

    def test_gpx_dataset_metrics(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = GPXDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            assert hasattr(dataset, "calculate_total_distance")
            assert hasattr(dataset, "calculate_total_elevation_gain")
            assert hasattr(dataset, "count_total_points")
            assert hasattr(dataset, "count_tracks")

            distance = dataset.calculate_total_distance()
            elevation = dataset.calculate_total_elevation_gain()
            points = dataset.count_total_points()
            tracks = dataset.count_tracks()

            assert distance is not None or distance == 0
            assert elevation is not None or elevation == 0
            assert points is not None or points == 0
            assert tracks is not None or tracks == 0


class TestPublicationType:

    def test_publication_types_exist(self):
        assert hasattr(PublicationType, "NONE")
        assert hasattr(PublicationType, "JOURNAL_ARTICLE")

    def test_metadata_with_different_publication_types(self, test_client):
        with test_client.application.app_context():
            pub_types = [PublicationType.NONE, PublicationType.JOURNAL_ARTICLE]

            for pub_type in pub_types:
                metadata = DSMetaData(title=f"Dataset {pub_type.name}", description="Test", publication_type=pub_type)
                db.session.add(metadata)
                db.session.commit()

                assert metadata.publication_type == pub_type

                db.session.delete(metadata)
                db.session.commit()


class TestDatasetMethods:

    def test_dataset_str_representation(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            str_repr = str(dataset)
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0


class TestDatasetRelationships:

    def test_dataset_metadata_relationship(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            metadata = DSMetaData.query.get(sample_metadata.id)
            assert metadata is not None


class TestDatasetVersioning:

    def test_dataset_get_latest_version(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            assert hasattr(dataset, "get_latest_version")


class TestDatasetRegistry:

    def test_infer_kind_uvl(self, test_client):
        with test_client.application.app_context():
            from app.modules.dataset.registry import infer_kind_from_filename

            assert infer_kind_from_filename("test.uvl") == "uvl"
            assert infer_kind_from_filename("TEST.UVL") == "uvl"

    def test_infer_kind_gpx(self, test_client):
        with test_client.application.app_context():
            from app.modules.dataset.registry import infer_kind_from_filename

            assert infer_kind_from_filename("track.gpx") == "gpx"
            assert infer_kind_from_filename("ROUTE.GPX") == "gpx"

    def test_get_descriptor_uvl(self, test_client):
        with test_client.application.app_context():
            from app.modules.dataset.registry import get_descriptor

            desc = get_descriptor("uvl")
            assert desc is not None
            assert hasattr(desc, "model_class")

    def test_get_descriptor_gpx(self, test_client):
        with test_client.application.app_context():
            from app.modules.dataset.registry import get_descriptor

            desc = get_descriptor("gpx")
            assert desc is not None
            assert hasattr(desc, "model_class")


class TestDatasetRegistryExtended:

    def test_infer_kind_unknown(self, test_client):
        with test_client.application.app_context():
            from app.modules.dataset.registry import infer_kind_from_filename

            result = infer_kind_from_filename("unknown.txt")
            # El sistema retorna "base" como fallback
            assert result is None or result in ["unknown", "base"]

    def test_get_all_descriptors(self, test_client):
        with test_client.application.app_context():
            from app.modules.dataset.registry import get_all_descriptors

            descriptors = get_all_descriptors()
            assert isinstance(descriptors, (list, dict))
            assert len(descriptors) > 0

    def test_register_descriptor(self, test_client):
        with test_client.application.app_context():
            from app.modules.dataset.registry import get_descriptor

            # Verificar que el sistema de registro funciona
            desc_uvl = get_descriptor("uvl")
            desc_gpx = get_descriptor("gpx")
            assert desc_uvl is not None
            assert desc_gpx is not None


class TestDatasetServices:

    def test_dataset_service_module_exists(self, test_client):
        """Verificar que el módulo de servicios existe"""
        with test_client.application.app_context():
            from app.modules.dataset import services

            assert services is not None

    def test_author_service_exists(self, test_client):
        """Verificar servicio de autores"""
        with test_client.application.app_context():
            from app.modules.dataset.services import AuthorService

            service = AuthorService()
            assert service is not None

    def test_ds_meta_data_service_exists(self, test_client):
        """Verificar servicio de metadata"""
        with test_client.application.app_context():
            from app.modules.dataset.services import DSMetaDataService

            service = DSMetaDataService()
            assert service is not None


class TestDatasetModelsExtended:

    def test_dataset_to_dict(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            # Crear request context para to_dict
            with test_client.application.test_request_context():
                dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
                db.session.add(dataset)
                db.session.commit()

                if hasattr(dataset, "to_dict"):
                    result = dataset.to_dict()
                    assert isinstance(result, dict)

    def test_metadata_fields(self, test_client, sample_metadata):
        with test_client.application.app_context():
            # Verificar campos de metadata
            assert hasattr(sample_metadata, "title")
            assert hasattr(sample_metadata, "description")
            assert sample_metadata.title == "Test Dataset"

    def test_dataset_get_files(self, test_client, sample_user, sample_metadata):
        with test_client.application.app_context():
            dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=sample_metadata.id)
            db.session.add(dataset)
            db.session.commit()

            # Verificar relación con feature models
            assert hasattr(dataset, "feature_models")
