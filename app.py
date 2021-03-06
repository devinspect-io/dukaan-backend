"""API for Achi Dukaan"""

import os
import sys
import re
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
from schemas.business import business_schema
from schemas.rating import rating_schema

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
        return jsonify(access_token=access_token, user_id=str(user["_id"])), 200

    return jsonify({"message": "Invalid email or password"}), 401


@app.route("/user/<user_id>", methods=["GET"])
@jwt_required
def get_user(user_id):
    """ GET user"""
    user = db.users.find_one({"_id": ObjectId(user_id)})
    if user is None:
        return jsonify({"success": False, "message": "User not found."}), 404

    return jsonify({"success": True, "user": clean_dict_helper(user)}), 200


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

    # payload = change_case(payload, "lower")
    db.users.insert_one(payload)
    return jsonify({"success": True, "user": clean_dict_helper(payload)}), 201


@app.route("/dukaan", methods=["GET", "POST"])
def get_or_add_dukaan():
    """ Add a new business """
    if request.method == "POST":
        payload = request.json
        # payload = change_case(payload, "lower")
        business = db.dukaans.find_one({"name": payload["name"]})
        if business is not None:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Business name already exists, Please choose another name.",
                    }
                ),
                400,
            )

        for required_key in business_schema:
            if required_key not in payload.keys():
                return jsonify({"message": f"Missing {required_key} parameter"}), 400

        db.dukaans.insert_one(payload)
        return jsonify({"success": True, "dukaan": clean_dict_helper(payload)}), 201

    dukaans = list(db.dukaans.find({}).limit(5))
    for dukaan in dukaans:
        if len(dukaan.get("categories", [])) > 0:
            dukaan["categories"] = [
                db.categories.find_one({"_id": ObjectId(_id)})["name"]
                for _id in dukaan["categories"]
            ]
        ratings = list(db.ratings.find({"business": str(dukaan["_id"])}, {"rating": 1}))
        if len(ratings) > 0:
            ratings_sum = sum([r["rating"] for r in ratings])
            dukaan["avg_rating"] = float(ratings_sum) / float(len(ratings))
        else:
            dukaan["avg_rating"] = 0.0

    return jsonify({"success": True, "dukaans": clean_dict_helper(dukaans)})


@app.route("/category/<category_name>", methods=["GET"])
def add_category(category_name):
    """ Adds a new category """
    category_name = category_name.lower()
    db.categories.insert_one({"name": category_name})
    return jsonify({"success": True, "message": f"{category_name} added successfully."})


@app.route("/categories", methods=["GET"])
def get_categories():
    """ List all categories """
    categories = list(db.categories.find({}))
    return jsonify({"success": True, "categories": clean_dict_helper(categories)})


@app.route("/rating", methods=["POST"])
def add_rating():
    """Add a new rating"""
    try:
        payload = request.json
        # payload = change_case(payload, "lower")
        for required_key in rating_schema:
            if required_key not in payload.keys():
                return jsonify({"message": f"Missing {required_key} parameter"}), 400
        
        db_rating = db.ratings.find_one(
            {
                "user": payload["user"],
                "business": payload["business"],
            }
        )
        if db_rating is not None:
            db.ratings.update_one({
                '_id': db_rating['_id']
            },{
            '$set': {
                'rating': payload['rating'],
                'comment': payload['comment']
                }
            }, upsert=False)
        else:
            db.ratings.insert_one(payload)
        

        # Now get updated business details
        business_id = payload["business"]
        business = db.dukaans.find_one({"_id": ObjectId(business_id)})
        if business is None:
            return jsonify({"success": False, "message": "Business not found."}), 404

        if len(business.get("categories", [])) > 0:
            business["categories"] = [
                db.categories.find_one({"_id": ObjectId(_id)})["name"]
                for _id in business["categories"]
            ]
        ratings = list(db.ratings.find({"business": str(business_id)}))
        if len(ratings) > 0:
            ratings_sum = sum([r["rating"] for r in ratings])
            business["avg_rating"] = round(float(ratings_sum) / float(len(ratings)), 1)
        else:
            business["avg_rating"] = 0.0

        for rating in ratings:
            rating["user_name"] = db.users.find_one({"_id": ObjectId(rating["user"])})[
                "name"
            ]

        business["ratings"] = ratings
        business["total_ratings"] = len(ratings)
        return jsonify({"success": True, "business": clean_dict_helper(business)}), 201
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
    businesses = list(db.dukaans.find({"city": {"$regex": city, "$options": "i"}}))
    # businesses = list(db.dukaans.find({"city": city}).limit(10))
    for business in businesses:
        if len(business.get("categories", [])) > 0:
            business["categories"] = [
                db.categories.find_one({"_id": ObjectId(_id)})["name"]
                for _id in business["categories"]
            ]
        ratings = list(
            db.ratings.find({"business": str(business["_id"])}, {"rating": 1})
        )
        if len(ratings) > 0:
            ratings_sum = sum([r["rating"] for r in ratings])
            business["avg_rating"] = round(float(ratings_sum) / float(len(ratings)), 1)
        else:
            business["avg_rating"] = 0.0
        business["total_ratings"] = len(ratings)
    return jsonify({"success": True, "businesses": clean_dict_helper(businesses)})


@app.route("/business/<business_id>", methods=["GET"])
def get_business_details(business_id):
    """ Get business details along with rating """

    business = db.dukaans.find_one({"_id": ObjectId(business_id)})
    if business is None:
        return jsonify({"success": False, "message": "Business not found."}), 404

    if len(business.get("categories", [])) > 0:
        business["categories"] = [
            db.categories.find_one({"_id": ObjectId(_id)})["name"]
            for _id in business["categories"]
        ]
    ratings = list(db.ratings.find({"business": str(business_id)}))
    if len(ratings) > 0:
        ratings_sum = sum([r["rating"] for r in ratings])
        business["avg_rating"] = round(float(ratings_sum) / float(len(ratings)), 1)
    else:
        business["avg_rating"] = 0.0

    for rating in ratings:
        rating["user_name"] = db.users.find_one({"_id": ObjectId(rating["user"])})[
            "name"
        ]

    business["ratings"] = ratings
    business["total_ratings"] = len(ratings)
    return jsonify({"success": True, "business": clean_dict_helper(business)})


@app.route("/search/<query>", methods=["GET"])
def search(query):
    """ Search by business name """
    rgx = re.compile(".*{}.*".format(query), re.IGNORECASE)  # compile the regex

    businesses = list(db.dukaans.find({"name": rgx}))
    if len(businesses) == 0:
        return jsonify({"success": False, "business": []}), 404

    return jsonify({"success": True, "business": clean_dict_helper(businesses)})
