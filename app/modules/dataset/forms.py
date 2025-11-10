from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import URL, DataRequired, Optional

from app.modules.dataset.models import PublicationType


class AuthorForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    affiliation = StringField("Affiliation")
    orcid = StringField("ORCID")

    class Meta:
        csrf = False

    def get_author(self):
        return {
            "name": self.name.data,
            "affiliation": self.affiliation.data,
            "orcid": self.orcid.data,
        }


# ✅ NUEVO: Formulario base para feature models
class BaseFeatureModelForm(FlaskForm):
    """Formulario base común para todos los tipos de archivos."""

    filename = StringField("Filename", validators=[DataRequired()])
    title = StringField("Title", validators=[Optional()])
    desc = TextAreaField("Description", validators=[Optional()])
    publication_type = SelectField(
        "Publication type",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in PublicationType],
        validators=[Optional()],
    )
    publication_doi = StringField("Publication DOI", validators=[Optional(), URL()])
    tags = StringField("Tags (separated by commas)", validators=[Optional()])

    class Meta:
        csrf = False

    def get_fmmetadata(self):
        return {
            "filename": self.filename.data,
            "title": self.title.data,
            "description": self.desc.data,
            "publication_type": self.publication_type.data,
            "publication_doi": self.publication_doi.data,
            "tags": self.tags.data,
        }

    def get_authors(self):
        return []  # Override en subclases si es necesario


# ✅ NUEVO: Formulario específico para UVL
class UVLFeatureModelForm(BaseFeatureModelForm):
    """Formulario específico para archivos UVL."""

    file_version = StringField("UVL Version", validators=[Optional()], default="1.0")

    class Meta:
        csrf = False

    def get_fmmetadata(self):
        data = super().get_fmmetadata()
        data["file_version"] = self.file_version.data or "1.0"
        return data


# ✅ NUEVO: Formulario específico para GPX
class GPXFeatureModelForm(BaseFeatureModelForm):
    """Formulario específico para archivos GPX."""

    file_version = StringField("GPX Version", validators=[Optional()], default="1.1")
    gpx_type = SelectField(
        "Track Type",
        choices=[
            ("run", "Running"),
            ("bike", "Cycling"),
            ("hike", "Hiking"),
            ("walk", "Walking"),
            ("other", "Other"),
        ],
        validators=[Optional()],
        default="other",
    )

    class Meta:
        csrf = False

    def get_fmmetadata(self):
        data = super().get_fmmetadata()
        data["file_version"] = self.file_version.data or "1.1"
        # Añadimos el tipo de track en las tags si no está vacío
        if self.gpx_type.data and self.gpx_type.data != "other":
            existing_tags = data.get("tags", "")
            if existing_tags:
                data["tags"] = f"{existing_tags}, {self.gpx_type.data}"
            else:
                data["tags"] = self.gpx_type.data
        return data


# ⚠️ DEPRECADO: Mantener por compatibilidad temporal
class FeatureModelForm(BaseFeatureModelForm):
    """Formulario genérico (deprecado, usar específicos)."""

    file_version = StringField("File Version", validators=[Optional()])

    class Meta:
        csrf = False


class DataSetForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    desc = TextAreaField("Description", validators=[DataRequired()])
    publication_type = SelectField(
        "Publication type",
        choices=[(pt.value, pt.name.replace("_", " ").title()) for pt in PublicationType],
        validators=[DataRequired()],
    )
    publication_doi = StringField("Publication DOI", validators=[Optional(), URL()])
    dataset_doi = StringField("Dataset DOI", validators=[Optional(), URL()])
    tags = StringField("Tags (separated by commas)", validators=[Optional()])

    # Mantener feature_models genérico para compatibilidad
    feature_models = FieldList(FormField(FeatureModelForm), min_entries=0)

    authors = FieldList(
        FormField(AuthorForm),
        min_entries=1,
        validators=[DataRequired()],
    )

    submit = SubmitField("Upload dataset")

    def get_dsmetadata(self):
        return {
            "title": self.title.data,
            "description": self.desc.data,
            "publication_type": self.publication_type.data,
            "publication_doi": self.publication_doi.data,
            "dataset_doi": self.dataset_doi.data,
            "tags": self.tags.data,
        }

    def get_authors(self):
        return [author_form.get_author() for author_form in self.authors]
