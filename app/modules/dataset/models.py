import xml.etree.ElementTree as ET
from datetime import datetime
from enum import Enum

from flask import request
from sqlalchemy import Enum as SQLAlchemyEnum

from app import db


# ---------------------------
# Catálogo de tipos de publicación
# ---------------------------
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


# ---------------------------
# Entidades auxiliares (comunes)
# ---------------------------
class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    affiliation = db.Column(db.String(120))
    orcid = db.Column(db.String(120))
    ds_meta_data_id = db.Column(db.Integer, db.ForeignKey("ds_meta_data.id"))
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
    # Guardamos como Enum real. En formularios conviene enviar .value ("none", "article", ...)
    publication_type = db.Column(SQLAlchemyEnum(PublicationType), nullable=False)
    publication_doi = db.Column(db.String(120))
    dataset_doi = db.Column(db.String(120))
    tags = db.Column(db.String(120))
    ds_metrics_id = db.Column(db.Integer, db.ForeignKey("ds_metrics.id"))
    ds_metrics = db.relationship("DSMetrics", uselist=False, backref="ds_meta_data", cascade="all, delete")
    authors = db.relationship("Author", backref="ds_meta_data", lazy=True, cascade="all, delete")


# ==========================================================
#   BASE POLIMÓRFICA (single-table inheritance)
# ==========================================================
class BaseDataset(db.Model):
    """
    Base polimórfica para todos los tipos de dataset (UVL, GPX, Image, Tabular, ...).
    Compartimos una sola tabla 'data_set' para compatibilidad con la plataforma.
    """

    __tablename__ = "data_set"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    ds_meta_data_id = db.Column(db.Integer, db.ForeignKey("ds_meta_data.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Discriminador de tipo; el server_default evita '' en inserts directos (problema del KeyError en mapper)
    dataset_kind = db.Column(
        db.String(32),
        nullable=False,
        default="uvl",
        server_default="uvl",
        index=True,
    )

    __mapper_args__ = {
        "polymorphic_on": dataset_kind,
    }
    versions = db.relationship(
        "DatasetVersion",
        back_populates="dataset",
        lazy="dynamic",
        cascade="all, delete-orphan",
        order_by="DatasetVersion.created_at.desc()",
    )
    user = db.relationship("User", foreign_keys=[user_id])
    ds_meta_data = db.relationship("DSMetaData", backref=db.backref("data_set", uselist=False))
    feature_models = db.relationship("FeatureModel", backref="data_set", lazy=True, cascade="all, delete")

    # ---------------------------
    # Métodos COMUNES (usados por plantillas y APIs)
    # ---------------------------
    def name(self) -> str:
        return self.ds_meta_data.title

    def files(self):
        return [file for fm in self.feature_models for file in fm.files]

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def _normalize_publication_type(self):
        """
        Devuelve un PublicationType o None, acepte lo que haya en ds_meta_data.publication_type.
        Puede venir como Enum, str (value o name), o None.
        """
        pt = getattr(self.ds_meta_data, "publication_type", None)
        if pt is None:
            return None
        if isinstance(pt, PublicationType):
            return pt
        # Si llega como string, intentamos casar primero por value, luego por name
        s = str(pt).strip()
        for enum_member in PublicationType:
            if enum_member.value == s:
                return enum_member
        for enum_member in PublicationType:
            if enum_member.name == s:
                return enum_member
        return None

    def get_cleaned_publication_type(self) -> str:
        pt = self._normalize_publication_type()
        if not pt:
            return "None"
        # Mostrar bonito
        return pt.name.replace("_", " ").title()

    def get_files_count(self) -> int:
        return sum(len(fm.files) for fm in self.feature_models)

    def get_file_total_size(self) -> int:
        return sum((file.size or 0) for fm in self.feature_models for file in fm.files)

    def get_file_total_size_for_human(self) -> str:
        # Uso local para evitar import circular
        size = self.get_file_total_size()
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024**2:
            return f"{round(size / 1024, 2)} KB"
        elif size < 1024**3:
            return f"{round(size / (1024 ** 2), 2)} MB"
        return f"{round(size / (1024 ** 3), 2)} GB"

    def get_zenodo_url(self):
        return f"https://zenodo.org/record/{self.ds_meta_data.deposition_id}" if self.ds_meta_data.dataset_doi else None

    def get_uvlhub_doi(self):
        # evitamos import circular; el servicio construye la URL pública
        from app.modules.dataset.services import DataSetService

        return DataSetService().get_uvlhub_doi(self)

    def to_dict(self):
        return {
            "title": self.ds_meta_data.title,
            "id": self.id,
            "created_at": self.created_at,
            "created_at_timestamp": int(self.created_at.timestamp()),
            "description": self.ds_meta_data.description,
            "authors": [author.to_dict() for author in self.ds_meta_data.authors],
            "publication_type": self.get_cleaned_publication_type(),
            "publication_doi": self.ds_meta_data.publication_doi,
            "dataset_doi": self.ds_meta_data.dataset_doi,
            "tags": self.ds_meta_data.tags.split(",") if self.ds_meta_data.tags else [],
            "url": self.get_uvlhub_doi(),
            "download": f'{request.host_url.rstrip("/")}/dataset/download/{self.id}',
            "zenodo": self.get_zenodo_url(),
            "files": [file.to_dict() for fm in self.feature_models for file in fm.files],
            "files_count": self.get_files_count(),
            "total_size_in_bytes": self.get_file_total_size(),
            "total_size_in_human_format": self.get_file_total_size_for_human(),
            "dataset_kind": self.dataset_kind,
            "specific_template": self.specific_template(),  # para vistas modulares
        }

    def get_latest_version(self):
        """Obtener la última versión del dataset"""
        return self.versions.first()

    def get_version_count(self):
        """Contar número de versiones"""
        return self.versions.count()

    # ---------------------------
    # HOOKS por tipo (cada subclase sobreescribe)
    # ---------------------------
    @classmethod
    def kind(cls) -> str:
        """Identificador de tipo (coincide con polymorphic_identity)."""
        return "base"

    def validate_upload(self, file_path: str) -> bool:
        """
        Validación de ficheros asociada al TIPO de dataset.
        Base: no valida nada. Subclases implementan su lógica.
        """
        return True

    def versioning_rules(self) -> dict:
        """
        Reglas de versionado para este tipo.
        Ejem: {"bump_on_new_file": True, "semantic": True}
        """
        return {}

    def specific_template(self) -> str | None:
        """
        Nombre de plantilla parcial específica para el detalle/explorer,
        por ejemplo: "dataset/blocks/gpx_preview.html".
        """
        return None

    def __repr__(self):
        return f"Dataset<{self.id}:{self.dataset_kind}>"


# ---------------------------
# Subclases concretas (single-table)
# ---------------------------


class UVLDataset(BaseDataset):
    __mapper_args__ = {"polymorphic_identity": "uvl"}

    @classmethod
    def kind(cls) -> str:
        return "uvl"

    def validate_upload(self, file_path: str) -> bool:
        # Aquí podrías validar sintaxis UVL, etc.
        # En el servicio ya haces validación por extensión, esto lo deja listo para mover ahí la lógica si quieres.
        return file_path.lower().endswith(".uvl")

    def specific_template(self) -> str | None:
        # Plantilla parcial específica (si la tienes)
        return "dataset/blocks/uvl_tree.html"

    def calculate_total_features(self):
        """Calcular total de features en todos los modelos UVL"""
        # TODO: Implementar según lógica UVL existente
        return 0

    def calculate_total_constraints(self):
        """Calcular total de constraints en todos los modelos UVL"""
        # TODO: Implementar según lógica UVL existente
        return 0


class GPXDataset(BaseDataset):
    __mapper_args__ = {"polymorphic_identity": "gpx"}

    @classmethod
    def kind(cls) -> str:
        return "gpx"

    def validate_upload(self, file_path: str) -> bool:
        # Validación real mínima: XML válido y raíz <gpx>
        if not file_path.lower().endswith(".gpx"):
            return False
        try:
            with open(file_path, "rb") as f:
                tree = ET.parse(f)
            root = tree.getroot()
            return root.tag.lower().endswith("gpx")
        except Exception:
            return False

    def calculate_total_distance(self):
        """Calcular distancia total de todos los tracks"""
        from app.modules.dataset.handlers.gpx_handler import GPXHandler

        handler = GPXHandler()
        total = 0

        for fm in self.feature_models:
            for file in fm.files:
                if file.name.lower().endswith(".gpx"):
                    file_path = file.get_path()
                    data = handler.parse_gpx(file_path)
                    if data:
                        total += data.get("distance", 0)
        return total

    def calculate_total_elevation_gain(self):
        """Calcular desnivel positivo total"""
        from app.modules.dataset.handlers.gpx_handler import GPXHandler

        handler = GPXHandler()
        total = 0

        for fm in self.feature_models:
            for file in fm.files:
                if file.name.lower().endswith(".gpx"):
                    file_path = file.get_path()
                    data = handler.parse_gpx(file_path)
                    if data:
                        total += data.get("elevation_gain", 0)
        return total

    def calculate_total_elevation_loss(self):
        """Calcular desnivel negativo total"""
        from app.modules.dataset.handlers.gpx_handler import GPXHandler

        handler = GPXHandler()
        total = 0

        for fm in self.feature_models:
            for file in fm.files:
                if file.name.lower().endswith(".gpx"):
                    file_path = file.get_path()
                    data = handler.parse_gpx(file_path)
                    if data:
                        total += data.get("elevation_loss", 0)
        return total

    def count_total_points(self):
        """Contar total de puntos GPS"""
        from app.modules.dataset.handlers.gpx_handler import GPXHandler

        handler = GPXHandler()
        total = 0

        for fm in self.feature_models:
            for file in fm.files:
                if file.name.lower().endswith(".gpx"):
                    file_path = file.get_path()
                    data = handler.parse_gpx(file_path)
                    if data:
                        total += data.get("points_count", 0)
        return total

    def count_tracks(self):
        """Contar número de tracks GPX"""
        count = 0
        for fm in self.feature_models:
            for file in fm.files:
                if file.name.lower().endswith(".gpx"):
                    count += 1
        return count


# ---------------------------
# Métricas/Registros/DOI mapping
# ---------------------------
class DSDownloadRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"))
    download_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    download_cookie = db.Column(db.String(36), nullable=False)  # UUID4

    def __repr__(self):
        return (
            f"<Download id={self.id} dataset_id={self.dataset_id} "
            f"date={self.download_date} cookie={self.download_cookie}>"
        )


class DSViewRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    dataset_id = db.Column(db.Integer, db.ForeignKey("data_set.id"))
    view_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    view_cookie = db.Column(db.String(36), nullable=False)  # UUID4

    def __repr__(self):
        return f"<View id={self.id} dataset_id={self.dataset_id} date={self.view_date} cookie={self.view_cookie}>"


class DOIMapping(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_doi_old = db.Column(db.String(120))
    dataset_doi_new = db.Column(db.String(120))


# ---------------------------
# Registro de tipos (útil para factorías en servicios/rutas)
# ---------------------------
DATASET_KIND_TO_CLASS = {
    "base": BaseDataset,
    "uvl": UVLDataset,
    "gpx": GPXDataset,
}
