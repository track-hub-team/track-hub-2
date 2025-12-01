import pytest

from app import db
from app.modules.dataset.models import Author, DSDownloadRecord, DSMetaData, PublicationType, UVLDataset
from app.modules.recommendation.services import RecommendationService


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Add HERE new elements to the database that you want to exist in the test context.
        # DO NOT FORGET to use db.session.add(<element>) and db.session.commit() to save the data.
        pass

    yield test_client


def _create_dataset(title, tags, author_names, user_id=1):
    """Helper to create test UVL datasets with metadata and authors."""
    meta = DSMetaData(
        title=title,
        description=f"Desc {title}",
        publication_type=PublicationType.NONE,
        tags=tags,
    )
    db.session.add(meta)
    db.session.flush()
    for name in author_names:
        db.session.add(Author(name=name, ds_meta_data_id=meta.id))
    ds = UVLDataset(user_id=user_id, ds_meta_data_id=meta.id)
    db.session.add(ds)
    return ds


def test_related_datasets_basic(test_client):
    """Test that related datasets are correctly ranked by author/tag overlap and downloads."""
    # Use existing test user from fixture (user_id=1 already exists)

    # Target and candidates
    target = _create_dataset("Target", "tagA,tagB", ["Alice", "Bob"])
    d1 = _create_dataset("Overlap Authors", "tagZ", ["Alice"])  # author overlap
    d2 = _create_dataset("Overlap Tags", "tagA,tagX", ["Carol"])  # tag overlap
    d3 = _create_dataset("Strong Overlap", "tagA,tagB", ["Alice", "Bob"])  # strong overlap
    d4 = _create_dataset("No Overlap", "tagY", ["Dave"])  # no overlap

    db.session.commit()

    # Add downloads to affect ranking
    db.session.add(DSDownloadRecord(dataset_id=d2.id, download_cookie="c1"))
    db.session.add(DSDownloadRecord(dataset_id=d3.id, download_cookie="c2"))
    db.session.add(DSDownloadRecord(dataset_id=d3.id, download_cookie="c3"))
    db.session.commit()

    svc = RecommendationService()
    related = svc.get_related_datasets(target, limit=10)

    ids = [d.id for d in related]
    assert target.id not in ids, "Target dataset should not be in recommendations"
    assert d4.id not in ids, "Dataset with no overlap should not be in recommendations"
    assert set([d1.id, d2.id, d3.id]).issubset(ids), "Datasets with overlap should be in recommendations"
    assert related[0].id == d3.id, "Dataset with strongest overlap should rank first"
