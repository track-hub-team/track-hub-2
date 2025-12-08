from flask_wtf import FlaskForm
from wtforms import SubmitField


class VersioningForm(FlaskForm):
    submit = SubmitField("Save versioning")
