from locust import HttpUser, TaskSet, between, task

from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token, login


class VersioningBehavior(TaskSet):
    """Comportamiento de usuario para el módulo de versionado"""

    def on_start(self):
        """Inicializar datos al comenzar"""
        self.login()
        self.dataset_id = 1  # ID de dataset para pruebas (ajustar según tu BD)
        self.version_ids = []

    def login(self):
        """Autenticarse antes de realizar acciones"""
        response = login(self, "test@example.com", "test1234")
        get_csrf_token(response)

    @task(3)
    def list_versions(self):
        """Ver historial de versiones de un dataset"""
        response = self.client.get(f"/dataset/{self.dataset_id}/versions", name="/dataset/[id]/versions")
        get_csrf_token(response)

    @task(2)
    def api_list_versions(self):
        """Obtener versiones vía API JSON"""
        response = self.client.get(f"/api/dataset/{self.dataset_id}/versions", name="/api/dataset/[id]/versions")

        if response.status_code == 200:
            try:
                data = response.json()
                if data.get("versions"):
                    self.version_ids = [v["id"] for v in data["versions"]]
            except Exception:
                pass

    @task(2)
    def api_get_version(self):
        """Obtener detalles de una versión específica"""
        # Primero asegurarse de tener versiones
        if not self.version_ids:
            self.api_list_versions()

        if self.version_ids:
            version_id = self.version_ids[0]
            self.client.get(f"/api/version/{version_id}", name="/api/version/[id]")

    @task(1)
    def compare_versions(self):
        """Comparar dos versiones del mismo dataset"""
        if not self.version_ids:
            self.api_list_versions()

        if len(self.version_ids) >= 2:
            v1_id = self.version_ids[0]
            v2_id = self.version_ids[1]

            response = self.client.get(f"/versions/{v1_id}/compare/{v2_id}", name="/versions/[id]/compare/[id]")
            get_csrf_token(response)

    @task(1)
    def create_version(self):
        """Crear una nueva versión del dataset"""
        response = self.client.get(f"/dataset/{self.dataset_id}/versions")
        csrf_token = get_csrf_token(response)

        response = self.client.post(
            f"/dataset/{self.dataset_id}/create_version",
            data={"csrf_token": csrf_token, "changelog": "Locust performance test version", "bump_type": "patch"},
            name="/dataset/[id]/create_version",
        )


class VersioningUser(HttpUser):
    """Usuario simulado para tests de carga del módulo versioning"""

    tasks = [VersioningBehavior]
    wait_time = between(5, 9)  # Entre 5 y 9 segundos entre tareas
    host = get_host_for_locust_testing()


class ReadOnlyVersioningUser(HttpUser):
    """Usuario que solo consulta versiones (sin crear)"""

    wait_time = between(3, 7)
    host = get_host_for_locust_testing()

    @task(4)
    def view_versions(self):
        """Solo ver historial de versiones"""
        response = self.client.get("/dataset/1/versions")
        get_csrf_token(response)

    @task(3)
    def check_api_versions(self):
        """Consultar API de versiones"""
        self.client.get("/api/dataset/1/versions")
