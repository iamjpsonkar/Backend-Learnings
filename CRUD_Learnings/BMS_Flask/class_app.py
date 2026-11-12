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