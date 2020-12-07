"""API for Achi Dukaan"""
import sys
import os
from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson.objectid import ObjectId
from utils import clean_dict_helper


app = Flask(__name__)
client = MongoClient(os.getenv("MONGO_URI"))
db = client["dukaan"]


@app.route("/")
def hello_world():
    """Welcome route"""
    return jsonify({"message": "Welcome to Dukaan Rating API"})


@app.route("/user/<user_id>", methods=["GET"])
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
    return jsonify({"success": False, "user": clean_dict_helper(payload)}), 201


@app.route("/dukaan", methods=["GET", "POST"])
def get_or_add_dukaan():
    """ Add a new business """
    if request.method == "POST":
        payload = request.json
        db.dukaans.insert_one(payload)
        return jsonify({"success": False, "dukaan": clean_dict_helper(payload)}), 201

    dukaans = list(db.dukaans.find({}))
    return jsonify({"success": True, "dukaans": clean_dict_helper(dukaans)})


@app.route("/rating", methods=["POST"])
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
    rating = db.ratings.aggregate(
        [{"$group": {"_id": business_id, "pop": {"$avg": "$rating"}}}]
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

    return jsonify({"success": True, "rating": clean_dict_helper(rating)})


# by cities
# by search
