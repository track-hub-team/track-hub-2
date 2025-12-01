from app.modules.recommendation.repositories import RecommendationRepository
from core.services.BaseService import BaseService


class RecommendationService(BaseService):
    def __init__(self):
        super().__init__(RecommendationRepository())

    def get_related_datasets(self, dataset, limit: int = 6):
        if not dataset:
            return []
        return self.repository.get_related_datasets(dataset.id, limit=limit)
