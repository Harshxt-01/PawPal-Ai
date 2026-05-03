import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from google import genai
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# 🔐 Use your valid API key
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "")

        prompt = f"""
You are a Dog Care Assistant.
Only answer dog care related questions.
If question is unrelated, politely refuse.

User: {user_message}
"""

        response = client.models.generate_content(
            model="models/gemini-2.5-flash",   # ✅ FIXED MODEL
            contents=prompt
        )

        return jsonify({"response": response.text})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"response": "Server error occurred."})

if __name__ == "__main__":
    app.run(debug=True)