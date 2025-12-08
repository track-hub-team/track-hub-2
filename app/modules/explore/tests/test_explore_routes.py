def test_explore_page(test_client):
    """GET /explore"""
    response = test_client.get("/explore")
    assert response.status_code == 200
    assert b"explore" in response.data.lower() or b"dataset" in response.data.lower()


class TestExploreServices:
    """Tests de servicios de explore"""

    def test_explore_service_init(self, test_client):
        """Inicializar servicio"""
        with test_client.application.app_context():
            from app.modules.explore.services import ExploreService

            service = ExploreService()
            assert service is not None

    def test_explore_page_content(self, test_client):
        """Contenido de página explore"""
        response = test_client.get("/explore")
        assert response.status_code == 200
        assert b"explore" in response.data.lower() or b"dataset" in response.data.lower()

    def test_explore_forms(self, test_client):
        """Forms de explore"""
        with test_client.application.app_context():
            from app.modules.explore.forms import ExploreForm

            assert ExploreForm is not None
