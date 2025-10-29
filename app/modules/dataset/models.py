from datetime import datetime
from enum import Enum

from flask import request
from sqlalchemy import Enum as SQLAlchemyEnum

from app import db

class BaseDataset(db.Model):
    """
    Base polymorphic class for all dataset types.
    Allows UVL, GPX, Image, Tabular, etc. to coexist.
    """
    __tablename__ = 'base_dataset'
    
    id = db.Column(db.Integer, primary_key=True)
    dataset_type = db.Column(db.String(50), nullable=False)  # Discriminator: 'uvl', 'gpx', etc.
    
    # Common fields across all dataset types
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Polymorphic configuration
    __mapper_args__ = {
        'polymorphic_identity': 'base',
        'polymorphic_on': dataset_type,
        'with_polymorphic': '*'
    }
    
    # Abstract interface that all dataset types must implement
    def get_type_name(self) -> str:
        """Return human-readable name of dataset type"""
        raise NotImplementedError("Subclasses must implement get_type_name()")
    
    def get_metadata(self):
        """Return the metadata object for this dataset"""
        raise NotImplementedError("Subclasses must implement get_metadata()")
    
    def get_files_count(self) -> int:
        """Return number of files in this dataset"""
        raise NotImplementedError("Subclasses must implement get_files_count()")
    
    def get_file_total_size(self) -> int:
        """Return total size in bytes"""
        raise NotImplementedError("Subclasses must implement get_file_total_size()")
    
    def to_dict(self) -> dict:
        """Return JSON-serializable dict representation"""
        raise NotImplementedError("Subclasses must implement to_dict()")
    
    # Common methods with default implementation
    def get_file_total_size_for_human(self) -> str:
        """Convert bytes to human-readable format"""
        from app.modules.dataset.services import SizeService
        return SizeService().get_human_readable_size(self.get_file_total_size())
    
    def get_uvlhub_doi(self) -> str:
        """Get DOI for this dataset (works for all types)"""
        from app.modules.dataset.services import DataSetService
        return DataSetService().get_uvlhub_doi(self)

class PublicationType(Enum):
    NONE = "none"
    ANNOTATION_COLLECTION = "annotationcollection"
    BOOK = "book"
    BOOK_SECTION = "section"
    CONFERENCE_PAPER = "conferencepaper"
    DATA_MANAGEMENT_PLAN = "datamanagementplan"
    JOURNAL_ARTICLE = "article"
    PATENT = "patent"
    PREPRINT = "preprint"
    PROJECT_DELIVERABLE = "deliverable"
    PROJECT_MILESTONE = "milestone"
    PROPOSAL = "proposal"
    REPORT = "report"
    SOFTWARE_DOCUMENTATION = "softwaredocumentation"
    TAXONOMIC_TREATMENT = "taxonomictreatment"
    TECHNICAL_NOTE = "technicalnote"
    THESIS = "thesis"
    WORKING_PAPER = "workingpaper"
    OTHER = "other"


class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    affiliation = db.Column(db.String(120))
    orcid = db.Column(db.String(120))
    ds_meta_data_id = db.Column(db.Integer, db.ForeignKey("ds_meta_data.id"))
    gpx_meta_data_id = db.Column(db.Integer, db.ForeignKey('gpx_meta_data.id'))
    fm_meta_data_id = db.Column(db.Integer, db.ForeignKey("fm_meta_data.id"))

    def to_dict(self):
        return {"name": self.name, "affiliation": self.affiliation, "orcid": self.orcid}


class DSMetrics(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number_of_models = db.Column(db.String(120))
    number_of_features = db.Column(db.String(120))

    def __repr__(self):
        return f"DSMetrics<models={self.number_of_models}, features={self.number_of_features}>"


class DSMetaData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    deposition_id = db.Column(db.Integer)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    publication_type = db.Column(SQLAlchemyEnum(PublicationType), nullable=False)
    publication_doi = db.Column(db.String(120))
    dataset_doi = db.Column(db.String(120))
    tags = db.Column(db.String(120))
    ds_metrics_id = db.Column(db.Integer, db.ForeignKey("ds_metrics.id"))
    ds_metrics = db.relationship("DSMetrics", uselist=False, backref="ds_meta_data", cascade="all, delete")
    authors = db.relationship("Author", backref="ds_meta_data", lazy=True, cascade="all, delete")


class DataSet(BaseDataset):
    """
    UVL Feature Model dataset (formerly the only dataset type).
    Now a specialized implementation of BaseDataset.
    """
    __tablename__ = 'data_set'
    
    id = db.Column(db.Integer, db.ForeignKey('base_dataset.id'), primary_key=True)
    ds_meta_data_id = db.Column(db.Integer, db.ForeignKey('ds_meta_data.id'), nullable=False)
    
    # Relationships (keep existing)
    ds_meta_data = db.relationship('DSMetaData', backref=db.backref('data_set', uselist=False))
    feature_models = db.relationship('FeatureModel', backref='data_set', lazy=True, cascade='all, delete')
    
    # Polymorphic configuration
    __mapper_args__ = {
        'polymorphic_identity': 'uvl',
    }

    def get_cleaned_publication_type(self) -> str:
        """Return cleaned publication type for display"""
        if not self.ds_meta_data or not self.ds_meta_data.publication_type:
            return "N/A"
        
        publication_type = self.ds_meta_data.publication_type.value
        # Convertir ENUM a formato legible
        return publication_type.replace('_', ' ').title()
    
    # Implement abstract methods from BaseDataset
    def get_type_name(self) -> str:
        return "UVL Feature Model"
    
    def get_metadata(self):
        return self.ds_meta_data
    
    def get_files_count(self) -> int:
        return sum(len(fm.files) for fm in self.feature_models)
    
    def get_file_total_size(self) -> int:
        return sum(
            file.size for feature_model in self.feature_models
            for file in feature_model.files
        )
    
    def to_dict(self) -> dict:
        # ...existing implementation...
        return {
            'id': self.id,
            'type': 'uvl',
            'title': self.ds_meta_data.title,
            'description': self.ds_meta_data.description,
            'publication_type': self.ds_meta_data.publication_type.value,
            'publication_doi': self.ds_meta_data.publication_doi,
            'dataset_doi': self.ds_meta_data.dataset_doi,
            'tags': self.ds_meta_data.tags,
            'authors': [author.to_dict() for author in self.ds_meta_data.authors],
            'files_count': self.get_files_count(),
            'total_size': self.get_file_total_size_for_human(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class DSDownloadRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"))
    download_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    download_cookie = db.Column(db.String(36), nullable=False)  # Assuming UUID4 strings

    def __repr__(self):
        return (
            f"<Download id={self.id} "
            f"dataset_id={self.dataset_id} "
            f"date={self.download_date} "
            f"cookie={self.download_cookie}>"
        )


class DSViewRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"))
    view_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    view_cookie = db.Column(db.String(36), nullable=False)  # Assuming UUID4 strings

    def __repr__(self):
        return f"<View id={self.id} dataset_id={self.dataset_id} date={self.view_date} cookie={self.view_cookie}>"


class DOIMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_doi_old = db.Column(db.String(120))
    dataset_doi_new = db.Column(db.String(120))
