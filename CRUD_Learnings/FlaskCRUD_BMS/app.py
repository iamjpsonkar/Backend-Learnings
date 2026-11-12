from flask import Flask, jsonify, request
from flask.views import MethodView
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# SQLite database configuration for demonstration purposes
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///mydatabase.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

"""
Book Model: Each book should have the following attributes:

book_id (Unique book_identifier)
title (Title of the book)
author (Author of the book)
published_date
"""

class BOOK(db.Model):
    book_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String)
    author = db.Column(db.String)
    published_date = db.Column(db.String)

    def __repr__(self):
        return f"""<BOOK {
            "book_id": {self.book_id},
            "title": {self.title},
            "author": {self.author},
            "published_date": {self.published_date},
        } >"""
        
    def to_dict(self):
        return {
        'book_id': self.book_id,
        'title': self.title,
        'author': self.author,
        'published_date': self.published_date
    }

# Creates the database and tables
with app.app_context():
    db.create_all()

class Home(MethodView):
    def get(self):
        return """
        <html>
            <head>
                <title>Book Management System</title>
            </head>
            <body>
                <h1>Welcome to Book Management System!</h1>
                <a href="/books/">List of Books</a>
            </body>
        </html>
        """


class BookManagementSystem(MethodView):
    def get(self, book_id=None):
        if book_id:
            res = BOOK.query.filter(BOOK.book_id==book_id).first()
            if res:
                return jsonify(res.to_dict())
            else:
                return jsonify({"status": 400, "message": "Book not found"})
        else:
            res = BOOK.query.all()
            return jsonify([book.to_dict() for book in res])

    def post(self):
        book = request.json
        if book:
            res = BOOK.query.filter(BOOK.book_id==book.get('book_id')).first()
            if res:
                return jsonify({"status": 500, "message": "Book book_id already exist"})
            else:
                new_book = BOOK(
                    book_id = book.get('book_id'),
                    title = book.get('title'),
                    author = book.get('author'),
                    published_date = book.get('published_date')
                )
                db.session.add(new_book)
                db.session.commit()
                return jsonify({"status": 200, "message": "Book added in db"})
        else:
            return jsonify({"status": 400, "message": "missing book details"})

    def put(self, book_id=None):
        book = request.json
        res = BOOK.query.filter(BOOK.book_id==book_id).first()
        if res and book:
            res.title = book.get('title',res.title)
            res.author = book.get('author',res.author)
            res.published_date = book.get('published_date',res.published_date)
            db.session.commit()
            return jsonify({"status": 200, "message": "Book update in DB"})
        else:
            return jsonify({"status": 400, "message": "missing book details/not found"})

    def delete(self, book_id=None):
        res = BOOK.query.filter(BOOK.book_id==book_id).first()
        if res:
            db.session.delete(res)
            db.session.commit()
            return jsonify({"status": 200, "message": "Book deleted from DB"})
        else:
            return jsonify({"status": 400, "message": "missing book missing"})


home_view = Home.as_view("home")
book_view = BookManagementSystem.as_view("book_api")


app.add_url_rule("/", view_func=home_view, methods=["GET"])
app.add_url_rule("/books/<int:book_id>/", view_func=book_view, methods=["GET"])
app.add_url_rule("/books/", view_func=book_view, methods=["GET", "POST"])
app.add_url_rule("/books/<int:book_id>/", view_func=book_view, methods=["PUT"])
app.add_url_rule("/books/<int:book_id>/", view_func=book_view, methods=["DELETE"])


if __name__ == "__main__":
    app.run(debug=True)
