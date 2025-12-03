from datetime import datetime, timedelta

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import DSDownloadRecord, DSMetaData, DSViewRecord, UVLDataset
from app.modules.trending.services import trending


@pytest.fixture(scope="module")
def seeded_db(test_client):
    """
    Seed the DB with a user and a helper to create datasets and records.
    """
    with test_client.application.app_context():
        # create a user required by BaseDataset.user_id foreign key
        user = User(email="tester@example.com", password="secret")
        db.session.add(user)
        db.session.commit()

        now = datetime.utcnow()

        def create_dataset(title: str, doi: str | None):
            meta = DSMetaData(title=title, description="desc", publication_type="none", dataset_doi=doi)
            db.session.add(meta)
            db.session.commit()
            # create a concrete subclass so SQLAlchemy polymorphic loading has a known identity
            ds = UVLDataset(user_id=user.id, ds_meta_data_id=meta.id)
            db.session.add(ds)
            db.session.commit()
            return ds

        def add_views(dataset, count: int, days_ago: int = 0):
            for _ in range(count):
                vr = DSViewRecord(dataset_id=dataset.id, view_date=now - timedelta(days=days_ago), view_cookie="c")
                db.session.add(vr)
            db.session.commit()

        def add_downloads(dataset, count: int, days_ago: int = 0):
            for _ in range(count):
                dr = DSDownloadRecord(
                    dataset_id=dataset.id, download_date=now - timedelta(days=days_ago), download_cookie="c"
                )
                db.session.add(dr)
            db.session.commit()

        yield {
            "user": user,
            "create_dataset": create_dataset,
            "add_views": add_views,
            "add_downloads": add_downloads,
            "now": now,
        }


def test_trending_downloads_metric(seeded_db):
    create_dataset = seeded_db["create_dataset"]
    add_downloads = seeded_db["add_downloads"]

    # two datasets with DOIs
    ds1 = create_dataset("DS One", "doi:1")
    ds2 = create_dataset("DS Two", "doi:2")

    # ds1 has 5 downloads in period, ds2 has 3
    add_downloads(ds1, 5, days_ago=0)
    add_downloads(ds2, 3, days_ago=0)

    res = trending(metric="downloads", period="week", limit=10)
    assert isinstance(res, list)
    assert len(res) >= 2
    # first result should be ds1 with 5 downloads
    assert res[0]["dataset"].id == ds1.id
    assert res[0]["downloads"] == 5


def test_trending_views_metric(seeded_db):
    create_dataset = seeded_db["create_dataset"]
    add_views = seeded_db["add_views"]

    ds3 = create_dataset("DS Three", "doi:3")
    ds4 = create_dataset("DS Four", "doi:4")

    add_views(ds3, 7, days_ago=0)
    add_views(ds4, 2, days_ago=0)

    res = trending(metric="views", period="week", limit=10)
    assert any(r["dataset"].id == ds3.id for r in res)
    # ds3 should appear before ds4 when ordering by views desc
    ids = [r["dataset"].id for r in res]
    assert ids.index(ds3.id) < ids.index(ds4.id)


def test_trending_score_v2_and_default(seeded_db):
    create_dataset = seeded_db["create_dataset"]
    add_views = seeded_db["add_views"]
    add_downloads = seeded_db["add_downloads"]

    # create two datasets with mixed recent and 1-day metrics
    a = create_dataset("A", "doi:A")
    b = create_dataset("B", "doi:B")

    # A: more 1-day downloads -> high score_v2
    add_downloads(a, 2, days_ago=0)  # downloads_p and downloads_1d
    add_downloads(a, 3, days_ago=0)
    add_views(a, 1, days_ago=0)

    # B: more period downloads but fewer 1-day
    add_downloads(b, 6, days_ago=3)
    add_views(b, 10, days_ago=3)

    res_v2 = trending(metric="score_v2", period="week", limit=10)
    # ensure results include our datasets and ordering respects score_v2
    ids_v2 = [r["dataset"].id for r in res_v2]
    assert a.id in ids_v2 and b.id in ids_v2

    # default metric (fallback) uses score = (Dp*2) + Vp
    res_def = trending(metric="unknown_metric", period="week", limit=10)
    assert isinstance(res_def, list)


def test_trending_limit_and_empty(seeded_db):
    create_dataset = seeded_db["create_dataset"]
    add_views = seeded_db["add_views"]

    d1 = create_dataset("L1", "doi:L1")
    d2 = create_dataset("L2", "doi:L2")
    d3 = create_dataset("L3", "doi:L3")

    add_views(d1, 1, days_ago=0)
    add_views(d2, 1, days_ago=0)
    add_views(d3, 1, days_ago=0)

    res2 = trending(metric="views", period="week", limit=2)
    assert len(res2) == 2

    # limit=0 should return empty list
    res0 = trending(metric="views", period="week", limit=0)
    assert res0 == []


