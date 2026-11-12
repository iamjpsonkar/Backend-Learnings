# CRUD | Create Read Update Delete | Post Get Put/Patch Delete | API Learnings

## CRUD Basic Definitions
*CRUD stands for Create, Read, Update, and Delete, which are the basic operations that can be performed on data. CRUD APIs are a set of application programming interfaces that enable developers to interact with a database or any other storage system to perform these fundamental operations. These APIs are essential for building and managing data-driven applications.*

Here's a brief overview of CRUD operations and how they relate to APIs:

- **Create (C)**:
    - **API Endpoint**: Typically uses HTTP methods like POST.
Purpose: Allows the creation of new records or entities in the database.
- **Read (R)**:
    - **API Endpoint**: Typically uses HTTP methods like GET.
    Purpose: Retrieves information from the database. It can be used to fetch a single record, a list of records, or filtered data.
- **Update (U)**:
    - **API Endpoint**: Typically uses HTTP methods like PUT or PATCH.
    Purpose: Modifies existing records in the database. PUT is often used to update an entire record, while PATCH is used for partial updates.
- **Delete (D)**:
    - **API Endpoint**: Typically uses HTTP method DELETE.
    Purpose: Removes records or entities from the database.

A simple example of how CRUD operations can be implemented using 

### **RESTful API endpoints**:

- **Create**:
```bash
POST /api/resource
```

- **Read**:
```bash
GET /api/resource
GET /api/resource/{id}
```

- **Update**:
```bash
PUT /api/resource/{id}
PATCH /api/resource/{id}
```

- **Delete**:
```bash
DELETE /api/resource/{id}
```

*Frameworks like Express (Node.js), Flask (Python), Django (Python), Spring Boot (Java), and many others provide tools and conventions for building CRUD APIs. These frameworks often use RESTful principles for designing API endpoints, making it easy to understand and work with data resources.*

**Let's create a complete Book Management System | BMS**

# Introduction to Flask

### What is Flask?
Flask is a lightweight and easy-to-extend web framework for Python. It provides the essentials for building web applications without imposing too many constraints. Its simplicity makes it an excellent choice for beginners while offering flexibility for more advanced users.

### Why Flask for Web Development?
- **Simplicity:** Flask follows the principle of simplicity, making it easy for developers to understand and use.
- **Modularity:** Flask is designed with modularity in mind, allowing you to use only the components you need.
- **Extensibility:** Extending Flask with additional libraries and functionality is straightforward.

## Web Frameworks in Python
Before diving into Flask, let's briefly discuss the role of web frameworks in Python web development.

### Web Frameworks
Web frameworks provide a structured way to build web applications. They offer tools and libraries for common tasks, such as handling HTTP requests, managing sessions, and interacting with databases.

### Flask vs. Other Web Frameworks
While there are several web frameworks available for Python (Django, Pyramid, etc.), Flask stands out for its simplicity and flexibility. It doesn't enforce a particular way of doing things, allowing developers to make choices based on their preferences and project requirements.

### Book Management System
Our project will be a Book Management System (BMS) where users can:
- View a list of books
- Add new books
- Update book information
- Delete books

## Setting Up the Development Environment

#### Prerequisites

