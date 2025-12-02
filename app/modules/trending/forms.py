from flask_wtf import FlaskForm
from wtforms import SubmitField


class TrendingForm(FlaskForm):
    submit = SubmitField('Save trending')
