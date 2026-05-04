import os
import datetime
import secrets
from functools import wraps

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from pymongo import MongoClient
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv


# -------------------------------------------------------------
# Load environment variables from .env
# -------------------------------------------------------------
load_dotenv(dotenv_path=".env", override=True)


app = Flask(__name__)
CORS(app)


# -------------------------------------------------------------
# Configuration
# -------------------------------------------------------------
app.config["SECRET_KEY"] = os.environ.get("JWT_SECRET")

if not app.config["SECRET_KEY"]:
    print("JWT_SECRET is missing. Please add it to .env")
    exit(1)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/pawpal")


# -------------------------------------------------------------
# Connect to MongoDB
# -------------------------------------------------------------
try:
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client.get_default_database(default="pawpal")
    users_collection = db["users"]
    chat_history_collection = db["chatHistory"]
    print("✅ Connected to MongoDB")
except Exception as e:
    print("❌ MongoDB Connection Error:", e)
    exit(1)


# -------------------------------------------------------------
# Gemini / GenAI Client
# -------------------------------------------------------------
gemini_api_key = os.environ.get("GEMINI_API_KEY")

if not gemini_api_key:
    print("GEMINI_API_KEY is missing. Please add it to .env")
    exit(1)


ai_client = genai.Client(api_key=gemini_api_key)


# -------------------------------------------------------------
# Middleware for Token Verification
# -------------------------------------------------------------
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        token = None

        auth_header = request.headers.get("Authorization")

        if auth_header:
            parts = auth_header.split()

            if len(parts) == 2 and parts[0] == "Bearer":
                token = parts[1]

        if not token:
            return jsonify({"error": "Token is missing!"}), 401

        try:
            data = jwt.decode(
                token,
                app.config["SECRET_KEY"],
                algorithms=["HS256"]
            )

            from bson.objectid import ObjectId

            current_user = users_collection.find_one({
                "_id": ObjectId(data["user_id"])
            })

            if not current_user:
                return jsonify({"error": "User not found!"}), 401

        except Exception:
            return jsonify({"error": "Token is invalid!"}), 401

        return f(current_user, *args, **kwargs)

    return decorator


# -------------------------------------------------------------
# Frontend Page Routes
# -------------------------------------------------------------
@app.route("/")
def home():
    return render_template("landing.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/forgot-password")
def forgot_password_page():
    return render_template("forgot-password.html")


@app.route("/reset-password/<token>")
def reset_password_page(token):
    return render_template("reset-password.html")


@app.route("/chatbot")
def chatbot_page():
    return render_template("index.html")


# -------------------------------------------------------------
# API Auth Routes
# -------------------------------------------------------------
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if users_collection.find_one({"email": email}):
        return jsonify({"error": "User with this email already exists"}), 400

    hashed_password = generate_password_hash(password)

    user_doc = {
        "name": name,
        "email": email,
        "password_hash": hashed_password,
        "dogName": data.get("dogName", ""),
        "dogBreed": data.get("dogBreed", ""),
        "dogAge": data.get("dogAge", ""),
        "createdAt": datetime.datetime.utcnow(),
        "updatedAt": datetime.datetime.utcnow()
    }

    result = users_collection.insert_one(user_doc)

    token = jwt.encode(
        {
            "user_id": str(result.inserted_id),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
        },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    return jsonify({
        "message": "Registered successfully",
        "token": token,
        "user": {
            "name": name,
            "email": email
        }
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = users_collection.find_one({"email": email})

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    token = jwt.encode(
        {
            "user_id": str(user["_id"]),
            "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
        },
        app.config["SECRET_KEY"],
        algorithm="HS256"
    )

    return jsonify({
        "message": "Logged in successfully",
        "token": token,
        "user": {
            "name": user["name"],
            "email": user["email"]
        }
    })


@app.route("/api/auth/me", methods=["GET"])
@token_required
def get_me(current_user):
    return jsonify({
        "name": current_user["name"],
        "email": current_user["email"],
        "dogName": current_user.get("dogName", ""),
        "dogBreed": current_user.get("dogBreed", ""),
        "dogAge": current_user.get("dogAge", "")
    })


@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json() or {}
    email = data.get("email", "").strip().lower()

    user = users_collection.find_one({"email": email})

    if user:
        reset_token = secrets.token_urlsafe(32)

        users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "resetPasswordToken": reset_token,
                    "resetPasswordExpires": datetime.datetime.utcnow()
                    + datetime.timedelta(hours=1)
                }
            }
        )

        print(
            f"\n🔑 DEVELOPMENT RESET LINK FOR {email}: "
            f"http://localhost:5000/reset-password/{reset_token}\n"
        )

    return jsonify({
        "message": "If this email exists, a reset link will be sent."
    })


@app.route("/api/auth/reset-password/<token>", methods=["POST"])
def reset_password(token):
    data = request.get_json() or {}
    new_password = data.get("password", "")

    if not new_password or len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    user = users_collection.find_one({
        "resetPasswordToken": token,
        "resetPasswordExpires": {"$gt": datetime.datetime.utcnow()}
    })

    if not user:
        return jsonify({"error": "Invalid or expired reset token"}), 400

    hashed_password = generate_password_hash(new_password)

    users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_hash": hashed_password,
                "updatedAt": datetime.datetime.utcnow()
            },
            "$unset": {
                "resetPasswordToken": 1,
                "resetPasswordExpires": 1
            }
        }
    )

    return jsonify({"message": "Password has been reset successfully"})


# -------------------------------------------------------------
# API Chat Routes
# -------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
@token_required
def chat(current_user):
    try:
        data = request.get_json() or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        prompt = f"""
You are a Dog Care Assistant.
Only answer dog care related questions.
If question is unrelated, politely refuse.

User: {user_message}
"""

        response = ai_client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt
        )

        bot_reply = response.text

        chat_history_collection.insert_one({
            "userId": str(current_user["_id"]),
            "userMessage": user_message,
            "botReply": bot_reply,
            "createdAt": datetime.datetime.utcnow()
        })

        return jsonify({"response": bot_reply})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": "Server error occurred."}), 500


@app.route("/api/chat/history", methods=["GET"])
@token_required
def get_chat_history(current_user):
    history_cursor = chat_history_collection.find(
        {"userId": str(current_user["_id"])},
        {
            "_id": 0,
            "userMessage": 1,
            "botReply": 1,
            "createdAt": 1
        }
    ).sort("createdAt", 1)

    history = list(history_cursor)

    return jsonify(history)


# -------------------------------------------------------------
# Run App
# -------------------------------------------------------------
# if __name__ == "__main__":
#     app.run(debug=True, use_reloader=False)




if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