- [Python](https://www.python.org/downloads/)

- [Virtualenv](https://virtualenv.pypa.io/en/latest/installation.html) (for creating isolated Python environments)

## Initializing a Flask Project

### Environment Setup
#### Create a Virtual Environment
Open your terminal and navigate to the directory where you want to create your project. Run the following commands:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```
#### Install Flask
With the virtual environment activated, install Flask using pip:
```bash
pip install Flask
```

## Basic App Structure

All Flask app starts with a file mostly `app.py`

```python
from flask import Flask

app = Flask(__name__)

if __name__ == '__main__':
    app.run(debug=True)
```

There are two ways to create a Flask app

1. Use Functions to define routes
2. Use Classes to define routes

## BMS Using Functions

### POST
```python
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route("/<int:data_id>",methods=["POST"])
def post(data_id):
    data = request.json
    books[data_id] = data
    return jsonify(books)

if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```

### GET

```python
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route("/<int:data_id>",methods=["POST"])
def post(data_id):
    data = request.json
    books[data_id] = data
    return jsonify(books)

@app.route("/<int:data_id>", methods=["GET"])
def get(data_id):
    return jsonify(books.get(data_id))

if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```

### PUT
```python
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route("/<int:data_id>",methods=["POST"])
def post(data_id):
    data = request.json
    books[data_id] = data
    return jsonify(books)

@app.route("/<int:data_id>", methods=["GET"])
def get(data_id):
    return jsonify(books.get(data_id))

@app.route("/<int:data_id>", methods=["PUT"])
def put(data_id):
    data = request.json
    books[data_id].update(data)
    return jsonify(books.get(data_id))


if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```

### PATCH
```python
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route("/<int:data_id>",methods=["POST"])
def post(data_id):
    data = request.json
    books[data_id] = data
    return jsonify(books)

@app.route("/<int:data_id>", methods=["GET"])
def get(data_id):
    return jsonify(books.get(data_id))

@app.route("/<int:data_id>", methods=["PUT"])
def put(data_id):
    data = request.json
    books[data_id].update(data)
    return jsonify(books.get(data_id))

@app.route("/<int:data_id>", methods=["PATCH"])
def patch(data_id):
    data = request.json
    books[data_id].update(data)
    return jsonify(books.get(data_id))

if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```

### DELETE
```python
from flask import Flask, request, jsonify
import json

app = Flask(__name__)

@app.route("/<int:data_id>",methods=["POST"])
def post(data_id):
    data = request.json
    books[data_id] = data
    return jsonify(books)

@app.route("/<int:data_id>", methods=["GET"])
def get(data_id):
    return jsonify(books.get(data_id))

@app.route("/<int:data_id>", methods=["PUT"])
def put(data_id):
    data = request.json
    books[data_id].update(data)
    return jsonify(books.get(data_id))

@app.route("/<int:data_id>", methods=["PATCH"])
def patch(data_id):
    data = request.json
    books[data_id].update(data)
    return jsonify(books.get(data_id))

@app.route("/<int:data_id>", methods=["DELETE"])
def delete(data_id):
    books.pop(data_id,{})
    return jsonify(books.get(data_id))

if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```


## BMS Using Classes
To use classes, we need to import `MethodView`


### POST 
```python
from flask import Flask, request, jsonify
from flask.views import MethodView

app = Flask(__name__)

class Book(MethodView):
    def post(self,data_id):
        data = request.json
        books[data_id] = data
        return jsonify(books)
    
app.add_url_rule("/<int:data_id>",view_func=Book.as_view("Home"),methods=["POST"])

if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```

### GET
```python
from flask import Flask, request, jsonify
from flask.views import MethodView

app = Flask(__name__)

class Book(MethodView):
    def post(self,data_id):
        data = request.json
        books[data_id] = data
        return jsonify(books)

    def get(self,data_id):
        return jsonify(books.get(data_id))

    
app.add_url_rule("/<int:data_id>",view_func=Book.as_view("Home"),methods=["GET","POST"])

if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```

### PUT
```python
from flask import Flask, request, jsonify
from flask.views import MethodView

app = Flask(__name__)

class Book(MethodView):
    def post(self,data_id):
        data = request.json
        books[data_id] = data
        return jsonify(books)

    def get(self,data_id):
        return jsonify(books.get(data_id))
    
    def put(self,data_id):
        data = request.json
        books[data_id].update(data)
        return jsonify(books.get(data_id))

    
app.add_url_rule("/<int:data_id>",view_func=Book.as_view("Home"),methods=["GET","POST","PUT"])

if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```

### PATCH
```python
from flask import Flask, request, jsonify
from flask.views import MethodView

app = Flask(__name__)

class Book(MethodView):
    def post(self,data_id):
        data = request.json
        books[data_id] = data
        return jsonify(books)

    def get(self,data_id):
        return jsonify(books.get(data_id))
    
    def put(self,data_id):
        data = request.json
        books[data_id].update(data)
        return jsonify(books.get(data_id))

    def patch(self,data_id):
        data = request.json
        books[data_id].update(data)
        return jsonify(books.get(data_id))

    
app.add_url_rule("/<int:data_id>",view_func=Book.as_view("Home"),methods=["GET","POST","PUT","PATCH"])

if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```

### DELETE
```python
from flask import Flask, request, jsonify
from flask.views import MethodView

app = Flask(__name__)

class Book(MethodView):
    def post(self,data_id):
        data = request.json
        books[data_id] = data
        return jsonify(books)

    def get(self,data_id):
        return jsonify(books.get(data_id))
    
    def put(self,data_id):
        data = request.json
        books[data_id].update(data)
        return jsonify(books.get(data_id))

    def patch(self,data_id):
        data = request.json
        books[data_id].update(data)
        return jsonify(books.get(data_id))
    
    def delete(self,data_id):
        books.pop(data_id,{})
        return jsonify(books.get(data_id))
    
app.add_url_rule("/<int:data_id>",view_func=Book.as_view("Home"),methods=["GET","POST","PUT","PATCH","DELETE"])

if __name__ == '__main__':
    books = {}
    app.run(debug=True)
```

## app.py | BMS class
```python
import errno
from flask import Flask, request, jsonify
from flask.views import MethodView

app = Flask(__name__)

class Books():
    def __init__(self):
        self.books = {}

    def bookError(self, error, book_id=None):
        return {
            "book_id": book_id,
            "Error": error
        }
    
    def create(self,book_id,book_data):
        try:
            self.books[book_id]=book_data
            return {"message": "Book Created"}
        except KeyError:
            return self.bookError("Book not found", book_id)
        except Exception as err:
            return self.bookError(str(err), book_id)

    def read(self,book_id):
        try:
            return {"message": "Book Fetched", "book": self.books[book_id]}
        except KeyError:
            return self.bookError("Book not found", book_id)
        except Exception as err:
            return self.bookError(str(err), book_id)
    
    def update(self,book_id,updated_book_data):
        try:
            self.books[book_id].update(updated_book_data)
            return {"message": "Book Updated", "book": self.books.get(book_id)}
        except KeyError:
            return self.bookError("Book not found", book_id)
        except Exception as err:
            return self.bookError(str(err), book_id)
    
    def delete(self,book_id):
        try:
            deleted_book = self.books.pop(book_id)
            return {"message": "Book Deleted", "deleted book": deleted_book}
        except KeyError:
            return self.bookError("Book not found", book_id)
        except Exception as err:
            return self.bookError(str(err), book_id)

class Book(MethodView):
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
        return jsonify(books.delete(book_id))
    
app.add_url_rule("/<int:book_id>",view_func=Book.as_view("Home"),methods=["GET","POST","PUT","PATCH","DELETE"])

if __name__ == '__main__':
    books = Books()
    app.run(debug=True)
```

## Adding DB in the application

### Install dependencies
```bash
pip install Flask SQLAlchemy
```

### Configure SQLAlchemy
```python
from flask_sqlalchemy import SQLAlchemy

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'  # Use SQLite for simplicity
db = SQLAlchemy(app)
```

### Create a model
```python
from datetime import datetime

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
```

### Create the database
```python
if __name__ == '__main__':

    with app.app_context():
        db.create_all()
```

### Update logic for CRUD according to DB
```python
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
```

### Complete DB connected single application file
```python
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
```

## Creating Using the MVC Model

### create a file name models.py
```python
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
```

### create a file name controllers.py
```python
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
```

### create a file name views.py
```python
# app.py
from flask import Flask
from controllers import BookView
from models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///books.db'
db.init_app(app)

with app.app_context():
    db.create_all()


app.add_url_rule("/<int:book_id>", view_func=BookView.as_view("BMS"), methods=["GET", "POST", "PUT", "PATCH", "DELETE"])

if __name__ == '__main__':
    app.run(debug=True)
```


## Authentication and Authorization

### Authentication

*Authentication is the process of verifying the identity of a user or system. In Flask, common methods for implementing authentication include session-based authentication and token-based authentication.*

#### Session-Based Authentication

```python
from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = "my_secret_key"

sample_users = {
    f"user_{i}":f"password_{i}" for i in range(10)
}

@app.route("/login", methods=["POST"])
def login():
    """
    {
        "username": "user_1",
        "password": "password_1",
    }
    """
    if request.method != 'POST':
        return jsonify({
            "message":"Failed, Only post request allowed"
        })
    data = request.json
    if sample_users[data.get("username")] == data.get("password"):
        session['username'] = data.get("username")
        return jsonify({
            "message":"login successful"
        })
    else:
        return jsonify({
            "message":"login failed"
        })

@app.route("/logout")
def logout():
    session.pop('username',None)
    return jsonify({
            "message":"logout successful"
    })

@app.route("/")
def home():
    if 'username' in session:
        return f"<h1>Welcome {session['username']}</h1>"
    else:
        return jsonify({
            "message":"Please login"
        })

if __name__ == '__main__':
    app.run(debug=True)
```

#### Token-Based Authentication
```python
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import timedelta

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] ='jwt_secret_key'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=1)

