from datetime import datetime

from app import db


class DatasetVersion(db.Model):
    """Modelo genérico para versiones de cualquier tipo de dataset"""

    __tablename__ = "dataset_version"

    id = db.Column(db.Integer, primary_key=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"), nullable=False)
    version_number = db.Column(db.String(20), nullable=False)  # Formato: "1.0.0"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Snapshot de metadatos en esta versión
    title = db.Column(db.String(200))
    description = db.Column(db.Text)

    # Snapshot de archivos (JSON: {filename: {checksum, size, id}})
    files_snapshot = db.Column(db.JSON)

    # Mensaje de cambios (changelog)
    changelog = db.Column(db.Text)

    # Usuario que creó esta versión
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    # Polimorfismo para extensiones específicas
    version_type = db.Column(db.String(50))

    __mapper_args__ = {"polymorphic_identity": "base", "polymorphic_on": version_type}

    # Relaciones
    dataset = db.relationship("BaseDataset", back_populates="versions")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<DatasetVersion {self.version_number} for Dataset {self.dataset_id}>"

    def to_dict(self):
        """Serializar a diccionario"""
        return {
            "id": self.id,
            "version_number": self.version_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "changelog": self.changelog,
            "created_by": self.created_by.profile.name if self.created_by else None,
            "title": self.title,
            "description": self.description,
        }

    def compare_with(self, other_version):
        """
        Comparar esta versión con otra.
        Método base que puede ser sobrescrito por subclases.
        """
        return {
            "metadata_changes": self._compare_metadata(other_version),
            "file_changes": self._compare_files(other_version),
        }

    def _compare_metadata(self, other):
        """Comparar cambios en metadatos"""
        changes = {}
        if self.title != other.title:
            changes["title"] = {"old": other.title, "new": self.title}
        if self.description != other.description:
            changes["description"] = {"old": other.description, "new": self.description}
        return changes

    def _compare_files(self, other):
        """Comparar cambios en archivos"""
        old_files = other.files_snapshot or {}
        new_files = self.files_snapshot or {}

        old_names = set(old_files.keys())
        new_names = set(new_files.keys())

        added = list(new_names - old_names)
        removed = list(old_names - new_names)

        modified = []
        for filename in old_names & new_names:
            old_checksum = old_files[filename].get("checksum")
            new_checksum = new_files[filename].get("checksum")
            old_id = old_files[filename].get("id")
            new_id = new_files[filename].get("id")

            if old_checksum != new_checksum or old_id != new_id:
                modified.append(filename)

        return {"added": added, "removed": removed, "modified": modified}


class GPXDatasetVersion(DatasetVersion):
    """Versión extendida para datasets GPX con estadísticas específicas"""

    __tablename__ = "gpx_dataset_version"

    id = db.Column(db.Integer, db.ForeignKey("dataset_version.id"), primary_key=True)

    # Estadísticas agregadas de todos los tracks
    total_distance = db.Column(db.Float)  # Distancia total en metros
    total_elevation_gain = db.Column(db.Float)  # Desnivel positivo total
    total_elevation_loss = db.Column(db.Float)  # Desnivel negativo total
    total_points = db.Column(db.Integer)  # Total de puntos GPS
    track_count = db.Column(db.Integer)  # Número de tracks

    __mapper_args__ = {"polymorphic_identity": "gpx"}

    def compare_with(self, other_version):
        """Comparación extendida para GPX con estadísticas"""
        base_comparison = super().compare_with(other_version)

        if not isinstance(other_version, GPXDatasetVersion):
            return base_comparison

        # Comparar estadísticas GPX
        gpx_changes = {}

        if self.total_distance != other_version.total_distance:
            diff = self.total_distance - other_version.total_distance
            gpx_changes["distance"] = {
                "old": round(other_version.total_distance / 1000, 2),
                "new": round(self.total_distance / 1000, 2),
                "diff": round(diff / 1000, 2),
                "unit": "km",
            }

        if self.total_elevation_gain != other_version.total_elevation_gain:
            diff = self.total_elevation_gain - other_version.total_elevation_gain
            gpx_changes["elevation_gain"] = {
                "old": round(other_version.total_elevation_gain, 0),
                "new": round(self.total_elevation_gain, 0),
                "diff": round(diff, 0),
                "unit": "m",
            }

        if self.track_count != other_version.track_count:
            gpx_changes["tracks"] = {
                "old": other_version.track_count,
                "new": self.track_count,
                "diff": self.track_count - other_version.track_count,
            }

        base_comparison["gpx_statistics"] = gpx_changes
        return base_comparison

    def to_dict(self):
        """Serializar incluyendo estadísticas GPX"""
        data = super().to_dict()
        data.update(
            {
                "total_distance_km": round(self.total_distance / 1000, 2) if self.total_distance else 0,
                "total_elevation_gain": round(self.total_elevation_gain, 0) if self.total_elevation_gain else 0,
                "total_elevation_loss": round(self.total_elevation_loss, 0) if self.total_elevation_loss else 0,
                "total_points": self.total_points,
                "track_count": self.track_count,
            }
        )
        return data


class UVLDatasetVersion(DatasetVersion):
    """Versión extendida para datasets UVL con métricas específicas"""

    __tablename__ = "uvl_dataset_version"

    id = db.Column(db.Integer, db.ForeignKey("dataset_version.id"), primary_key=True)

    # Métricas UVL
    total_features = db.Column(db.Integer)
    total_constraints = db.Column(db.Integer)
    model_count = db.Column(db.Integer)

    __mapper_args__ = {"polymorphic_identity": "uvl"}

    def compare_with(self, other_version):
        """Comparación extendida para UVL"""
        base_comparison = super().compare_with(other_version)

        if not isinstance(other_version, UVLDatasetVersion):
            return base_comparison

        uvl_changes = {}

        if self.total_features != other_version.total_features:
            uvl_changes["features"] = {
                "old": other_version.total_features,
                "new": self.total_features,
                "diff": self.total_features - other_version.total_features,
            }

        if self.total_constraints != other_version.total_constraints:
            uvl_changes["constraints"] = {
                "old": other_version.total_constraints,
                "new": self.total_constraints,
                "diff": self.total_constraints - other_version.total_constraints,
            }

        base_comparison["uvl_metrics"] = uvl_changes
        return base_comparison
