import os
from dotenv import load_dotenv
from google import genai

# Force load .env from current project folder
load_dotenv(dotenv_path=".env", override=True)

api_key = os.environ.get("AIzaSyBgNpfEIrZhYJ0jHEIC_R-IsrxqhUoXd6I")

if not api_key:
    print("GEMINI_API_KEY is missing. Please add it to .env")
    exit(1)

print("Gemini API key loaded: YES")
print("Key starts with:", api_key[:10])
print("Key ends with:", api_key[-6:])

client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents="Say hello in one short sentence."
    )

    print("✅ API WORKING!")
    print(response.text)

except Exception as e:
    print("❌ API ERROR:")
    print(e)