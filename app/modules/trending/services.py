from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import selectinload

from app import db
from app.modules.dataset.models import BaseDataset, DSDownloadRecord, DSMetaData, DSViewRecord
from app.modules.trending.repositories import TrendingRepository
from core.services.BaseService import BaseService


class TrendingService(BaseService):
    def __init__(self):
        super().__init__(TrendingRepository())


def trending(metric: str = "downloads", period: str = "week", limit: int = 10, **kwargs):
    """
    Returns a list of dicts with dataset and aggregated metrics.

    Accepts extra kwargs for backward compatibility (e.g. allow_mock) and ignores them.
    """

    period_days = {"day": 1, "week": 7, "month": 30}.get(period, 7)
    if limit <= 0:
        return []
    now = datetime.utcnow()
    since_period = now - timedelta(days=period_days)
    since_1d = now - timedelta(days=1)

    def agg_subq(model, date_col, since, count_label):
        return (
            db.session.query(
                getattr(model, "dataset_id").label("dataset_id"),
                func.count(getattr(model, "id")).label(count_label),
            )
            .filter(getattr(model, date_col) >= since)
            .group_by(getattr(model, "dataset_id"))
            .subquery()
        )

    views_p = agg_subq(DSViewRecord, "view_date", since_period, "views_p")
    dls_p = agg_subq(DSDownloadRecord, "download_date", since_period, "downloads_p")
    views_1d = agg_subq(DSViewRecord, "view_date", since_1d, "views_1d")
    dls_1d = agg_subq(DSDownloadRecord, "download_date", since_1d, "downloads_1d")

    Vp = func.coalesce(views_p.c.views_p, 0)
    Dp = func.coalesce(dls_p.c.downloads_p, 0)
    Vd = func.coalesce(views_1d.c.views_1d, 0)
    Dd = func.coalesce(dls_1d.c.downloads_1d, 0)

    base = (
        db.session.query(
            BaseDataset.id.label("dataset_id"),
            Vp.label("views"),
            Dp.label("downloads"),
            Vd.label("views_1d"),
            Dd.label("downloads_1d"),
        )
        .join(DSMetaData, DSMetaData.id == BaseDataset.ds_meta_data_id)
        .filter(DSMetaData.dataset_doi.isnot(None))
        .outerjoin(views_p, views_p.c.dataset_id == BaseDataset.id)
        .outerjoin(dls_p, dls_p.c.dataset_id == BaseDataset.id)
        .outerjoin(views_1d, views_1d.c.dataset_id == BaseDataset.id)
        .outerjoin(dls_1d, dls_1d.c.dataset_id == BaseDataset.id)
    )

    if metric == "views":
        base = base.filter(Vp > 0).order_by(Vp.desc(), BaseDataset.id.asc())
    elif metric == "downloads":
        base = base.filter(Dp > 0).order_by(Dp.desc(), BaseDataset.id.asc())
    elif metric == "score_v2":
        score_v2 = (Dd * 3.0) + (Dp * 2.0) + (Vd * 1.0) + (Vp * 0.5)
        base = base.filter((Vp + Dp + Vd + Dd) > 0).order_by(score_v2.desc(), BaseDataset.id.asc())
    else:
        score = (Dp * 2) + Vp
        base = base.filter((Vp + Dp) > 0).order_by(score.desc(), BaseDataset.id.asc())

    rows = base.limit(limit).all()
    if not rows:
        return []

    ids = [r.dataset_id for r in rows]
    datasets = BaseDataset.query.options(selectinload(BaseDataset.ds_meta_data)).filter(BaseDataset.id.in_(ids)).all()
    ds_map = {d.id: d for d in datasets}

    results = []
    for r in rows:
        ds = ds_map.get(r.dataset_id)
        if ds:
            results.append(
                {
                    "dataset": ds,
                    "views": int(r.views or 0),
                    "downloads": int(r.downloads or 0),
                    "views_1d": int(r.views_1d or 0),
                    "downloads_1d": int(r.downloads_1d or 0),
                }
            )
    return results
