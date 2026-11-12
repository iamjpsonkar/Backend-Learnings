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