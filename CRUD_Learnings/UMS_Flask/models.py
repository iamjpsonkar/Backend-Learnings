from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(30))
    age = db.Column(db.Float)
    
    def __repr__(self):
        return f"User({self.name}, {self.age})"
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'age': self.age
        }