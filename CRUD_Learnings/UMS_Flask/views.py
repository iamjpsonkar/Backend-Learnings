from flask import Flask
from models import db
from controllers import UserView

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db.init_app(app)

with app.app_context():
    db.create_all()

app.add_url_rule("/<int:user_id>",view_func=UserView.as_view("UMS"),methods=["GET","POST"])

if __name__ == '__main__':
    app.run(debug=True)
