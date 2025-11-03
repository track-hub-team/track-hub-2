from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SelectField
from wtforms.validators import DataRequired, Optional, Length
from wtforms import StringField, SelectField, TextAreaField
from flask_wtf.file import FileField, FileRequired, FileAllowed

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
    
class GPXUploadForm(FlaskForm):
    """Form for uploading GPX files"""
    
    gpx_file = FileField(
        'GPX File',
        validators=[
            FileRequired(),
            FileAllowed(['gpx'], 'Only GPX files are allowed!')
        ]
    )
    
    name = StringField(
        'Track Name',
        validators=[DataRequired()],
        render_kw={"placeholder": "e.g., Summit Hike to Piz Buin"}
    )
    
    difficulty = SelectField(
        'Difficulty',
        choices=[
            ('', 'Select difficulty'),
            ('T1', 'T1 - Hiking'),
            ('T2', 'T2 - Mountain hiking'),
            ('T3', 'T3 - Demanding mountain hiking'),
            ('T4', 'T4 - Alpine hiking'),
            ('T5', 'T5 - Demanding alpine hiking'),
            ('T6', 'T6 - Difficult alpine hiking')
        ],
        validators=[Optional()]
    )
    
    description = TextAreaField(
        'Description',
        validators=[Optional()],
        render_kw={"placeholder": "Describe your hiking track..."}
    )


class GPXEditForm(FlaskForm):
    """Form for editing GPX metadata"""
    name = StringField('Track Name', validators=[
        DataRequired(message="Track name is required"),
        Length(min=3, max=255, message="Name must be between 3 and 255 characters")
    ])
    
    difficulty = SelectField('Difficulty', choices=[
        ('', 'Not specified'),
        ('T1', 'T1 - Hiking'),
        ('T2', 'T2 - Mountain hiking'),
        ('T3', 'T3 - Demanding mountain hiking'),
        ('T4', 'T4 - Alpine hiking'),
        ('T5', 'T5 - Demanding alpine hiking'),
        ('T6', 'T6 - Difficult alpine hiking'),
    ], validators=[Optional()])
    
    changelog = TextAreaField('Changelog', validators=[
        DataRequired(message="Please describe what you changed"),
        Length(min=5, max=500, message="Changelog must be between 5 and 500 characters")
    ])