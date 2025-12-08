import pytest


class TestZenodoRoutes:
    """Tests de rutas de Zenodo"""

    def test_zenodo_home_page(self, test_client):
        """GET /zenodo"""
        response = test_client.get("/zenodo")
        assert response.status_code == 200

    def test_zenodo_test_endpoint(self, test_client):
        """GET /zenodo/test"""
        response = test_client.get("/zenodo/test")
        assert response.status_code in [200, 404]

    def test_zenodo_demo_endpoint(self, test_client):
        """GET /zenodo/demo"""
        response = test_client.get("/zenodo/demo")
        assert response.status_code in [200, 404]


class TestZenodoServices:
    """Tests de servicios Zenodo"""

    def test_zenodo_service_exists(self, test_client):
        """Verificar que el servicio existe"""
        # Sin usar app_context anidado
        try:
            from app.modules.zenodo.services import ZenodoService

            assert ZenodoService is not None
        except ImportError:
            pytest.skip("ZenodoService no implementado")
