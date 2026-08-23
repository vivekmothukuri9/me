import time
import json
import random
import urllib.parse
import urllib.request
import os
import toml
from datetime import datetime, timedelta, timezone
from openai import OpenAI
from supabase import create_client, Client

# Load configuration from Streamlit secrets (if available locally)
def load_secrets():
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8") as f:
            return toml.load(f)
    return {}

secrets = load_secrets()
TELEGRAM_BOT_TOKEN = secrets.get("TELEGRAM_BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN"))
TELEGRAM_CHAT_ID = secrets.get("TELEGRAM_CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID"))
OPENROUTER_API_KEY = secrets.get("OPENROUTER_API_KEY", os.environ.get("OPENROUTER_API_KEY"))
SUPABASE_URL = secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL"))
SUPABASE_KEY = secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY"))

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not OPENROUTER_API_KEY or not SUPABASE_URL:
    print("Error: Missing API keys in .streamlit/secrets.toml or environment variables.")
    exit(1)

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_ist_now():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5, minutes=30)

def send_telegram_message(text, bot_name):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({'chat_id': TELEGRAM_CHAT_ID, 'text': f"💖 {bot_name}:\n\n{text}"}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
        print(f"Sent message: {text}")
    except Exception as e:
        print("Telegram error:", e)

def get_app_state():
    try:
        response = supabase.table("app_state").select("data").eq("id", "singleton").execute()
        if response.data and len(response.data) > 0:
            return response.data[0]["data"]
    except Exception as e:
        print("Error fetching state:", e)
    return {}

def save_app_state(data):
    try:
        supabase.table("app_state").upsert({"id": "singleton", "data": data}).execute()
    except Exception as e:
        print("Error saving state:", e)

def get_current_session(app_state):
    sessions = app_state.get("sessions", {})
    if not sessions:
        return None, None
    latest_session_id = max(sessions.keys(), key=lambda k: sessions[k].get("updated_at", ""))
    return latest_session_id, sessions[latest_session_id]

def generate_ai_response(prompt_text, recent_messages):
    messages = [{"role": "system", "content": prompt_text}]
    # Add context from app history
    for msg in recent_messages[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    try:
        response = client.chat.completions.create(
            model="google/gemma-4-26b-a4b-it", # same openrouter model as the app
            messages=messages,
            stream=False
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("OpenRouter error:", e)
        return "Sorry ra, edho technical issue vachindi."

def get_system_prompt(state, period, intent="proactive", user_text=""):
    settings = state.get("settings", {})
    u_name = settings.get("user_name", "Vivek")
    a_name = settings.get("ai_name", "Nithya")
    
    now = get_ist_now()
    prompt = f"""You are {a_name}, a caring and slightly teasing female companion (college friend) of {u_name}.
    CURRENT TIME: {now.strftime("%I:%M %p")}
    
    """
    if intent == "proactive":
        prompt += f"""Your task is to send a random, spontaneous check-in text on Telegram.
        CONTEXT: {period}
        """
    else:
        prompt += f"""{u_name} just messaged you this on Telegram: "{user_text}"
        Your task is to reply naturally to his message.
        """
        
    prompt += f"""
    RULES:
    - Strictly use Tanglish (Telugu in English script). No pure English or Telugu script.
    - Be completely natural, keep it very short (1-2 sentences). 
    - Act like a real person messaging on WhatsApp/Telegram. Do not use emojis in every message.
    - Since this is Telegram and you usually chat on the companion App, you can subtly ask him to open the App if he wants to chat more or play games.
    - Generate EXACTLY ONE message. Do not mention this prompt.
    """
    return prompt, a_name

def get_telegram_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?timeout=30"
    if offset:
        url += f"&offset={offset}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=35) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data.get("result", [])
    except Exception as e:
        print("Error fetching updates:", e)
        return []

def main_loop():
    print("Background Bot is starting with Supabase integration...")
    last_update_id = None
    
    state = get_app_state()
    settings = state.get("settings", {})
    a_name = settings.get("ai_name", "Nithya")
    
    send_telegram_message("Hey, I'm online in the background now! ✨", a_name)
    last_proactive_time = get_ist_now()
    
    while True:
        try:
            state = get_app_state()
            session_id, session_data = get_current_session(state)
            recent_messages = session_data.get("messages", []) if session_data else []
            settings = state.get("settings", {})
            a_name = settings.get("ai_name", "Nithya")
            
            # 1. Handle incoming messages (Polling)
            updates = get_telegram_updates(offset=last_update_id)
            for update in updates:
                last_update_id = update["update_id"] + 1
                message = update.get("message", {})
                
                if str(message.get("chat", {}).get("id")) == str(TELEGRAM_CHAT_ID):
                    text = message.get("text")
                    if text and text != "/start":
                        print(f"Received message: {text}")
                        
                        # Add user msg to db
                        if session_data:
                            new_user_msg = {"role": "user", "content": text, "timestamp": get_ist_now().strftime("%I:%M %p")}
                            session_data["messages"].append(new_user_msg)
                            state["sessions"][session_id] = session_data
                            state["interactions_count"] = state.get("interactions_count", 0) + 1
                            save_app_state(state)
                        
                        prompt, ai_name = get_system_prompt(state, "", intent="reply", user_text=text)
                        reply = generate_ai_response(prompt, recent_messages)
                        send_telegram_message(reply, ai_name)
                        
                        # Add ai msg to db
                        if session_data:
                            new_ai_msg = {"role": "assistant", "content": reply, "timestamp": get_ist_now().strftime("%I:%M %p")}
                            session_data["messages"].append(new_ai_msg)
                            session_data["updated_at"] = get_ist_now().isoformat()
                            state["sessions"][session_id] = session_data
                            save_app_state(state)
                            
                        last_proactive_time = get_ist_now()
            
            # 2. Handle proactive messages
            time_since_last = (get_ist_now() - last_proactive_time).total_seconds()
            
            if time_since_last > random.uniform(10800, 18000):
                print("Sending proactive message...")
                now = get_ist_now()
                hour = now.hour
                if 5 <= hour < 12: period = "Morning. Greet them good morning."
                elif 12 <= hour < 17: period = "Afternoon. Ask about lunch or work."
                elif 17 <= hour < 21: period = "Evening. Ask about evening plans."
                else: period = "Night. Ask why they are still awake."
                
                prompt, ai_name = get_system_prompt(state, period, intent="proactive")
                reply = generate_ai_response(prompt, recent_messages)
                send_telegram_message(reply, ai_name)
                
                # Add proactive msg to db
                if session_data:
                    new_ai_msg = {"role": "assistant", "content": reply, "timestamp": get_ist_now().strftime("%I:%M %p")}
                    session_data["messages"].append(new_ai_msg)
                    session_data["updated_at"] = get_ist_now().isoformat()
                    state["sessions"][session_id] = session_data
                    save_app_state(state)
                    
                last_proactive_time = get_ist_now()
                
            time.sleep(2)
            
        except Exception as e:
            print("Error in main loop:", e)
            time.sleep(10)

if __name__ == "__main__":
    main_loop()
