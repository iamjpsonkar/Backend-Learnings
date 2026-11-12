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