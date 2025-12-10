import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import BaseDataset, DSMetaData, PublicationType
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from app.modules.versioning.models import DatasetVersion
from app.modules.zenodo.services import ZenodoService


@pytest.fixture(scope="function")
def sample_user(test_client):
    """Fixture para obtener usuario de prueba"""
    with test_client.application.app_context():
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(email="test@example.com")
            user.set_password("test1234")
            db.session.add(user)
            db.session.commit()
        return user


@pytest.fixture(scope="function")
def sample_dataset_with_doi(test_client, sample_user):
    """Fixture para crear un dataset con DOI"""
    with test_client.application.app_context():
        metadata = DSMetaData(
            title="Versioned Dataset",
            description="Dataset with versioning",
            publication_type=PublicationType.NONE,
            dataset_doi="10.5281/zenodo.1234567",
        )
        db.session.add(metadata)
        db.session.commit()

        dataset = BaseDataset(user_id=sample_user.id, ds_meta_data_id=metadata.id)
        db.session.add(dataset)
        db.session.commit()

        yield dataset

        # Cleanup
        try:
            DatasetVersion.query.filter_by(dataset_id=dataset.id).delete()
            BaseDataset.query.filter_by(id=dataset.id).delete()
            DSMetaData.query.filter_by(id=metadata.id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture(scope="function")
def sample_version(test_client, sample_dataset_with_doi):
    """Fixture para crear una versión de dataset"""
    with test_client.application.app_context():
        version = DatasetVersion(
            dataset_id=sample_dataset_with_doi.id, version_number="1.0.0", description="Initial version"
        )
        db.session.add(version)
        db.session.commit()

        yield version

        # Cleanup
        try:
            DatasetVersion.query.filter_by(id=version.id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture(scope="function")
def sample_feature_model_versioned(test_client, sample_dataset_with_doi):
    """Fixture para crear un feature model para dataset versionado"""
    with test_client.application.app_context():
        fm_metadata = FMMetaData(
            filename="versioned_model.uvl",
            title="Versioned Feature Model",
            description="Feature model for versioning",
            publication_type=PublicationType.NONE,
            publication_doi="",
            tags="test, versioning",
            file_version="1.0",
        )
        db.session.add(fm_metadata)
        db.session.commit()

        feature_model = FeatureModel(data_set_id=sample_dataset_with_doi.id, fm_meta_data_id=fm_metadata.id)
        db.session.add(feature_model)
        db.session.commit()

        yield feature_model

        # Cleanup
        try:
            FeatureModel.query.filter_by(id=feature_model.id).delete()
            FMMetaData.query.filter_by(id=fm_metadata.id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()


class TestZenodoServiceVersioning:
    """Tests para versionado en Zenodo"""

    @patch("app.modules.zenodo.services.requests.put")
    @patch("app.modules.zenodo.services.requests.get")
    def test_create_new_version_success(
        self, mock_get, mock_put, test_client, sample_dataset_with_doi, sample_version, monkeypatch
    ):
        """Test: Crear nueva versión exitosamente"""
        # Mock metadata update
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put.return_value = mock_put_response

        # Mock get deposition
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "id": 1234567,
            "doi": "10.5281/zenodo.1234567.v1",
            "files": [],
        }
        mock_get.return_value = mock_get_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset_with_doi.id)
            version = DatasetVersion.query.get(sample_version.id)
            service = ZenodoService()

            result = service.create_new_version(1234567, dataset, version)
            assert result is not None
            assert "doi" in result

    @patch("app.modules.zenodo.services.requests.put")
    def test_create_new_version_deposition_not_found(
        self, mock_put, test_client, sample_dataset_with_doi, sample_version, monkeypatch
    ):
        """Test: Deposición no encontrada al crear versión"""
        mock_put_response = Mock()
        mock_put_response.status_code = 404
        mock_put.return_value = mock_put_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset_with_doi.id)
            version = DatasetVersion.query.get(sample_version.id)
            service = ZenodoService()

            result = service.create_new_version(999999, dataset, version)
            assert result["message"] == "Deposition not found, version created locally only"

    @patch("app.modules.zenodo.services.requests.put")
    def test_create_new_version_metadata_update_failure(
        self, mock_put, test_client, sample_dataset_with_doi, sample_version, monkeypatch
    ):
        """Test: Fallo al actualizar metadatos de versión"""
        mock_put_response = Mock()
        mock_put_response.status_code = 500
        mock_put_response.text = "Internal server error"
        mock_put.return_value = mock_put_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset_with_doi.id)
            version = DatasetVersion.query.get(sample_version.id)
            service = ZenodoService()

            with pytest.raises(Exception, match="Failed to update metadata"):
                service.create_new_version(1234567, dataset, version)

    @patch("app.modules.zenodo.services.requests.put")
    @patch("app.modules.zenodo.services.requests.get")
    @patch("app.modules.zenodo.services.requests.post")
    def test_create_new_version_with_new_files(
        self,
        mock_post,
        mock_get,
        mock_put,
        test_client,
        sample_dataset_with_doi,
        sample_version,
        sample_feature_model_versioned,
        monkeypatch,
    ):
        """Test: Crear nueva versión con archivos nuevos"""
        # Mock metadata update
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put.return_value = mock_put_response

        # Mock get deposition - no files initially
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "id": 1234567,
            "doi": "10.5281/zenodo.1234567.v2",
            "files": [],
        }
        mock_get.return_value = mock_get_response

        # Mock file upload
        mock_post_response = Mock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"id": "file-123", "filename": "versioned_model.uvl"}
        mock_post.return_value = mock_post_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("WORKING_DIR", tempfile.gettempdir())

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset_with_doi.id)
            version = DatasetVersion.query.get(sample_version.id)
            version.version_number = "2.0.0"

            # Create dummy file
            user_id = dataset.user_id
            file_dir = os.path.join(tempfile.gettempdir(), f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(file_dir, exist_ok=True)
            file_path = os.path.join(file_dir, "versioned_model.uvl")
            with open(file_path, "w") as f:
                f.write("test content")

            service = ZenodoService()

            try:
                result = service.create_new_version(1234567, dataset, version)
                assert result is not None
            finally:
                # Cleanup
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(file_dir):
                    os.rmdir(file_dir)

    @patch("app.modules.zenodo.services.requests.put")
    @patch("app.modules.zenodo.services.requests.get")
    def test_create_new_version_with_publication_type(
        self, mock_get, mock_put, test_client, sample_dataset_with_doi, sample_version, monkeypatch
    ):
        """Test: Crear versión con tipo de publicación"""
        # Mock metadata update
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put.return_value = mock_put_response

        # Mock get deposition
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {
            "id": 1234567,
            "doi": "10.5281/zenodo.1234567.v1",
            "files": [],
        }
        mock_get.return_value = mock_get_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset_with_doi.id)
            dataset.ds_meta_data.publication_type = PublicationType.CONFERENCE_PAPER
            dataset.ds_meta_data.publication_doi = "10.1234/conference"
            db.session.commit()

            version = DatasetVersion.query.get(sample_version.id)
            service = ZenodoService()

            result = service.create_new_version(1234567, dataset, version)
            assert result is not None

            # Verify metadata was sent with publication type
            call_args = mock_put.call_args
            json_data = call_args[1]["json"]
            assert json_data["metadata"]["upload_type"] == "publication"
            assert json_data["metadata"]["publication_type"] == "conferencepaper"

    @patch("app.modules.zenodo.services.requests.put")
    @patch("app.modules.zenodo.services.requests.get")
    def test_create_new_version_without_doi(
        self, mock_get, mock_put, test_client, sample_dataset_with_doi, sample_version, monkeypatch
    ):
        """Test: Crear versión cuando la deposición no tiene DOI"""
        # Mock metadata update
        mock_put_response = Mock()
        mock_put_response.status_code = 200
        mock_put.return_value = mock_put_response

        # Mock get deposition without DOI
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"id": 1234567, "files": []}
        mock_get.return_value = mock_get_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset_with_doi.id)
            version = DatasetVersion.query.get(sample_version.id)
            service = ZenodoService()

            result = service.create_new_version(1234567, dataset, version)
            assert result is not None
            # Should return deposition data even without DOI
            assert result["id"] == 1234567


