from datetime import datetime
from sqlalchemy import Enum as SQLAlchemyEnum
from enum import Enum

from app import db
from app.modules.dataset.models import BaseDataset


class GPXDifficultyRating(Enum):
    """SAC Hiking Scale difficulty ratings"""
    T1 = "T1"
    T2 = "T2"
    T3 = "T3"
    T4 = "T4"
    T5 = "T5"
    T6 = "T6"


class GPXMetaData(db.Model):
    """Metadata specific to GPX hiking datasets"""
    __tablename__ = 'gpx_meta_data'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic info
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # hikr.org data
    hikr_id = db.Column(db.String(50), unique=True)
    hikr_user = db.Column(db.String(100))
    hikr_url = db.Column(db.String(500))
    
    # Distance (meters)
    length_2d = db.Column(db.Float)
    length_3d = db.Column(db.Float)
    
    # Elevation (meters)
    max_elevation = db.Column(db.Float)
    min_elevation = db.Column(db.Float)
    uphill = db.Column(db.Float)
    downhill = db.Column(db.Float)
    
    # Time
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    moving_time = db.Column(db.Float)  # seconds
    
    # Speed
    max_speed = db.Column(db.Float)  # m/s
    
    # Difficulty
    difficulty = db.Column(SQLAlchemyEnum(GPXDifficultyRating))
    
    # Bounding box
    bounds_min_lat = db.Column(db.Float)
    bounds_max_lat = db.Column(db.Float)
    bounds_min_lon = db.Column(db.Float)
    bounds_max_lon = db.Column(db.Float)
    
    # GPX file content
    gpx_content = db.Column(db.Text)
    
    # Common fields
    tags = db.Column(db.String(200))
    publication_doi = db.Column(db.String(120))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    authors = db.relationship('Author', backref='gpx_meta_data', lazy=True,
                            foreign_keys='Author.gpx_meta_data_id', cascade='all, delete')
    
    def get_duration_hours(self):
        if self.moving_time:
            return round(self.moving_time / 3600, 2)
        return None
    
    def get_distance_km(self):
        if self.length_3d:
            return round(self.length_3d / 1000, 2)
        return None
    
    def __repr__(self):
        return f'GPXMetaData<{self.name}>'


class GPXDataset(BaseDataset):
    """GPX hiking dataset implementation"""
    __tablename__ = 'gpx_dataset'
    
    id = db.Column(db.Integer, db.ForeignKey('base_dataset.id'), primary_key=True)
    gpx_meta_data_id = db.Column(db.Integer, db.ForeignKey('gpx_meta_data.id'), nullable=False)
    
    gpx_meta_data = db.relationship('GPXMetaData', backref=db.backref('gpx_dataset', uselist=False))
    
    __mapper_args__ = {
        'polymorphic_identity': 'gpx',
    }
    
    def __repr__(self):
        return f'<GPXDataset {self.id}>'
    
    # Implement abstract methods
    def get_type_name(self) -> str:
        return "GPX Hiking Track"
    
    def get_metadata(self):
        return self.gpx_meta_data
    
    def get_files_count(self) -> int:
        return 1 if self.gpx_meta_data.gpx_content else 0
    
    def get_file_total_size(self) -> int:
        if self.gpx_meta_data.gpx_content:
            return len(self.gpx_meta_data.gpx_content.encode('utf-8'))
        return 0
    
    def to_dict(self) -> dict:
        metadata = self.gpx_meta_data
        return {
            'id': self.id,
            'type': 'gpx',
            'name': metadata.name,
            'description': metadata.description,
            'distance_km': metadata.get_distance_km(),
            'max_elevation_m': metadata.max_elevation,
            'uphill_m': metadata.uphill,
            'duration_hours': metadata.get_duration_hours(),
            'difficulty': metadata.difficulty.value if metadata.difficulty else None,
            'hikr_url': metadata.hikr_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }