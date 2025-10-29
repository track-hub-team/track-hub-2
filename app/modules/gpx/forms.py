from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SelectField
from wtforms.validators import DataRequired, Optional

from app.modules.gpx.models import GPXDifficultyRating


class GPXDatasetForm(FlaskForm):
    """Form for GPX datasets"""
    
    name = StringField('Trail Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    
    hikr_user = StringField('Hikr.org User', validators=[Optional()])
    hikr_url = StringField('Hikr.org URL', validators=[Optional()])
    
    length_3d = FloatField('Distance (m)', validators=[Optional()])
    max_elevation = FloatField('Max Elevation (m)', validators=[Optional()])
    uphill = FloatField('Elevation Gain (m)', validators=[Optional()])
    
    difficulty = SelectField(
        'Difficulty (SAC Scale)',
        choices=[('', 'Not specified')] + [(r.value, r.value) for r in GPXDifficultyRating],
        validators=[Optional()]
    )
    
    tags = StringField('Tags', validators=[Optional()])
    
    def get_metadata(self):
        return {
            'name': self.name.data,
            'description': self.description.data,
            'hikr_user': self.hikr_user.data,
            'hikr_url': self.hikr_url.data,
            'length_3d': self.length_3d.data,
            'max_elevation': self.max_elevation.data,
            'uphill': self.uphill.data,
            'difficulty': self.difficulty.data if self.difficulty.data else None,
            'tags': self.tags.data,
        }