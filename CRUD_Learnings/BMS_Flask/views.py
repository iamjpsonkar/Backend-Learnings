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
