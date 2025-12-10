from app import db
from app.modules.dataset.models import Author, DSDownloadRecord, DSMetaData, PublicationType, UVLDataset
from app.modules.recommendation.forms import RecommendationForm
from app.modules.recommendation.models import Recommendation
from app.modules.recommendation.repositories import RecommendationRepository
from app.modules.recommendation.services import RecommendationService


def _create_dataset(title, tags, author_names, user_id=1):
    """Create a test UVL dataset with metadata and authors."""
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

    dataset = UVLDataset(user_id=user_id, ds_meta_data_id=meta.id)
    db.session.add(dataset)
    return dataset


class TestRecommendationService:
    """Tests for recommendation ranking and filtering logic."""

    def test_basic_ranking(self, test_client):
        """Verify datasets are ranked by author/tag overlap, downloads, and recency."""
        target = _create_dataset("Target", "tagA,tagB", ["Alice", "Bob"])
        d1 = _create_dataset("Author Match", "tagZ", ["Alice"])
        d2 = _create_dataset("Tag Match", "tagA,tagX", ["Carol"])
        d3 = _create_dataset("Strong Match", "tagA,tagB", ["Alice", "Bob"])
        d4 = _create_dataset("No Match", "tagY", ["Dave"])

        db.session.commit()

        db.session.add(DSDownloadRecord(dataset_id=d2.id, download_cookie="c1"))
        db.session.add(DSDownloadRecord(dataset_id=d3.id, download_cookie="c2"))
        db.session.add(DSDownloadRecord(dataset_id=d3.id, download_cookie="c3"))
        db.session.commit()

        svc = RecommendationService()
        related = svc.get_related_datasets(target, limit=10)

        ids = [d.id for d in related]
        assert target.id not in ids
        assert d4.id not in ids
        assert set([d1.id, d2.id, d3.id]).issubset(ids)
        assert related[0].id == d3.id

    def test_none_dataset(self, test_client):
        """Verify empty list when dataset is None."""
        svc = RecommendationService()
        assert svc.get_related_datasets(None) == []

    def test_no_candidates(self, test_client):
        """Verify empty list when target has no overlapping datasets."""
        target = _create_dataset("Target", "tag1", ["Author1"])
        db.session.commit()

        svc = RecommendationService()
        assert svc.get_related_datasets(target, limit=5) == []

    def test_orcid_matching(self, test_client):
        """Verify authors are matched by ORCID."""
        target_meta = DSMetaData(
            title="Target ORCID",
            description="Dataset with ORCID author",
            publication_type=PublicationType.NONE,
            tags="orcid_tag",
        )
        db.session.add(target_meta)
        db.session.flush()
        db.session.add(Author(name="Alice", orcid="0000-0001-2345-6789", ds_meta_data_id=target_meta.id))
        db.session.add(UVLDataset(user_id=1, ds_meta_data_id=target_meta.id))

        candidate_meta = DSMetaData(
            title="Candidate ORCID",
            description="Dataset with same ORCID author",
            publication_type=PublicationType.NONE,
            tags="other_tag",
        )
        db.session.add(candidate_meta)
        db.session.flush()
        db.session.add(Author(name="Alice", orcid="0000-0001-2345-6789", ds_meta_data_id=candidate_meta.id))
        candidate = UVLDataset(user_id=1, ds_meta_data_id=candidate_meta.id)
        db.session.add(candidate)
        db.session.commit()

        target = db.session.query(UVLDataset).filter_by(ds_meta_data_id=target_meta.id).first()
        svc = RecommendationService()
        related = svc.get_related_datasets(target, limit=10)

        assert any(d.id == candidate.id for d in related)

    def test_no_overlap_returns_empty(self, test_client):
        """Verify no results when target has no tags or authors."""
        target = _create_dataset("No Data", "", [])
        _create_dataset("Other", "tag1", ["Author1"])
        db.session.commit()

        svc = RecommendationService()
        assert svc.get_related_datasets(target) == []

    def test_limit_respected(self, test_client):
        """Verify limit parameter is respected."""
        target = _create_dataset("Target", "tag1", ["Alice"])
        for i in range(5):
            _create_dataset(f"Candidate {i}", "tag1", ["Alice"])
        db.session.commit()

        svc = RecommendationService()
        related = svc.get_related_datasets(target, limit=2)
        assert len(related) == 2

    def test_tag_ranking(self, test_client):
        """Verify datasets with more tag overlaps rank higher."""
        target = _create_dataset("Target", "tagA,tagB,tagC", [])
        d1 = _create_dataset("One Tag", "tagA", [])
        d2 = _create_dataset("Two Tags", "tagB,tagC", [])
        db.session.commit()

        svc = RecommendationService()
        related = svc.get_related_datasets(target, limit=10)

        related_ids = [d.id for d in related if d.id in [d1.id, d2.id]]
        assert len(related_ids) == 2
        assert related_ids[0] == d2.id

    def test_download_ranking(self, test_client):
        """Verify datasets with more downloads rank higher."""
        target = _create_dataset("Target", "tag1", ["Author1"])
        d1 = _create_dataset("Few Downloads", "tag1", [])
        d2 = _create_dataset("Many Downloads", "tag1", [])
        db.session.commit()

        for i in range(5):
            db.session.add(DSDownloadRecord(dataset_id=d2.id, download_cookie=f"c{i}"))
        db.session.commit()

        svc = RecommendationService()
        related = svc.get_related_datasets(target, limit=10)

        related_test = [d for d in related if d.id in [d1.id, d2.id]]
        assert len(related_test) == 2
        assert related_test[0].id == d2.id


class TestRecommendationModel:
    """Tests for Recommendation model."""

    def test_model_creation(self, test_client):
        """Verify model can be created and has correct repr."""
        rec = Recommendation()
        assert isinstance(rec, Recommendation)
        assert str(rec) == "Recommendation<None>"

        db.session.add(rec)
        db.session.commit()

        assert rec.id is not None
        assert str(rec) == f"Recommendation<{rec.id}>"


class TestRecommendationForm:
    """Tests for RecommendationForm."""

    def test_form_creation(self, test_client):
        """Verify form can be instantiated."""
        form = RecommendationForm()
        assert form is not None
        assert hasattr(form, "submit")


class TestRecommendationRepository:
    """Tests for RecommendationRepository."""

    def test_initialization(self, test_client):
        """Verify repository initializes with correct model and session."""
        repo = RecommendationRepository()
        assert hasattr(repo, "model")
        assert hasattr(repo, "session")
        assert repo.session is not None
