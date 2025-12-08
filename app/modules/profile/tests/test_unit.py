class TestProfileRoutes:
    """Tests de rutas profile"""

    def test_profile_edit_page(self, test_client):
        """GET /profile/edit"""
        login(test_client, "test@example.com", "test1234")
        response = test_client.get("/profile/edit")
        assert response.status_code == 200

    def test_profile_summary_page(self, test_client):
        """GET /profile/summary"""
        login(test_client, "test@example.com", "test1234")
        response = test_client.get("/profile/summary")
        assert response.status_code == 200


def login(client, email, password):
    """Helper para login"""
    return client.post("/login", data={"email": email, "password": password})
