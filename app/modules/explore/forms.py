from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import Optional


class ExploreForm(FlaskForm):
    """Formulario de búsqueda y filtros."""

    # Búsqueda general
    query = StringField("Search", validators=[Optional()])

    # Filtro por tipo de dataset
    dataset_type = SelectField(
        "Dataset Type",
        choices=[("all", "All types"), ("uvl", "UVL Feature Models"), ("gpx", "GPS Tracks")],
        default="all",
        validators=[Optional()],
    )

    # Ordenamiento
    sorting = SelectField(
        "Sort by",
        choices=[
            ("newest", "Newest first"),
            ("oldest", "Oldest first"),
            ("downloads", "Most downloaded"),
            ("title", "Title A-Z"),
        ],
        default="newest",
        validators=[Optional()],
    )

    # Tipo de publicación
    publication_type = SelectField(
        "Publication Type",
        choices=[
            ("any", "Any"),
            ("none", "None"),
            ("conference_paper", "Conference Paper"),
            ("journal_article", "Journal Article"),
            ("technical_note", "Technical Note"),
            ("other", "Other"),
        ],
        default="any",
        validators=[Optional()],
    )

    # Filtros específicos para GPX
    min_distance = IntegerField("Min Distance (km)", validators=[Optional()])
    max_distance = IntegerField("Max Distance (km)", validators=[Optional()])

    activity_type = SelectField(
        "Activity Type",
        choices=[
            ("any", "Any"),
            ("run", "Running"),
            ("bike", "Cycling"),
            ("hike", "Hiking"),
            ("walk", "Walking"),
            ("other", "Other"),
        ],
        default="any",
        validators=[Optional()],
    )

    tags = StringField("Tags", validators=[Optional()])

    submit = SubmitField("Search")