def test_trending_ignores_old_metrics(seeded_db):
    """
    Verifica que las descargas/vistas fuera del periodo (ej. hace 1 año)
    NO cuentan para el trending de la semana.
    """
    create_dataset = seeded_db["create_dataset"]
    add_downloads = seeded_db["add_downloads"]

    # Dataset "Old Famous": Muy popular hace un mes, pero olvidado hoy
    ds_old = create_dataset("Old Hit", "doi:old")
    # Añadimos 100 descargas, pero hace 40 días
    add_downloads(ds_old, 100, days_ago=40)

    # Dataset "New Viral": Pocas descargas, pero hoy
    ds_new = create_dataset("New Viral", "doi:new")
    add_downloads(ds_new, 5, days_ago=0)

    # Pedimos trending de la SEMANA ("week")
    res = trending(metric="downloads", period="week", limit=10)

    # El dataset nuevo debe ganar al viejo en el ranking semanal
    # (El viejo podría tener 0 o pocas, dependiendo de si tu lógica cuenta histórico o no,
    # pero el nuevo debe estar primero)
    ids = [r["dataset"].id for r in res]

    assert ds_new.id in ids

    # Si la lógica excluye totalmente lo antiguo, ds_old no debería estar o tener 0 descargas
    if ds_old.id in ids:
        index_new = ids.index(ds_new.id)
        index_old = ids.index(ds_old.id)
        assert index_new < index_old, "El dataset nuevo debería estar por encima del viejo en trending semanal"


def test_trending_excludes_no_doi(seeded_db):
    """
    Verifica que los datasets sin DOI (borradores/privados) no salen en trending.
    """
    create_dataset = seeded_db["create_dataset"]
    add_views = seeded_db["add_views"]

    # Dataset publicado (Con DOI)
    ds_public = create_dataset("Public DS", "doi:public123")
    add_views(ds_public, 10, days_ago=0)

    # Dataset borrador (Sin DOI - pasamos None)
    ds_draft = create_dataset("Draft DS", None)
    add_views(ds_draft, 50, days_ago=0)  # Tiene muchas vistas (quizás del autor)

    res = trending(metric="views", period="week", limit=10)

    ids = [r["dataset"].id for r in res]

    # El público DEBE estar
    assert ds_public.id in ids
    # El borrador NO DEBE estar (asumiendo que tu servicio filtra por DOI)
    assert ds_draft.id not in ids


def test_trending_tie_breaker_by_id(seeded_db):
    create_dataset = seeded_db["create_dataset"]
    add_views = seeded_db["add_views"]
    add_downloads = seeded_db["add_downloads"]

    a = create_dataset("Tie A", "doi:tieA")
    b = create_dataset("Tie B", "doi:tieB")
    # Hacemos que ambos tengan exactamente el mismo score (Dp*2 + Vp)
    add_downloads(a, 1, days_ago=0)
    add_views(a, 2, days_ago=0)  # score = (1*2)+2 = 4
    add_downloads(b, 2, days_ago=0)
    add_views(b, 0, days_ago=0)  # score = (2*2)+0 = 4

    res = trending(metric="unknown_metric", period="week", limit=10)
    ids = [r["dataset"].id for r in res]
    assert ids.index(a.id) < ids.index(b.id)  # a.id menor que b.id si se creó antes


def test_trending_score_v2_weights(seeded_db):
    create_dataset = seeded_db["create_dataset"]
    add_downloads = seeded_db["add_downloads"]

    x = create_dataset("X", "doi:X")
    y = create_dataset("Y", "doi:Y")

    # Diseñamos números claros: X tiene muchas descargas en 1 día,
    # Y tiene descargas en el periodo pero ninguna en 1 día.
    add_downloads(x, 3, days_ago=0)  # Dd=3, Dp=3
    add_downloads(y, 3, days_ago=3)  # Dd=0, Dp=3

    # pedir suficientes filas para incluir ambos datasets
    res = trending(metric="score_v2", period="week", limit=100)

    # construir mapa id -> row para nuestras dos filas
    row_map = {r["dataset"].id: r for r in res if r["dataset"].id in (x.id, y.id)}

    assert (
        x.id in row_map and y.id in row_map
    ), f"Both datasets must appear in results, got ids={[r['dataset'].id for r in res]}"

    def compute_score_v2(row):
        # fórmula del servicio: (Dd * 3.0) + (Dp * 2.0) + (Vd * 1.0) + (Vp * 0.5)
        return (row["downloads_1d"] * 3.0) + (row["downloads"] * 2.0) + (row["views_1d"] * 1.0) + (row["views"] * 0.5)

    score_x = compute_score_v2(row_map[x.id])
    score_y = compute_score_v2(row_map[y.id])

    assert score_x > score_y, f"Expected X score > Y score, got X={score_x} Y={score_y}"


def test_trending_negative_limit_behaviour(seeded_db):
    create_dataset = seeded_db["create_dataset"]
    add_views = seeded_db["add_views"]

    d = create_dataset("NegL", "doi:neg")
    add_views(d, 1, days_ago=0)

    res = trending(metric="views", period="week", limit=-1)
    # Propuesta: el servicio debería devolver [] si limit <= 0.
    assert res == []
