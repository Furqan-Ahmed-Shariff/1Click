from flask import Flask, request, jsonify, session
import json, re
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
from bson.json_util import dumps, loads
import os
import datetime
from flask_mail import Message,Mail

load_dotenv()

app = Flask(__name__)
bcrypt = Bcrypt()
app.secret_key = os.environ.get("SECRET_KEY")

# MongoDB configuration
MONGO_URI = os.environ.get("MONGO_URI")
DATABASE_NAME = "infothon-vvce"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
users_col = db["users"]
events_col = db["events"]
attendees_col = db["attendees"]

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("EMAIL")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("EMAIL")
app.config['MAIL_PASSWORD'] = os.environ.get("APP_PASSWORD")
mail = Mail(app)


def parse_json(data):
    return json.loads(json.dumps(data, default=str))

def validate_password(password):

    # Password checker
    # Primary conditions for password validation:
    # Minimum 8 characters.
    # The alphabet must be between [a-z]
    # At least one alphabet should be of Upper Case [A-Z]
    # At least 1 number or digit between [0-9].
    # At least 1 character from [ _ or @ or $ ]. 

    #\s- Returns a match where the string contains a white space character
    if len(password) < 8 or re.search("\s" , password):  
        return False  
    if not (re.search("[a-z]", password) and re.search("[A-Z]", password) and re.search("[0-9]", password) ):
        return False  
    return True  

@app.route("/api/signup", methods=["POST"])
def signup():
    # Get the signup data from the request
    data = request.get_json()

    # Validate the required fields
    required_fields = [
        "coordinates",
        "description",
        "name",
        "password",
        "confirmPassword",
        "languages",
        "topics",
        "email",
        "phone",
        "organization",
        "status",
        "industry",
        "age",
        "gender",
        "discoverable",
    ]
    for field in required_fields:
        if field not in data:
            return jsonify(error=f"Missing required field: {field}"), 400

    # Validate Password
    if not validate_password(data["password"]):
        return jsonify(error="Password must contain atleast 8 characters, 1 uppercase, 1 lowercase, 1 number and 1 special character"), 400
    
    # Compare password with confirmPassword
    if data["password"] != data["confirmPassword"]:
        return jsonify(error="Passwords do not match"), 400

    if users_col.find_one({"email": data["email"]}) is not None:
        return jsonify(error="User already exists!"), 400

    # Hash the password
    hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

    # Create a new user document
    user = {
        "coordinates": data["coordinates"],
        "description": data["description"],
        "name": data["name"],
        "password": hashed_password,
        "languages": data["languages"],
        "topics": data["topics"],
        "email": data["email"],
        "phone": data["phone"],
        "organization": data["organization"],
        "status": data["status"],
        "industry": data["industry"],
        "age": data["age"],
        "gender": data["gender"],
        "discoverable": data["discoverable"],
        "createdAt": datetime.datetime.utcnow(),
    }

    # Insert the user document into the users collection
    users_col.insert_one(user)

    # Send email to user
    subject = f"You're registered to 1Click, {data['name']}"
    body = "Your registeration is complete!\nLogin here http://localhost:3000/login to get started with 1Click!"
    
    # # Create the plain-text and HTML version of your message
    text = "Subject:" + subject + "\n" + body
    html = """
    <html>
    <body>
        <h2>Your registeration is complete!</h2>
        <p><em><a href="http://localhost:3000/login">Login here</a></em> to get started with 1Click!</p>
    </body>
    </html>
    """

    msg = Message()
    msg.subject = subject
    msg.recipients = [data['email']]
    msg.body = text
    msg.html = html
    mail.send(msg)

    return jsonify(message="Signup successful")


@app.route("/api/login", methods=["POST"])
def login():
    # Get the login data from the request
    data = request.get_json()

    # Validate the required fields
    required_fields = ["email", "password"]
    for field in required_fields:
        if field not in data:
            return jsonify(error=f"Missing required field: {field}"), 400

    # Retrieve the user document from the users collection
    user = users_col.find_one({"email": data["email"]})

    if user is None:
        return jsonify(error="User doesn't exist"), 400


    if user and bcrypt.check_password_hash(user["password"], data["password"]):
        # Store the entire user in the session
        # parse_json helps us deal with ObjectID in python
        session["user"] = parse_json(user)
        return parse_json(user), 200
    else:
        return jsonify(error="Invalid credentials"), 400


@app.route("/api/logout", methods=["POST"])
def logout():
    # Clear the user from the session
    if not session.get("user"):
        return jsonify({"error": "Not logged in"}), 403
    session.pop("user", None)
    return jsonify(message="Logout successful")


@app.route("/api/forgot-password", methods=["POST"])
def forgot_password():
    # Get the forgot password data from the request
    data = request.get_json()

    # Validate the required fields
    required_fields = ["email"]
    for field in required_fields:
        if field not in data:
            return jsonify(error=f"Missing required field: {field}"), 400

    # Retrieve the user document from the users collection
    user = users_col.find_one({"email": data["email"]})

    if user:
        # Reset the password logic here (e.g., send password reset email)
        return jsonify(message="Password reset email sent")
    else:
        return jsonify(error="User not found")


