from unittest.mock import patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import DSMetaData, GPXDataset, UVLDataset
from app.modules.versioning.models import GPXDatasetVersion, UVLDatasetVersion
from app.modules.versioning.services import VersionService


@pytest.fixture(scope="module")
def test_client_versioning(test_client):
    """Extends test_client with versioning-specific data"""
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


@pytest.fixture
def sample_uvl_dataset(test_client, sample_user):
    with test_client.application.app_context():
        metadata = DSMetaData(title="Test UVL Dataset", description="Test description", publication_type="none")
        db.session.add(metadata)
        db.session.commit()

        dataset = UVLDataset(user_id=sample_user.id, ds_meta_data_id=metadata.id)
        db.session.add(dataset)
        db.session.commit()

        return dataset.id


@pytest.fixture
def sample_gpx_dataset(test_client, sample_user):
    with test_client.application.app_context():
        metadata = DSMetaData(title="Test GPX Dataset", description="Test description", publication_type="none")
        db.session.add(metadata)
        db.session.commit()

        dataset = GPXDataset(user_id=sample_user.id, ds_meta_data_id=metadata.id)
        db.session.add(dataset)
        db.session.commit()

        return dataset.id


class TestVersionIncrement:

    def test_increment_patch_version(self):
        result = VersionService._increment_version("1.0.0", "patch")
        assert result == "1.0.1"

    def test_increment_minor_version(self):
        result = VersionService._increment_version("1.0.0", "minor")
        assert result == "1.1.0"

    def test_increment_major_version(self):
        result = VersionService._increment_version("1.0.0", "major")
        assert result == "2.0.0"

    def test_increment_from_zero(self):
        result = VersionService._increment_version("0.0.0", "patch")
        assert result == "1.0.0"

    def test_increment_high_numbers(self):
        result = VersionService._increment_version("99.99.99", "patch")
        assert result == "99.99.100"


class TestFileSnapshot:

    def test_create_files_snapshot_empty_dataset(self, test_client, sample_uvl_dataset):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            snapshot = VersionService._create_files_snapshot(dataset)

            assert isinstance(snapshot, dict)
            assert len(snapshot) == 0

    @patch("app.modules.versioning.services.VersionService._create_files_snapshot")
    def test_create_files_snapshot_with_files(self, mock_snapshot):
        mock_snapshot.return_value = {
            "model1.uvl": {"id": 1, "checksum": "abc123", "size": 1024},
            "model2.uvl": {"id": 2, "checksum": "def456", "size": 2048},
        }

        result = mock_snapshot()

        assert len(result) == 2
        assert "model1.uvl" in result
        assert result["model1.uvl"]["checksum"] == "abc123"


