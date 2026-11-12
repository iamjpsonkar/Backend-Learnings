# controllers.py
from flask import request, jsonify
from flask.views import MethodView
from models import Book, db

class BookDB():
    def __init__(self):
        pass

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

    def read(self, book_id):
        try:
            book_data = Book.query.get_or_404(book_id)
            return self.bookSuccess("Book Fetched", book_data.to_dict())
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

    def delete(self, book_id):
        try:
            deleted_book = Book.query.get_or_404(book_id)
            db.session.delete(deleted_book)
            db.session.commit()
            return self.bookSuccess("Book Deleted", deleted_book.to_dict())
        except Exception as err:
            return self.bookError(str(err), book_id)

class BookView(MethodView):
    def __init__(self):
        self.books = BookDB()

    def post(self, book_id):
        book_data = request.json
        return jsonify(self.books.create(book_id=book_id, book_data=book_data))

    def get(self, book_id):
        return jsonify(self.books.read(book_id))

    def put(self, book_id):
        updated_book_data = request.json
        return jsonify(self.books.update(book_id=book_id, updated_book_data=updated_book_data))

    def patch(self, book_id):
        updated_book_data = request.json
        return jsonify(self.books.update(book_id=book_id, updated_book_data=updated_book_data))

    def delete(self, book_id):
        print("delete for ", book_id)
        return jsonify(self.books.delete(book_id))
