import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import BaseDataset, DSMetaData, PublicationType
from app.modules.featuremodel.models import FeatureModel, FMMetaData
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
def sample_dataset(test_client, sample_user):
    """Fixture para crear un dataset de prueba"""
    with test_client.application.app_context():
        metadata = DSMetaData(
            title="Test Dataset",
            description="Dataset for unit testing",
            publication_type=PublicationType.NONE,
            dataset_doi=None,
        )
        db.session.add(metadata)
        db.session.commit()

        dataset = BaseDataset(user_id=sample_user.id, ds_meta_data_id=metadata.id)
        db.session.add(dataset)
        db.session.commit()

        yield dataset

        # Cleanup
        try:
            BaseDataset.query.filter_by(id=dataset.id).delete()
            DSMetaData.query.filter_by(id=metadata.id).delete()
            db.session.commit()
        except Exception:
            db.session.rollback()


@pytest.fixture(scope="function")
def sample_feature_model(test_client, sample_dataset):
    """Fixture para crear un feature model de prueba"""
    with test_client.application.app_context():
        fm_metadata = FMMetaData(
            filename="test_model.uvl",
            title="Test Feature Model",
            description="Feature model for testing",
            publication_type=PublicationType.NONE,
            publication_doi="",
            tags="test, uvl",
            file_version="1.0",
        )
        db.session.add(fm_metadata)
        db.session.commit()

        feature_model = FeatureModel(data_set_id=sample_dataset.id, fm_meta_data_id=fm_metadata.id)
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


class TestZenodoServiceConfiguration:
    """Tests para configuración de ZenodoService"""

    def test_service_initialization(self, test_client):
        """Test: Inicializar el servicio correctamente"""
        with test_client.application.app_context():
            service = ZenodoService()
            assert service is not None
            assert hasattr(service, "ZENODO_ACCESS_TOKEN")
            assert hasattr(service, "ZENODO_API_URL")
            assert hasattr(service, "headers")

    def test_get_zenodo_url_with_fakenodo(self, test_client, monkeypatch):
        """Test: Obtener URL de Fakenodo cuando está configurado"""
        monkeypatch.setenv("FAKENODO_URL", "http://localhost:5001/api/deposit/depositions")
        with test_client.application.app_context():
            service = ZenodoService()
            assert service.ZENODO_API_URL == "http://localhost:5001/api/deposit/depositions"

    def test_get_zenodo_url_sandbox_dev(self, test_client, monkeypatch):
        """Test: Obtener URL de sandbox en desarrollo"""
        monkeypatch.delenv("FAKENODO_URL", raising=False)
        monkeypatch.setenv("FLASK_ENV", "development")
        monkeypatch.delenv("ZENODO_API_URL", raising=False)
        with test_client.application.app_context():
            service = ZenodoService()
            assert "sandbox.zenodo.org" in service.ZENODO_API_URL

    def test_get_zenodo_url_production(self, test_client, monkeypatch):
        """Test: Obtener URL de producción"""
        monkeypatch.delenv("FAKENODO_URL", raising=False)
        monkeypatch.setenv("FLASK_ENV", "production")
        monkeypatch.delenv("ZENODO_API_URL", raising=False)
        with test_client.application.app_context():
            service = ZenodoService()
            assert service.ZENODO_API_URL == "https://zenodo.org/api/deposit/depositions"

    def test_get_zenodo_access_token(self, test_client, monkeypatch):
        """Test: Obtener token de acceso"""
        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token-123")
        with test_client.application.app_context():
            service = ZenodoService()
            assert service.get_zenodo_access_token() == "test-token-123"

    def test_params_with_token(self, test_client, monkeypatch):
        """Test: Generar parámetros con token"""
        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        with test_client.application.app_context():
            service = ZenodoService()
            params = service._params()
            assert params == {"access_token": "test-token"}

    def test_params_without_token(self, test_client, monkeypatch):
        """Test: Generar parámetros sin token"""
        monkeypatch.delenv("ZENODO_ACCESS_TOKEN", raising=False)
        with test_client.application.app_context():
            service = ZenodoService()
            params = service._params()
            assert params == {}

    def test_params_with_custom_token(self, test_client):
        """Test: Generar parámetros con token personalizado"""
        with test_client.application.app_context():
            service = ZenodoService()
            params = service._params(token="custom-token")
            assert params == {"access_token": "custom-token"}


