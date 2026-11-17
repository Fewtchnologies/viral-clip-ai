import time
from google import genai
from backend.config import GEMINI_API_KEY
client = genai.Client(api_key=GEMINI_API_KEY)

for model in ["gemini-3.8-flash", "gemini-2.5-pro", "gemini-3.5-flash-lite"]:
    try:
        res = client.models.generate_content(model=model, contents="Say hi")
        print(f"Model {model}: SUCCESS -> {res.text.strip()}", flush=True)
        break
    except Exception as e:
        print(f"Model {model}: FAILED -> {e}", flush=True)
