from flask import Flask, request, jsonify
from flask.views import MethodView
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
db = SQLAlchemy(app)

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

class BookDB():
    def __init__(self):
        self.books = {}

    def bookError(self, error, book_id=None):
        return {
            "book_id": book_id,
            "Error": error
        }
    
    def bookSuccess(self, message, book_data):
        return {
            "data": book_data,
            "message": message
        }
    
    def create(self, book_id, book_data):
        try:
            new_book = Book(id=book_id, bookName=book_data['bookname'], authorName=book_data['authorname'])
            db.session.add(new_book)
            db.session.commit()
            return self.bookSuccess("Book Created", new_book.to_dict())
        except Exception as err:
            return self.bookError(str(err), book_id)

    def read(self,book_id):
        try:
            book_data = Book.query.get_or_404(book_id)
            return self.bookSuccess("Book Fetched",book_data.to_dict())
        except Exception as err:
            return self.bookError(str(err), book_id)
    
    def update(self, book_id, updated_book_data):
        try:
            book_data = Book.query.get_or_404(book_id)
            book_data.bookName = updated_book_data.get("bookname", book_data.bookName)
            book_data.authorName = updated_book_data.get("authorname", book_data.authorName)
            book_data.extra_data = updated_book_data.get("extra_data", book_data.extra_data)
            db.session.commit()
            return self.bookSuccess("Book Updated", book_data.to_dict())
        except Exception as err:
            return self.bookError(str(err), book_id)
    
    def delete(self,book_id):
        try:
            deleted_book = Book.query.get_or_404(book_id)
            print(deleted_book.to_dict())
            db.session.delete(deleted_book)
            db.session.commit()
            return self.bookSuccess("Book Deleted",deleted_book.to_dict())
        except Exception as err:
            return self.bookError(str(err), book_id)

class BookView(MethodView):
    def post(self,book_id):
        book_data = request.json
        return jsonify(books.create(book_id=book_id,book_data=book_data))

    def get(self,book_id):
        return jsonify(books.read(book_id))
    
    def put(self,book_id):
        updated_book_data = request.json
        return jsonify(books.update(book_id=book_id,updated_book_data=updated_book_data))

    def patch(self,book_id):
        updated_book_data = request.json
        return jsonify(books.update(book_id=book_id,updated_book_data=updated_book_data))

    def delete(self,book_id):
        print("delete for ", book_id)
        return jsonify(books.delete(book_id))
    

app.add_url_rule("/<int:book_id>",view_func=BookView.as_view("Home"),methods=["GET","POST","PUT","PATCH","DELETE"])


if __name__ == '__main__':

    with app.app_context():
        db.create_all()
    
    books = BookDB()

    app.run(debug=True)