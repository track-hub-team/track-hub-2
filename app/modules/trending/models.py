from app import db


class Trending(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    def __repr__(self):
        return f'Trending<{self.id}>'
