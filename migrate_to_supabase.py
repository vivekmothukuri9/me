import json
import os
import toml
from supabase import create_client, Client

def load_secrets():
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8") as f:
            return toml.load(f)
    return {}

secrets = load_secrets()
url: str = secrets.get("SUPABASE_URL")
key: str = secrets.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

if os.path.exists("chat_history.json"):
    with open("chat_history.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    try:
        response = supabase.table("app_state").upsert({"id": "singleton", "data": data}).execute()
        print("Successfully migrated chat_history.json to Supabase!")
    except Exception as e:
        print(f"Failed to migrate: {e}")
else:
    print("No chat_history.json found to migrate.")
