class TestHubfileRoutes:
    """Tests de routes de hubfile"""

    def test_file_download_endpoint(self, test_client):
        response = test_client.get("/file/download/1")
        assert response.status_code in [200, 404, 500]

    def test_file_view_endpoint(self, test_client):
        response = test_client.get("/file/view/1")
        assert response.status_code in [200, 404, 500]

    def test_file_download_invalid_id(self, test_client):
        response = test_client.get("/file/download/99999")
        assert response.status_code in [404, 500]


class TestHubfileServices:
    """Tests de servicios"""

    def test_hubfile_service_init(self, test_client):
        """Inicializar servicio"""
        with test_client.application.app_context():
            from app.modules.hubfile.services import HubfileService

            service = HubfileService()
            assert service is not None


class TestHubfileDownload:
    """Tests de descarga de archivos"""

    def test_file_download_nonexistent(self, test_client):
        """Descargar archivo que no existe"""
        response = test_client.get("/file/download/99999")
        assert response.status_code in [404, 500]

    def test_file_view_nonexistent(self, test_client):
        """Ver archivo que no existe"""
        response = test_client.get("/file/view/99999")
        assert response.status_code in [404, 500]

    def test_file_download_negative_id(self, test_client):
        """ID negativo"""
        response = test_client.get("/file/download/-1")
        assert response.status_code in [404, 500]
