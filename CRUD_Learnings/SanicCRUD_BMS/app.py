from sanic import Sanic
from sanic.response import json, html
from sanic.views import HTTPMethodView

from sqlalchemy import create_engine, Column, Integer, String, delete
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///BMS.db')
Base = declarative_base()
Base.metadata.bind = engine

DBsession = sessionmaker(bind=engine)
session = DBsession()

class Books(Base):
    __tablename__ = 'Books'

    book_id = Column(Integer, primary_key=True)
    title = Column(String(20))
    author = Column(String(20))
    published_date = Column(String(20))
    
    def to_dict(self):
        return {
        "book_id": self.book_id,
        "title": self.title,
        "author": self.author,
        "published_date": self.published_date
    }

Base.metadata.create_all(engine)

app = Sanic(__name__)

class Home(HTTPMethodView):
    async def get(self, request):
        html_content = """
            <html>
                <head>
                    <title>Book Management System</title>
                </head>
                <body>
                    <h1>Welcome to Book Management System</h1>
                    <a href="/books/"> Get All Books </a>
                </body>
            </html>
        """
        return html(html_content)


class BookManagementSystem(HTTPMethodView):
    async def get(self, request,*args, **kwargs):
        book_id = kwargs.get("book_id")
        if book_id:
            res = session.query(Books).filter(Books.book_id==book_id).first()
            if res:
                return json(res.to_dict())
            else:
                return json({"status":400, "message":"book not found"})
        else:
            return json([data.to_dict() for data in session.query(Books).all()])

    async def post(self, request,*args, **kwargs):
        book = request.json
        if book:
            res = session.query(Books).filter(Books.book_id==book.get('book_id')).first()
            if not res:
                session.add(Books(**book))
                session.commit()
                return json({"status":200, "message":"book added successfully"})
            else:
                return json({"status":500, "message":"book already exist"})
        else:
            return json({"status":400, "message":"Invalid book"})

    async def put(self, request,*args, **kwargs):
        book_id = int(kwargs.get("book_id",None))
        book = request.json
        if book_id and book and book.get("book_id")==book_id:
            res = session.query(Books).filter(Books.book_id==book_id).first()
            if res:
                res.title = book.get("title",res.title)
                res.author = book.get("author",res.author)
                res.published_date = book.get("published_date",res.published_date)
                session.commit()
                return json({"status":200, "message":"book updated successfully!"})
            else:
                return json({"status":400, "message":"book not found!"})
        else:
            return json({"status":500, "message":"Invalid Data!"})

    async def delete(self, request,*args, **kwargs):
        book_id = kwargs.get("book_id")
        res = session.query(Books).filter(Books.book_id==book_id).first()
        if res:
                session.delete(res)
                session.commit()
                return json({"status":200, "message":"book deleted successfully!"})
        else:
            return json({"status":400, "message":"book not found!"})


app.add_route(Home.as_view(),"/",methods=["GET"], name="home_view")

book_view = BookManagementSystem.as_view()

app.add_route(book_view, "/books/<book_id>/", methods=[ "GET", "PUT", "DELETE"], name="book_d")
app.add_route(book_view, "/books", methods=["GET", "POST"], name="book_view")

if __name__ == '__main__':
    app.run(debug=True, auto_reload=True)