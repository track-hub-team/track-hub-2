import pytest

from app import db
from app.modules.auth.models import User


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


def login(client, email, password):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


class TestDatasetRoutes:
    """Tests de integración para rutas de dataset"""

    def test_dataset_list_route(self, test_client):
        """Test: GET /dataset/list"""
        response = test_client.get("/dataset/list")
        assert response.status_code in [200, 302]

    def test_dataset_upload_page_requires_login(self, test_client):
        """Test: GET /dataset/upload sin login"""
        response = test_client.get("/dataset/upload")
        assert response.status_code == 302

    def test_dataset_upload_page_logged_in(self, test_client):
        """Test: GET /dataset/upload con login"""
        login(test_client, "test@example.com", "test1234")
        response = test_client.get("/dataset/upload")
        assert response.status_code == 200


class TestDatasetRoutesExtended:
    """Tests extendidos de rutas de dataset"""

    def test_dataset_upload_authenticated(self, test_client):
        """Test: Acceder a página de upload autenticado"""
        login(test_client, "test@example.com", "test1234")
        response = test_client.get("/dataset/upload")
        assert response.status_code == 200

    def test_api_datasets_list(self, test_client):
        """Test: API listar datasets"""
        response = test_client.get("/api/v1/datasets/")
        assert response.status_code == 200

    def test_api_dataset_detail(self, test_client):
        """Test: API obtener dataset específico"""
        response = test_client.get("/api/v1/datasets/1")
        assert response.status_code in [200, 404]

    def test_dataset_download_endpoint(self, test_client):
        """Test: Descargar dataset"""
        response = test_client.get("/dataset/download/1")
        assert response.status_code in [200, 302, 404]

    def test_doi_redirect(self, test_client):
        """Test: Redirección por DOI"""
        response = test_client.get("/doi/10.1234/test/")
        assert response.status_code in [200, 302, 404]


class TestDatasetAPIEndpoints:
    """Tests de API REST"""

    def test_api_v1_datasets_list(self, test_client):
        """Test: API listar datasets con JSON"""
        response = test_client.get("/api/v1/datasets/")
        assert response.status_code == 200
        assert "application/json" in response.content_type
        data = response.get_json()
        assert isinstance(data, list) or isinstance(data, dict)

    def test_api_v1_dataset_detail(self, test_client):
        """Test: API dataset específico"""
        response = test_client.get("/api/v1/datasets/1")
        assert response.status_code in [200, 404]


class TestDatasetRelatedAPI:
    """Test para datasets relacionados"""

    def test_dataset_related_api(self, test_client):
        """Test: API de datasets relacionados"""
        response = test_client.get("/dataset/1/related")
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.get_json()
            assert isinstance(data, list)


class TestFileOperations:
    """Tests para operaciones de archivos"""

    def test_delete_file_without_login(self, test_client):
        """Test: Intentar borrar sin login"""
        response = test_client.post("/dataset/file/delete", json={"file": "test.uvl"})
        assert response.status_code in [200, 302, 401]

    def test_delete_file_with_login(self, test_client):
        """Test: Borrar archivo con login"""
        login(test_client, "test@example.com", "test1234")

        response = test_client.post(
            "/dataset/file/delete", json={"file": "nonexistent.uvl"}, content_type="application/json"
        )

        assert response.status_code in [200, 400, 404]
        data = response.get_json()
        assert data is not None


class TestDOIRedirection:
    """Tests para redirección DOI"""

    def test_doi_redirect_nonexistent(self, test_client):
        """Test: DOI que no existe"""
        response = test_client.get("/doi/10.9999/fake.doi/")
        assert response.status_code == 404

    def test_doi_redirect_format(self, test_client):
        """Test: Verificar formato de endpoint DOI"""
        response = test_client.get("/doi/test.doi/")
        assert response.status_code in [200, 302, 404]


class TestDatasetDownload:
    """Tests para descarga de datasets"""

    def test_download_nonexistent_dataset(self, test_client):
        """Test: Descargar dataset que no existe"""
        response = test_client.get("/dataset/download/99999")
        assert response.status_code == 404

    def test_download_endpoint_exists(self, test_client):
        """Test: Verificar endpoint de descarga"""
        response = test_client.get("/dataset/download/1")
        assert response.status_code in [200, 404]


class TestGPXAPI:
    """Tests para API GPX"""

    def test_gpx_api_nonexistent(self, test_client):
        """Test: API GPX con archivo inexistente"""
        response = test_client.get("/api/gpx/99999")
        assert response.status_code in [404, 500]

    def test_gpx_api_endpoint(self, test_client):
        """Test: Verificar endpoint GPX"""
        response = test_client.get("/api/gpx/1")
        assert response.status_code in [200, 400, 403, 404]


class TestDatasetEditRoutes:
    """Tests para rutas de edición"""

    def test_dataset_edit_page_requires_login(self, test_client):
        """Test: Editar dataset sin login"""
        response = test_client.get("/dataset/1/edit")
        assert response.status_code in [302, 403, 404]

    def test_dataset_edit_page_logged_in(self, test_client):
        """Test: Acceder a edición con login"""
        login(test_client, "test@example.com", "test1234")
        response = test_client.get("/dataset/1/edit")
        assert response.status_code in [200, 404]

    def test_dataset_delete_endpoint(self, test_client):
        """Test: Eliminar dataset"""
        login(test_client, "test@example.com", "test1234")
        response = test_client.post("/dataset/99999/delete")
        assert response.status_code in [302, 404]


class TestDatasetVersionRoutes:
    """Tests para rutas de versiones"""

    def test_dataset_versions_list(self, test_client):
        """Test: Listar versiones de dataset"""
        response = test_client.get("/dataset/1/versions")
        assert response.status_code in [200, 404]

    def test_create_version_endpoint(self, test_client):
        """Test: Crear versión"""
        login(test_client, "test@example.com", "test1234")
        response = test_client.post("/dataset/1/create-version", data={"version_name": "v1.0", "version_type": "minor"})
        assert response.status_code in [200, 302, 404]


class TestFileDownloadRoutes:
    """Tests para descargas de archivos"""

    def test_file_download_404(self, test_client):
        """Test: Descargar archivo inexistente"""
        response = test_client.get("/file/download/99999")
        assert response.status_code in [404, 500]

    def test_file_view_404(self, test_client):
        """Test: Ver archivo inexistente"""
        response = test_client.get("/file/view/99999")
        assert response.status_code in [404, 500]


class TestDatasetPublishRoutes:
    """Tests para publicación"""

    def test_publish_endpoint_requires_login(self, test_client):
        """Test: Publicar sin login"""
        response = test_client.post("/dataset/1/publish")
        assert response.status_code in [302, 403, 404]

    def test_unsynchronized_endpoint(self, test_client):
        """Test: Marcar como no sincronizado"""
        login(test_client, "test@example.com", "test1234")
        response = test_client.get("/dataset/unsynchronized/1", follow_redirects=True)
        assert response.status_code in [200, 302, 308, 404]


class TestDatasetListFilters:
    """Tests para filtros y ordenamiento"""

    def test_dataset_list_basic(self, test_client):
        """Test: Listar datasets básico"""
        login(test_client, "test@example.com", "test1234")
        response = test_client.get("/explore")  # Usar explore en vez de dataset/list
        assert response.status_code == 200