class TestZenodoServiceConnection:
    """Tests para conexión con Zenodo"""

    @patch("app.modules.zenodo.services.requests.get")
    def test_connection_success(self, mock_get, test_client, monkeypatch):
        """Test: Conexión exitosa con Zenodo"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        with test_client.application.app_context():
            service = ZenodoService()
            result = service.test_connection()
            assert result is True

    @patch("app.modules.zenodo.services.requests.get")
    def test_connection_failure(self, mock_get, test_client, monkeypatch):
        """Test: Fallo de conexión con Zenodo"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "invalid-token")
        with test_client.application.app_context():
            service = ZenodoService()
            result = service.test_connection()
            assert result is False

    @patch("app.modules.zenodo.services.requests.get")
    def test_connection_exception(self, mock_get, test_client):
        """Test: Excepción durante la conexión"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with test_client.application.app_context():
            service = ZenodoService()
            result = service.test_connection()
            assert result is False


class TestZenodoServiceDepositions:
    """Tests para operaciones con deposiciones"""

    @patch("app.modules.zenodo.services.requests.get")
    def test_get_all_depositions_success(self, mock_get, test_client, monkeypatch):
        """Test: Obtener todas las deposiciones exitosamente"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"id": 1, "title": "Test"}]
        mock_get.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        with test_client.application.app_context():
            service = ZenodoService()
            result = service.get_all_depositions()
            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0]["id"] == 1

    @patch("app.modules.zenodo.services.requests.get")
    def test_get_all_depositions_failure(self, mock_get, test_client):
        """Test: Fallo al obtener deposiciones"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        with test_client.application.app_context():
            service = ZenodoService()
            with pytest.raises(Exception, match="Failed to get depositions"):
                service.get_all_depositions()

    @patch("app.modules.zenodo.services.requests.get")
    def test_get_deposition_success(self, mock_get, test_client, monkeypatch):
        """Test: Obtener una deposición específica"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "title": "Test Deposition"}
        mock_get.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        with test_client.application.app_context():
            service = ZenodoService()
            result = service.get_deposition(123)
            assert result["id"] == 123
            assert result["title"] == "Test Deposition"

    @patch("app.modules.zenodo.services.requests.get")
    def test_get_deposition_failure(self, mock_get, test_client):
        """Test: Fallo al obtener deposición"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        with test_client.application.app_context():
            service = ZenodoService()
            with pytest.raises(Exception, match="Failed to get deposition"):
                service.get_deposition(999)

    @patch("app.modules.zenodo.services.requests.post")
    def test_create_new_deposition_success(self, mock_post, test_client, sample_dataset, monkeypatch):
        """Test: Crear nueva deposición exitosamente"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 456, "doi": "10.5281/zenodo.456"}
        mock_post.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset.id)
            service = ZenodoService()
            result = service.create_new_deposition(dataset)
            assert result["id"] == 456
            assert "doi" in result

    @patch("app.modules.zenodo.services.requests.post")
    def test_create_new_deposition_failure(self, mock_post, test_client, sample_dataset):
        """Test: Fallo al crear deposición"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Invalid metadata"}
        mock_post.return_value = mock_response

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset.id)
            service = ZenodoService()
            with pytest.raises(Exception, match="Failed to create deposition"):
                service.create_new_deposition(dataset)

    @patch("app.modules.zenodo.services.requests.post")
    def test_publish_deposition_success(self, mock_post, test_client, monkeypatch):
        """Test: Publicar deposición exitosamente"""
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {"id": 789, "state": "done"}
        mock_post.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        with test_client.application.app_context():
            service = ZenodoService()
            result = service.publish_deposition(789)
            assert result["id"] == 789
            assert result["state"] == "done"

    @patch("app.modules.zenodo.services.requests.post")
    def test_publish_deposition_failure(self, mock_post, test_client):
        """Test: Fallo al publicar deposición"""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response

        with test_client.application.app_context():
            service = ZenodoService()
            with pytest.raises(Exception, match="Failed to publish deposition"):
                service.publish_deposition(999)


class TestZenodoServiceDOI:
    """Tests para operaciones con DOI"""

    @patch("app.modules.zenodo.services.requests.get")
    def test_get_doi_success(self, mock_get, test_client, monkeypatch):
        """Test: Obtener DOI de una deposición"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123, "doi": "10.5281/zenodo.123"}
        mock_get.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        with test_client.application.app_context():
            service = ZenodoService()
            doi = service.get_doi(123)
            assert doi == "10.5281/zenodo.123"

    @patch("app.modules.zenodo.services.requests.get")
    def test_get_doi_not_found(self, mock_get, test_client, monkeypatch):
        """Test: DOI no encontrado"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 123}
        mock_get.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        with test_client.application.app_context():
            service = ZenodoService()
            doi = service.get_doi(123)
            assert doi is None


class TestZenodoServiceFileUpload:
    """Tests para carga de archivos"""

    @patch("app.modules.zenodo.services.requests.post")
    @patch("builtins.open", create=True)
    def test_upload_file_success(
        self, mock_open, mock_post, test_client, sample_dataset, sample_feature_model, monkeypatch
    ):
        """Test: Subir archivo exitosamente"""
        # Mock file
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": "file-123", "filename": "test_model.uvl"}
        mock_post.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("WORKING_DIR", tempfile.gettempdir())

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset.id)
            fm = FeatureModel.query.get(sample_feature_model.id)
            service = ZenodoService()

            # Create a dummy file
            user_id = dataset.user_id
            file_dir = os.path.join(tempfile.gettempdir(), f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(file_dir, exist_ok=True)
            file_path = os.path.join(file_dir, "test_model.uvl")
            with open(file_path, "w") as f:
                f.write("test content")

            try:
                result = service.upload_file(dataset, 123, fm, user=dataset.user)
                assert result["filename"] == "test_model.uvl"
            finally:
                # Cleanup
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(file_dir):
                    os.rmdir(file_dir)

    @patch("app.modules.zenodo.services.requests.post")
    def test_upload_file_not_found(self, mock_post, test_client, sample_dataset, sample_feature_model):
        """Test: Archivo no encontrado"""
        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset.id)
            fm = FeatureModel.query.get(sample_feature_model.id)
            service = ZenodoService()

            with pytest.raises(Exception, match="File not found"):
                service.upload_file(dataset, 123, fm, user=dataset.user)

    @patch("app.modules.zenodo.services.requests.post")
    @patch("builtins.open", create=True)
    def test_upload_file_failure(
        self, mock_open, mock_post, test_client, sample_dataset, sample_feature_model, monkeypatch
    ):
        """Test: Fallo al subir archivo"""
        # Mock file
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"message": "Upload failed"}
        mock_post.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("WORKING_DIR", tempfile.gettempdir())

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset.id)
            fm = FeatureModel.query.get(sample_feature_model.id)
            service = ZenodoService()

            # Create a dummy file
            user_id = dataset.user_id
            file_dir = os.path.join(tempfile.gettempdir(), f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(file_dir, exist_ok=True)
            file_path = os.path.join(file_dir, "test_model.uvl")
            with open(file_path, "w") as f:
                f.write("test content")

            try:
                with pytest.raises(Exception, match="Failed to upload files"):
                    service.upload_file(dataset, 123, fm, user=dataset.user)
            finally:
                # Cleanup
                if os.path.exists(file_path):
                    os.remove(file_path)
                if os.path.exists(file_dir):
                    os.rmdir(file_dir)


class TestZenodoServiceMetadata:
    """Tests para metadatos"""

    @patch("app.modules.zenodo.services.requests.post")
    def test_create_deposition_with_publication_type(self, mock_post, test_client, sample_dataset, monkeypatch):
        """Test: Crear deposición con tipo de publicación"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123}
        mock_post.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset.id)
            dataset.ds_meta_data.publication_type = PublicationType.JOURNAL_ARTICLE
            dataset.ds_meta_data.publication_doi = "10.1234/test"
            db.session.commit()

            service = ZenodoService()
            result = service.create_new_deposition(dataset)
            assert result["id"] == 123

            # Verify the request was made with correct metadata
            call_args = mock_post.call_args
            json_data = call_args[1]["json"]
            assert json_data["metadata"]["upload_type"] == "publication"
            assert json_data["metadata"]["publication_type"] == "article"

    @patch("app.modules.zenodo.services.requests.post")
    def test_create_deposition_with_tags(self, mock_post, test_client, sample_dataset, monkeypatch):
        """Test: Crear deposición con tags"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 123}
        mock_post.return_value = mock_response

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")

        with test_client.application.app_context():
            dataset = BaseDataset.query.get(sample_dataset.id)
            dataset.ds_meta_data.tags = "feature model, software"
            db.session.commit()
            # Verify the request was made with correct keywords
            call_args = mock_post.call_args
            json_data = call_args[1]["json"]
            assert "feature model" in json_data["metadata"]["keywords"]
            assert "software" in json_data["metadata"]["keywords"]
            assert "uvlhub" in json_data["metadata"]["keywords"]
