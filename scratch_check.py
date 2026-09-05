import urllib.request
import json
import os
import toml

secrets_path = os.path.join(".streamlit", "secrets.toml")
with open(secrets_path, "r", encoding="utf-8") as f:
    secrets = toml.load(f)

API_KEY = secrets.get("OPENROUTER_API_KEY")

url = "https://openrouter.ai/api/v1/models"
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
try:
    response = urllib.request.urlopen(req)
    data = json.loads(response.read().decode('utf-8'))
    gemini_models = [m['id'] for m in data['data'] if 'gemini' in m['id'].lower()]
    print("Available Gemini Models:", gemini_models)
except Exception as e:
    print("Error:", e)
