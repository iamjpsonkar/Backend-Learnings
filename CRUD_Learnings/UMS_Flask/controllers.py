from flask import jsonify, request
from flask.views import MethodView
from models import User, db

class UserView(MethodView):
    def post(self, user_id):
        try:
            user_data = request.json
            user_data.update({'id':user_id})
            user = User(**user_data)
            db.session.add(user)
            db.session.commit()
            return jsonify({
                "message": "User added",
                "user": user.to_dict()
            })
        except Exception as err:
            return jsonify({
                "message": "User not Added",
                "Error": str(err)
            })
    
    def get(self,user_id):
        try:
            user = User.query.get_or_404(user_id)
            return jsonify({
                "message": "User fetched",
                "user": user.to_dict()
            })
        except Exception as err:
            return jsonify({
                "message": "User fetch failed",
                "Error": str(err)
            })