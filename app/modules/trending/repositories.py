from app.modules.trending.models import Trending
from core.repositories.BaseRepository import BaseRepository


class TrendingRepository(BaseRepository):
    def __init__(self):
        super().__init__(Trending)
