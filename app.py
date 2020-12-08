"""API for Achi Dukaan"""

import os
import sys
from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_jwt_extended import (
    JWTManager,
    jwt_required,
    create_access_token,
    get_jwt_identity,
)

from schemas.users import users_schema
from utils import clean_dict_helper


app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI"))
db = client["dukaan"]

# Setup the Flask-JWT-Extended extension
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)


@app.route("/")
def hello_world():
    """Welcome route"""
    return jsonify({"message": "Welcome to Dukaan Rating API"})


@app.route("/login", methods=["POST"])
def login():
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request"}), 400

    email = request.json.get("email", None)
    password = request.json.get("password", None)
    if not email:
        return jsonify({"message": "Missing email parameter"}), 400
    if not password:
        return jsonify({"message": "Missing password parameter"}), 400

    user = db.users.find_one({"email": email})

    if user is None:
        return jsonify({"message": "User not found"}), 404

    if user["password"] == password:
        # Return access token
        access_token = create_access_token(identity=email)
        return jsonify(access_token=access_token), 200

    return jsonify({"message": "Invalid email or password"}), 401


@app.route("/user/<user_id>", methods=["GET"])
@jwt_required
def get_user(user_id):
    """ GET user"""
    user = db.users.find_one({"_id": ObjectId(user_id)})

    if user is None:
        return jsonify({"success": False, "message": "User not found."}), 404

    return jsonify({"success": True, "user": clean_dict_helper(user)})


@app.route("/user", methods=["POST"])
def add_user():
    """ Add a user"""
    payload = request.json
    for required_key in users_schema:
        if required_key not in payload.keys():
            return jsonify({"message": f"Missing {required_key} parameter"}), 400

    user = db.users.find_one({"email": payload["email"]})
    if user is not None:
        return (
            jsonify(
                {
                    "success": False,
                    "message": f'Duplicate email detected. User {payload["email"]} already exists.',
                }
            ),
            400,
        )

    db.users.insert_one(payload)
    return jsonify({"success": True, "user": clean_dict_helper(payload)}), 201


@app.route("/dukaan", methods=["GET", "POST"])
@jwt_required
def get_or_add_dukaan():
    """ Add a new business """
    if request.method == "POST":
        payload = request.json
        db.dukaans.insert_one(payload)
        return jsonify({"success": False, "dukaan": clean_dict_helper(payload)}), 201

    dukaans = list(db.dukaans.find({}))
    return jsonify({"success": True, "dukaans": clean_dict_helper(dukaans)})


@app.route("/rating", methods=["POST"])
@jwt_required
def add_rating():
    """Add a new rating"""
    try:
        payload = request.json
        db_rating = db.ratings.find_one(
            {
                "user": payload["user"],
                "business": payload["business"],
            }
        )
        if db_rating is not None:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": """Duplicate Rating detected for Shop 
                        {} User {} already exists.""".format(
                            payload["user"], payload["business"]
                        ),
                    }
                ),
                400,
            )
        db.ratings.insert_one(payload)
        return jsonify({"success": True, "rating": clean_dict_helper(payload)}), 201

    except Exception as err:
        print("Error: ", str(err))
        print(sys.exc_info()[-1].tb_lineno)


@app.route("/rating/<business_id>", methods=["GET"])
def get_rating(business_id):
    """ GET Business rating"""
    rating = list(
        db.ratings.aggregate(
            [{"$group": {"_id": "$business", "pop": {"$avg": "$rating"}}}]
        )
    )
    if rating is None:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Rating for business {} not found.".format(business_id),
                }
            ),
            404,
        )
    print(rating)
    return jsonify({"success": True, "rating": clean_dict_helper(rating)})


@app.route("/get-business-by-city/<city>", methods=["GET"])
def get_business_by_city(city):
    businesses = list(db.dukaans.find({"city": city}))
    if len(businesses) == 0:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Business for city {} not found.".format(city),
                }
            ),
            404,
        )

    return jsonify({"success": True, "businesses": clean_dict_helper(businesses)})
