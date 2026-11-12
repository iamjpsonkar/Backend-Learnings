# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bookName = db.Column(db.String(20), unique=True, nullable=False)
    authorName = db.Column(db.String(120), unique=True, nullable=False)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    extra_data = db.Column(db.JSON)

    def __repr__(self):
        return f"Book('{self.bookName}', '{self.authorName}')"

    def to_dict(self):
        return {
            'id': self.id,
            'bookName': self.bookName,
            'authorName': self.authorName,
            'createdAt': self.createdAt.isoformat() if self.createdAt else None,
            'extra_data': self.extra_data
        }
