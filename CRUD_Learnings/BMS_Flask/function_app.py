from flask import Flask, request, jsonify

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