@app.route("/api/create", methods=["POST"])
def create_event():
    # Get the event data from the request
    if not session.get("user"):
        return jsonify(error="Not logged in"), 403

    data = request.get_json()

    # Validate the required fields
    required_fields = [
        "description",
        "name",
        "language",
        "topics",
        "fields",
        "email",
        "phone",
        "status",
        "industry",
        "minAge",
        "maxAge",
        "startDate",
        "endDate",
        "coordinates",
        "venue",
        "location",
        "url",
        "genders",
    ]
    for field in required_fields:
        if field not in data:
            return jsonify(error=f"Missing required field: {field}"), 400

    # Create a new event document
    event = {
        "description": data["description"],
        "name": data["name"],
        "language": data["language"],
        "topics": data["topics"],
        "fields": data["fields"],
        "email": data["email"],
        "phone": data["phone"],
        "status": data["status"],
        "industry": data["industry"],
        "minAge": data["minAge"],
        "maxAge": data["maxAge"],
        "startDate": data["startDate"],
        "endDate": data["endDate"],
        "coordinates": data["coordinates"],
        "venue": data["venue"],
        "location": data["location"],
        "url": data["url"],
        "genders": data["genders"],
        "uid": data["uid"],
        "createdAt": datetime.datetime.utcnow(),
    }

    # Insert the event document into the events collection
    events_col.insert_one(event)

    return jsonify(message="Event created")


@app.route("/api/network")
def network():
    if not session.get("user"):
        return jsonify({"error": "Not logged in"}), 403

    # print(session.get("user").get("email"), session["user"])
    query = {"email": {"$ne": session.get("user").get("email")}, "discoverable": True}
    networks = list(users_col.find(query))
    return parse_json(networks), 200


@app.route("/api/recommended")
def recommended():
    recommended_events = list(events_col.find())
    return parse_json(recommended_events), 200


@app.route("/api/search", methods=["GET"])
def search_events():
    if not session.get("user"):
        return jsonify({"error": "Not logged in"}), 403
    query = request.args.get("query")

    # Construct the search query
    search_query = {
        "$or": [
            {"name": {"$regex": query, "$options": "i"}},
            {"venue": {"$regex": query, "$options": "i"}},
            {"location": {"$regex": query, "$options": "i"}},
            {"topics": {"$regex": query, "$options": "i"}},
            {"description": {"$regex": query, "$options": "i"}},
        ]
    }

    # Perform the search in the database
    events = list(events_col.find(search_query))
    return parse_json(events)


# Events listed by the user
@app.route("/api/list")
def list_events():
    if not session.get("user"):
        return jsonify({"error": "Not logged in"}), 403

    query = {"uid": {"$eq": session.get("user").get("_id")}}
    events = list(events_col.find(query))
    return parse_json(events), 200


@app.route("/api/list-attendees/<eid>")
def list_attendees(eid):
    if not session.get("user"):
        return jsonify({"error": "Not logged in"}), 403

    query = {"eid": eid}
    events = list(attendees_col.find(query))
    return parse_json(events), 200


# Users reigistering for the event
@app.route("/api/register/<eid>", methods=["POST"])
def register(eid):
    # if not session.get("user"):
    data = request.get_json()
    # print(data, data["isRegistered"])
    # if data.get("email") and session.get("user") is None:
    #     email = attendees_col.find_one({"email": data.get("email"), "eid": eid})
    #     print("EMAILLLL ", email)
    #     if email is not None:
    #         return jsonify(error="Email already registered for the event!"), 400

    if data["isRegistered"] is True:
        fields = events_col.find_one({"_id": ObjectId(eid)}, {"fields": 1, "_id": 0})
        attendee_details = {}
        for field in fields["fields"]:
            attendee_details[field.lower()] = data[field]
        attendee_details["eid"] = eid
        if session.get("user_id"):
            attendee_details["uid"] = session.get("user").get("_id")  # or data["_id"]

        attendees_col.insert_one(attendee_details)
        return jsonify(fields), 201
    else:
        attendees_col.delete_one({"uid": session.get("user").get("_id"), "eid": eid})
        return jsonify(message="Successfully unregistered"), 200


# Check if the user is registered
@app.route("/api/check-register/<eid>")
def check_register(eid):
    check = None
    if session.get("user"):
        check = attendees_col.find_one(
            {"eid": eid, "uid": session.get("user").get("_id")}
        )
        return jsonify({"registered": True}), 200
    if check is None:
        return jsonify({"registered": False}), 200


# Implement this Afnan
@app.route("/api/my-events")
def my_events():
    if session.get("user"):
        events = attendees_col.find({"uid": session.get("user").get("_id")})


# Check if user's session exists
@app.route("/api/check-user")
def check_user():
    if session.get("user"):
        return parse_json({"exists": True, "user": session.get("user")}), 200
    return jsonify({"exists": False}), 200


if __name__ == "__main__":
    app.run(debug=True)