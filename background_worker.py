import os
import toml
import time
import random
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from supabase import create_client
from openai import OpenAI

def load_secrets():
    secrets_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        with open(secrets_path, "r", encoding="utf-8") as f:
            return toml.load(f)
    return {}

def get_ist_now():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5, minutes=30)

def send_telegram_notification(message_text, bot_name, bot_token, chat_id):
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({'chat_id': chat_id, 'text': f"💖 {bot_name}:\n\n{message_text}"}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
        print("Telegram notification sent.")
    except Exception as e:
        print("Telegram error:", e)

def main():
    print("Starting Background Proactive Worker...")
    secrets = load_secrets()
    url = secrets.get("SUPABASE_URL")
    key = secrets.get("SUPABASE_KEY")
    bot_token = secrets.get("TELEGRAM_BOT_TOKEN")
    chat_id = secrets.get("TELEGRAM_CHAT_ID")
    openrouter_key = secrets.get("OPENROUTER_API_KEY")

    if not all([url, key, bot_token, chat_id, openrouter_key]):
        print("Missing required secrets. Exiting.")
        return

    supabase = create_client(url, key)
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=openrouter_key)

    while True:
        try:
            print(f"[{get_ist_now().strftime('%H:%M:%S')}] Checking for idle sessions...")
            response = supabase.table("app_state").select("data").eq("id", "singleton").execute()
            if not response.data:
                time.sleep(600)
                continue

            app_state = response.data[0]["data"]
            sessions = app_state.get("sessions", {})
            if not sessions:
                time.sleep(600)
                continue

            # Find the most recently updated session
            latest_session_id = max(sessions.keys(), key=lambda k: sessions[k].get("updated_at", ""))
            session = sessions[latest_session_id]
            messages = session.get("messages", [])

            if not messages:
                time.sleep(600)
                continue

            # Check if last message was from user or AI, it doesn't matter, just check idle time
            try:
                last_updated = datetime.fromisoformat(session.get("updated_at", get_ist_now().isoformat()))
            except ValueError:
                last_updated = get_ist_now()

            idle_minutes = (get_ist_now() - last_updated).total_seconds() / 60.0

            # Only trigger if idle for more than 60 minutes
            if idle_minutes > 60:
                now = get_ist_now()
                # Don't text too much between 1 AM and 7 AM unless very lucky
                if 1 <= now.hour < 7:
                    prob = 0.05
                else:
                    prob = 0.3 # 30% chance every 10 minutes after 1 hour idle

                if random.random() < prob:
                    print("Triggering proactive message!")
                    settings = app_state.get("settings", {})
                    u_name = settings.get("user_name", "Vivek")
                    a_name = settings.get("ai_name", "Nithya")
                    
                    if 5 <= now.hour < 12: period = "Morning"
                    elif 12 <= now.hour < 17: period = "Afternoon"
                    elif 17 <= now.hour < 21: period = "Evening"
                    else: period = "Night"
                    
                    time_context = "Ask how their day is going or what they are doing."
                    if period == "Morning":
                        time_context = "Say good morning, ask if they woke up, or how they slept."
                    elif period == "Night":
                        time_context = "Say goodnight, or ask why they are not sleeping yet."

                    special_prompt = f"Act as {a_name}, {u_name}'s loving partner. You haven't talked in over an hour. Based on the PREVIOUS CONVERSATION HISTORY and the current time ({now.strftime('%I:%M %p')}), generate a completely natural, spontaneous check-in text in Tanglish. {time_context} MAXIMUM LENGTH: 5 to 10 words. NEVER write paragraphs. Send EXACTLY ONE short message."
                    
                    # Prepare messages payload
                    messages_payload = [{"role": "system", "content": "You are a real person texting on WhatsApp. Keep texts short, natural, in Tanglish. DO NOT ACT LIKE AN AI."}]
                    # include last 5 messages for context
                    for m in messages[-5:]:
                        messages_payload.append({"role": m["role"], "content": m["content"]})
                    messages_payload.append({"role": "user", "content": special_prompt})

                    ai_res = client.chat.completions.create(
                        model="google/gemini-1.5-flash",
                        messages=messages_payload,
                        stream=False
                    )
                    
                    import re
                    full_response = ai_res.choices[0].message.content.strip()
                    full_response = re.sub(r'\n+', '|||', full_response)
                    generated_msgs = [m.strip() for m in full_response.split("|||") if m.strip() and len(m.strip()) > 1]
                    
                    for text in generated_msgs:
                        new_msg = {"role": "assistant", "content": text, "timestamp": get_ist_now().strftime("%I:%M %p")}
                        session["messages"].append(new_msg)
                        send_telegram_notification(text, a_name, bot_token, chat_id)
                        time.sleep(1) # small delay if multiple

                    session["updated_at"] = get_ist_now().isoformat()
                    app_state["interactions_count"] = app_state.get("interactions_count", 0) + 1
                    
                    supabase.table("app_state").upsert({"id": "singleton", "data": app_state}).execute()
                    print("Proactive message sent and state updated.")

        except Exception as e:
            print("Error in background loop:", e)

        # Sleep for 10 minutes before checking again
        time.sleep(600)

if __name__ == "__main__":
    main()