class TestZenodoServiceFullConnection:
    """Tests para test_full_connection"""

    @patch("app.modules.zenodo.services.requests.delete")
    @patch("app.modules.zenodo.services.requests.post")
    @patch("builtins.open", create=True)
    def test_full_connection_complete_flow(self, mock_open, mock_post, mock_delete, test_client, monkeypatch):
        """Test: Flujo completo de test_full_connection"""
        from unittest.mock import MagicMock

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock create deposition
        mock_create_response = Mock()
        mock_create_response.status_code = 201
        mock_create_response.json.return_value = {"id": 123}

        # Mock upload file
        mock_upload_response = Mock()
        mock_upload_response.status_code = 201
        mock_upload_response.json.return_value = {"filename": "test_file.txt"}

        # Mock delete
        mock_delete_response = Mock()
        mock_delete_response.status_code = 204

        mock_post.side_effect = [mock_create_response, mock_upload_response]
        mock_delete.return_value = mock_delete_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("WORKING_DIR", tempfile.gettempdir())

        with test_client.application.app_context():
            service = ZenodoService()
            response = service.test_full_connection()
            data = response.get_json()

            assert data["success"] is True
            assert isinstance(data["messages"], list)

    @patch("app.modules.zenodo.services.requests.post")
    def test_full_connection_create_deposition_fails(self, mock_post, test_client, monkeypatch):
        """Test: Fallo al crear deposición en test_full_connection"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("WORKING_DIR", tempfile.gettempdir())

        with test_client.application.app_context():
            service = ZenodoService()
            response = service.test_full_connection()
            data = response.get_json()

            assert data["success"] is False
            assert "Failed to create test deposition" in data["messages"]

    @patch("app.modules.zenodo.services.requests.post")
    def test_full_connection_network_error_on_create(self, mock_post, test_client, monkeypatch):
        """Test: Error de red al crear deposición"""
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("Network error")

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("WORKING_DIR", tempfile.gettempdir())

        with test_client.application.app_context():
            service = ZenodoService()
            response = service.test_full_connection()
            data = response.get_json()

            assert data["success"] is False
            assert any("network error" in msg.lower() for msg in data["messages"])

    @patch("app.modules.zenodo.services.requests.delete")
    @patch("app.modules.zenodo.services.requests.post")
    @patch("builtins.open", create=True)
    def test_full_connection_upload_fails(self, mock_open, mock_post, mock_delete, test_client, monkeypatch):
        """Test: Fallo al subir archivo en test_full_connection"""
        from unittest.mock import MagicMock

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock create deposition (success)
        mock_create_response = Mock()
        mock_create_response.status_code = 201
        mock_create_response.json.return_value = {"id": 123}

        # Mock upload file (failure)
        mock_upload_response = Mock()
        mock_upload_response.status_code = 400
        mock_upload_response.content = b"Upload failed"

        # Mock delete
        mock_delete_response = Mock()
        mock_delete_response.status_code = 204

        mock_post.side_effect = [mock_create_response, mock_upload_response]
        mock_delete.return_value = mock_delete_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("WORKING_DIR", tempfile.gettempdir())

        with test_client.application.app_context():
            service = ZenodoService()
            response = service.test_full_connection()
            data = response.get_json()

            assert data["success"] is False
            assert any("Failed to upload test file" in msg for msg in data["messages"])

    @patch("app.modules.zenodo.services.requests.delete")
    @patch("app.modules.zenodo.services.requests.post")
    @patch("builtins.open", create=True)
    def test_full_connection_delete_fails(self, mock_open, mock_post, mock_delete, test_client, monkeypatch):
        """Test: Fallo al eliminar deposición en test_full_connection"""
        from unittest.mock import MagicMock

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock create deposition
        mock_create_response = Mock()
        mock_create_response.status_code = 201
        mock_create_response.json.return_value = {"id": 123}

        # Mock upload file
        mock_upload_response = Mock()
        mock_upload_response.status_code = 201
        mock_upload_response.json.return_value = {"filename": "test_file.txt"}

        # Mock delete (failure)
        import requests

        mock_delete.side_effect = requests.exceptions.Timeout("Delete timeout")

        mock_post.side_effect = [mock_create_response, mock_upload_response]

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("WORKING_DIR", tempfile.gettempdir())

        with test_client.application.app_context():
            service = ZenodoService()
            response = service.test_full_connection()
            data = response.get_json()

            assert data["success"] is False
            assert any("Failed to delete test deposition" in msg for msg in data["messages"])