jwt = JWTManager(app)

sample_users = {
    f"user_{i}":f"password_{i}" for i in range(10)
}



@app.route("/login", methods=["POST"])
def login():
    """
    {
        "username": "user_1",
        "password": "password_1",
    }
    """
    if request.method != 'POST':
        return jsonify({
            "message":"Failed, Only post request allowed"
        })
    data = request.json
    if sample_users[data.get("username")] == data.get("password"):
        access_token = create_access_token(identity=data.get("username"))
        return jsonify({'access_token': access_token})
    else:
        return jsonify({
            "message":"login failed"
        })

@app.route("/")
@jwt_required()
def home():
    current_user = get_jwt_identity()
    if current_user:
        return f"<h1>Welcome {current_user}</h1>"
    else:
        return jsonify({
            "message":"Please login"
        })

if __name__ == '__main__':
    app.run(debug=True)
```

## Authorization

*Authorization involves determining what actions a user is allowed to perform within an application. Flask provides various ways to implement authorization, often involving user roles and permissions.*

### Role-Based Authorization

```python
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "secret_key"
app.config["JWT_SECRET_KEY"] = "jwt_secret_key"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=1)

jwt = JWTManager(app)

sample_users = {
    f"user_{i}":f"password_{i}" for i in range(10)
}

