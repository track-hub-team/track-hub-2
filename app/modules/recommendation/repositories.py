import logging
from datetime import datetime
from typing import cast

from sqlalchemy import func, or_
from sqlalchemy.sql.elements import BinaryExpression

from app.modules.dataset.models import Author, BaseDataset, DSDownloadRecord, DSMetaData
from core.repositories.BaseRepository import BaseRepository

logger = logging.getLogger(__name__)


class RecommendationRepository(BaseRepository):
    """Repositorio para obtener datasets relacionados.

    Usa `BaseDataset` como modelo raíz para poder consultar polimórficamente
    (uvl, gpx, etc.). No crea entidades nuevas.
    """

    def __init__(self):
        super().__init__(BaseDataset)

    def get_related_datasets(self, dataset_id: int, limit: int = 6):
        """Calcula datasets relacionados por autores/tags y los ordena con un scoring.

        - +3 por autor coincidente
        - +2 por tag coincidente
        - +1 * (descargas normalizadas)
        - + recencia (0..1) con ventana de 180 días
        """
        target: BaseDataset = self.model.query.join(DSMetaData).filter(BaseDataset.id == dataset_id).first()
        if not target:
            return []

        target_author_keys = set()
        for a in target.ds_meta_data.authors:
            key = (a.name or "").strip().lower()
            if a.orcid:
                key += f"|{a.orcid.strip().lower()}"
            target_author_keys.add(key)

        target_tags = set([t.strip().lower() for t in (target.ds_meta_data.tags or "").split(",") if t.strip()])

        query = self.model.query.join(DSMetaData).outerjoin(Author, Author.ds_meta_data_id == DSMetaData.id)
        query = query.filter(BaseDataset.id != target.id)

        filters = []
        if target_author_keys:
            simple_author_names = [k.split("|")[0] for k in target_author_keys]
            filters.append(func.lower(Author.name).in_(simple_author_names))
        if target_tags:
            tag_like_filters = [DSMetaData.tags.ilike(f"%{tag}%") for tag in target_tags]
            if tag_like_filters:
                filters.append(cast(BinaryExpression, or_(*tag_like_filters)))

        if filters:
            query = query.filter(or_(*filters))
        else:
            return []

        candidates = query.distinct().all()
        if not candidates:
            return []

        download_counts = {
            r.dataset_id: r.count
            for r in (
                self.session.query(DSDownloadRecord.dataset_id, func.count(DSDownloadRecord.id).label("count"))
                .group_by(DSDownloadRecord.dataset_id)
                .all()
            )
        }
        max_downloads = max(download_counts.values(), default=0)

        now = datetime.utcnow()
        scored = []
        for ds in candidates:
            # Autores
            author_overlap = 0
            for a in ds.ds_meta_data.authors:
                key = (a.name or "").strip().lower()
                key_orcid = key + (f"|{a.orcid.strip().lower()}" if a.orcid else "")
                if key in target_author_keys or key_orcid in target_author_keys:
                    author_overlap += 1

            tags_ds = set([t.strip().lower() for t in (ds.ds_meta_data.tags or "").split(",") if t.strip()])
            tag_overlap = len(target_tags & tags_ds)

            downloads = download_counts.get(ds.id, 0)
            downloads_score = (downloads / max_downloads) if max_downloads > 0 else 0

            age_days = (now - ds.created_at).days if ds.created_at else 0
            recency_score = max(0.0, 1 - (age_days / 180))

            score = author_overlap * 3 + tag_overlap * 2 + downloads_score * 1 + recency_score
            scored.append((ds, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [ds for ds, _ in scored[:limit]]
