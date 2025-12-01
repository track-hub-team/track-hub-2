from flask_wtf import FlaskForm
from wtforms import SubmitField


class RecommendationForm(FlaskForm):
    submit = SubmitField("Save recommendation")