sample_role = {
    f"user_{i}": "admin" for i in range(0,10,2)
}

@app.route("/login",methods=["POST"])
def login():
    data = request.json
    if sample_users[data.get("username")] == data.get("password"):
        access_token = create_access_token(identity=data.get("username"))
        return jsonify({'access_token': access_token})
    else:
        return jsonify({
            "message":"login failed"
        })

@app.route("/", methods=["GET"])
@jwt_required()
def home():
    user = get_jwt_identity()
    if user:
        return f"<h1>Welcome {user}</h1>"
    else:
        return jsonify({
            "message":"Please login"
        })

@app.route("/update", methods=["GET"])
@jwt_required()
def update():
    user = get_jwt_identity()
    if sample_role.get(user) == 'admin':
        return jsonify({
            "message": f"Welcome admin {user}"
        })
    else:
        return jsonify({
            "message": f"You are not admin! {user}"
        })

if __name__ == '__main__':
    app.run(debug=True)
```

### Access-Based Authorization

```python
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "secret_key"
app.config["JWT_SECRET_KEY"] = "jwt_secret_key"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=1)

jwt = JWTManager(app)

sample_users = {
    f"user_{i}":f"password_{i}" for i in range(10)
}

sample_access = {
    f"user_{i}": "write" for i in range(0,10,2)
}

@app.route("/login",methods=["POST"])
def login():
    data = request.json
    if sample_users[data.get("username")] == data.get("password"):
        access_token = create_access_token(identity=data.get("username"))
        return jsonify({'access_token': access_token})
    else:
        return jsonify({
            "message":"login failed"
        })

@app.route("/", methods=["GET"])
@jwt_required()
def home():
    user = get_jwt_identity()
    if user:
        return f"<h1>Welcome {user}</h1>"
    else:
        return jsonify({
            "message":"Please login"
        })

@app.route("/update", methods=["GET"])
@jwt_required()
def update():
    user = get_jwt_identity()
    if sample_access.get(user) == 'write':
        return jsonify({
            "message": f"Welcome {user}, have write permission"
        })
    else:
        return jsonify({
            "message": f"{user}, does not have write permission"
        })

if __name__ == '__main__':
    app.run(debug=True)
```