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