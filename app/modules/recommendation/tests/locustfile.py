from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing


class RecommendationBehavior(TaskSet):
    def on_start(self):
        self.index()

    @task
    def index(self):
        response = self.client.get("/recommendation")

        if response.status_code != 200:
            print(f"Recommendation index failed: {response.status_code}")


class RecommendationUser(HttpUser):
    tasks = [RecommendationBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