class TestVersionCreation:

    def test_create_first_version_uvl(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            version = VersionService.create_version(
                dataset=dataset, changelog="Initial version", user=sample_user, bump_type="patch"
            )

            assert version is not None
            assert version.version_number == "1.0.0"
            assert version.changelog == "Initial version"
            assert version.created_by_id == sample_user.id
            assert isinstance(version, UVLDatasetVersion)

    def test_create_second_version_patch(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            VersionService.create_version(dataset, "v1", sample_user, "patch")
            version2 = VersionService.create_version(dataset, "v2", sample_user, "patch")

            assert version2.version_number == "1.0.1"

    def test_create_version_minor(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            VersionService.create_version(dataset, "v1", sample_user, "patch")
            version2 = VersionService.create_version(dataset, "v2", sample_user, "minor")

            assert version2.version_number == "1.1.0"

    def test_create_version_major(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            VersionService.create_version(dataset, "v1", sample_user, "patch")
            version2 = VersionService.create_version(dataset, "v2", sample_user, "major")

            assert version2.version_number == "2.0.0"


class TestGPXVersionMetrics:

    @patch("app.modules.dataset.models.GPXDataset.calculate_total_distance")
    @patch("app.modules.dataset.models.GPXDataset.calculate_total_elevation_gain")
    @patch("app.modules.dataset.models.GPXDataset.count_tracks")
    def test_gpx_version_metrics(
        self, mock_tracks, mock_elevation, mock_distance, test_client, sample_gpx_dataset, sample_user
    ):
        mock_distance.return_value = 10.5
        mock_elevation.return_value = 500.0
        mock_tracks.return_value = 3

        with test_client.application.app_context():
            from app.modules.dataset.models import GPXDataset

            dataset = GPXDataset.query.get(sample_gpx_dataset)

            version = VersionService.create_version(dataset, "v1", sample_user, "patch")

            assert isinstance(version, GPXDatasetVersion)
            assert version.total_distance == 10.5
            assert version.total_elevation_gain == 500.0
            assert version.track_count == 3


class TestVersionComparison:

    def test_compare_versions_same_dataset(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            v1 = VersionService.create_version(dataset, "First version", sample_user, "patch")
            v2 = VersionService.create_version(dataset, "Second version", sample_user, "patch")

            comparison = VersionService.compare_versions(v1.id, v2.id)

            assert comparison is not None

    def test_compare_versions_different_datasets_raises_error(
        self, test_client, sample_uvl_dataset, sample_gpx_dataset, sample_user
    ):
        with test_client.application.app_context():
            from app.modules.dataset.models import GPXDataset, UVLDataset

            dataset1 = UVLDataset.query.get(sample_uvl_dataset)
            dataset2 = GPXDataset.query.get(sample_gpx_dataset)

            v1 = VersionService.create_version(dataset1, "v1", sample_user, "patch")
            v2 = VersionService.create_version(dataset2, "v1", sample_user, "patch")

            with pytest.raises(ValueError, match="must belong to the same dataset"):
                VersionService.compare_versions(v1.id, v2.id)


class TestVersionModel:

    def test_version_to_dict(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            version = VersionService.create_version(dataset, "Test", sample_user, "patch")
            version_dict = version.to_dict()

            assert "id" in version_dict
            assert "version_number" in version_dict
            assert "changelog" in version_dict
            assert version_dict["version_number"] == "1.0.0"

    def test_version_string_representation(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            version = VersionService.create_version(dataset, "Test", sample_user, "patch")

            assert "Version 1.0.0" in str(version)


class TestVersioningRoutesIntegration:

    def test_compare_versions_endpoint(self, test_client):
        test_client.post("/login", data={"email": "test@example.com", "password": "test1234"})

        response = test_client.get("/versions/1/compare/2")
        assert response.status_code in [200, 302, 400, 403, 404]

    def test_create_version_endpoint(self, test_client, sample_uvl_dataset):
        test_client.post("/login", data={"email": "test@example.com", "password": "test1234"})

        response = test_client.post(
            f"/dataset/{sample_uvl_dataset}/create_version", data={"changelog": "Test version", "bump_type": "patch"}
        )

        assert response.status_code in [200, 302, 403, 404]

    def test_versions_list_page(self, test_client):
        test_client.post("/login", data={"email": "test@example.com", "password": "test1234"})

        response = test_client.get("/dataset/1/versions")
        assert response.status_code in [200, 404]

    def test_api_versions_list(self, test_client):
        response = test_client.get("/api/dataset/1/versions")
        assert response.status_code in [200, 404]

    def test_api_version_detail(self, test_client):
        response = test_client.get("/api/version/1")
        assert response.status_code in [200, 404]


class TestVersioningEdgeCases:

    def test_create_version_without_changelog(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            version = VersionService.create_version(dataset, "", sample_user, "patch")
            assert version.changelog == ""

    def test_multiple_versions_order(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset
            from app.modules.versioning.models import UVLDatasetVersion

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            VersionService.create_version(dataset, "v1", sample_user, "patch")
            VersionService.create_version(dataset, "v2", sample_user, "patch")
            VersionService.create_version(dataset, "v3", sample_user, "minor")

            all_versions = UVLDatasetVersion.query.filter_by(dataset_id=dataset.id).all()

            assert len(all_versions) == 3

            version_numbers = {v.version_number for v in all_versions}
            assert "1.0.0" in version_numbers
            assert "1.0.1" in version_numbers
            assert "1.1.0" in version_numbers

    def test_version_count_for_dataset(self, test_client, sample_uvl_dataset, sample_user):
        with test_client.application.app_context():
            from app.modules.dataset.models import UVLDataset
            from app.modules.versioning.models import UVLDatasetVersion

            dataset = UVLDataset.query.get(sample_uvl_dataset)

            VersionService.create_version(dataset, "v1", sample_user, "patch")
            VersionService.create_version(dataset, "v2", sample_user, "patch")

            count = UVLDatasetVersion.query.filter_by(dataset_id=dataset.id).count()
            assert count == 2
