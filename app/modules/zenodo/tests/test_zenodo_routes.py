from unittest.mock import Mock, patch


class TestZenodoRoutes:
    """Tests de rutas de Zenodo"""

    def test_zenodo_home_page(self, test_client):
        """GET /zenodo - Página principal de Zenodo"""
        response = test_client.get("/zenodo")
        assert response.status_code == 200
        assert b"zenodo" in response.data.lower() or b"Zenodo" in response.data

    @patch("app.modules.zenodo.routes.ZenodoService")
    def test_zenodo_test_endpoint_success(self, mock_service, test_client):
        """GET /zenodo/test - Test exitoso de conexión"""
        mock_instance = Mock()
        mock_instance.test_full_connection.return_value = {
            "success": True,
            "messages": ["Connection successful"],
        }
        mock_service.return_value = mock_instance

        response = test_client.get("/zenodo/test")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is True

    @patch("app.modules.zenodo.routes.ZenodoService")
    def test_zenodo_test_endpoint_failure(self, mock_service, test_client):
        """GET /zenodo/test - Test fallido de conexión"""
        mock_instance = Mock()
        mock_instance.test_full_connection.return_value = {
            "success": False,
            "messages": ["Connection failed"],
        }
        mock_service.return_value = mock_instance

        response = test_client.get("/zenodo/test")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is False

    @patch("app.modules.zenodo.routes.requests.delete")
    @patch("app.modules.zenodo.routes.requests.post")
    @patch("app.modules.zenodo.routes.requests.get")
    def test_zenodo_demo_endpoint_success(self, mock_get, mock_post, mock_delete, test_client, monkeypatch):
        """GET /zenodo/demo - Demo exitoso"""
        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("FAKENODO_URL", "http://localhost:9999/api/deposit/depositions")

        mock_post_response = Mock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"id": 123}
        mock_post_response.ok = True

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"id": 123, "title": "Test"}
        mock_get_response.ok = True

        mock_delete_response = Mock()
        mock_delete_response.status_code = 204
        mock_delete_response.text = ""

        mock_post.return_value = mock_post_response
        mock_get.return_value = mock_get_response
        mock_delete.return_value = mock_delete_response

        response = test_client.get("/zenodo/demo")
        assert response.status_code == 200
        json_data = response.get_json()
        assert "steps" in json_data

    @patch("app.modules.zenodo.routes.requests.post")
    def test_zenodo_demo_endpoint_create_failure(self, mock_post, test_client, monkeypatch):
        """GET /zenodo/demo - Fallo al crear deposición"""
        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("FAKENODO_URL", "http://localhost:9999/api/deposit/depositions")

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Bad request"}
        mock_response.text = '{"error": "Bad request"}'
        mock_post.return_value = mock_response

        response = test_client.get("/zenodo/demo")
        assert response.status_code == 200
        json_data = response.get_json()
        assert json_data["success"] is False
        assert "steps" in json_data

    @patch("app.modules.zenodo.routes.requests.post")
    def test_zenodo_demo_endpoint_exception(self, mock_post, test_client, monkeypatch):
        """GET /zenodo/demo - Manejo de excepciones"""
        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("FAKENODO_URL", "http://localhost:9999/api/deposit/depositions")

        mock_post.side_effect = Exception("Network error")

        response = test_client.get("/zenodo/demo")
        assert response.status_code == 200
        json_data = response.get_json()
        assert "steps" in json_data
        assert any(step.get("name") == "exception" for step in json_data["steps"])


class TestZenodoRouteHelpers:
    """Tests para funciones auxiliares de rutas"""

    @patch("app.modules.zenodo.routes.requests.delete")
    @patch("app.modules.zenodo.routes.requests.post")
    @patch("app.modules.zenodo.routes.requests.get")
    def test_demo_creates_temp_file(self, mock_get, mock_post, mock_delete, test_client, monkeypatch):
        """GET /zenodo/demo - Verifica creación de archivo temporal"""
        import os
        import tempfile

        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("FAKENODO_URL", "http://localhost:9999/api/deposit/depositions")

        mock_post_response = Mock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"id": 123}
        mock_post_response.ok = True

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"id": 123}
        mock_get_response.ok = True

        mock_delete_response = Mock()
        mock_delete_response.status_code = 204
        mock_delete_response.text = ""

        mock_post.return_value = mock_post_response
        mock_get.return_value = mock_get_response
        mock_delete.return_value = mock_delete_response

        response = test_client.get("/zenodo/demo")
        assert response.status_code == 200

        tmpfile = os.path.join(tempfile.gettempdir(), "uvlhub_demo.txt")
        assert not os.path.exists(tmpfile)
        json_data = response.get_json()
        assert "steps" in json_data

    @patch("app.modules.zenodo.routes.requests.delete")
    @patch("app.modules.zenodo.routes.requests.post")
    @patch("app.modules.zenodo.routes.requests.get")
    def test_demo_includes_all_steps(self, mock_get, mock_post, mock_delete, test_client, monkeypatch):
        """GET /zenodo/demo - Verifica que incluye todos los pasos"""
        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("FAKENODO_URL", "http://localhost:9999/api/deposit/depositions")

        mock_post_response = Mock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"id": 123}
        mock_post_response.ok = True

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"id": 123}
        mock_get_response.ok = True

        mock_delete_response = Mock()
        mock_delete_response.status_code = 204
        mock_delete_response.text = ""

        mock_post.return_value = mock_post_response
        mock_get.return_value = mock_get_response
        mock_delete.return_value = mock_delete_response

        response = test_client.get("/zenodo/demo")
        json_data = response.get_json()

        assert len(json_data["steps"]) > 0

        for step in json_data["steps"]:
            assert "name" in step
            assert "method" in step
            assert "url" in step
            assert "status" in step
            assert "ok" in step

    @patch("app.modules.zenodo.routes.requests.delete")
    @patch("app.modules.zenodo.routes.requests.post")
    @patch("app.modules.zenodo.routes.requests.get")
    def test_demo_step_structure(self, mock_get, mock_post, mock_delete, test_client, monkeypatch):
        """GET /zenodo/demo - Verifica estructura de cada paso"""
        monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "test-token")
        monkeypatch.setenv("FAKENODO_URL", "http://localhost:9999/api/deposit/depositions")

        mock_post_response = Mock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {"id": 456}
        mock_post_response.ok = True

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"id": 456}
        mock_get_response.ok = True

        mock_delete_response = Mock()
        mock_delete_response.status_code = 204
        mock_delete_response.text = ""

        mock_post.return_value = mock_post_response
        mock_get.return_value = mock_get_response
        mock_delete.return_value = mock_delete_response

        response = test_client.get("/zenodo/demo")
        json_data = response.get_json()

        for step in json_data["steps"]:
            if step["status"] >= 200 and step["status"] < 300:
                assert step["ok"] is True
            else:
                assert step["ok"] is False or step["status"] in [201, 202, 204]
