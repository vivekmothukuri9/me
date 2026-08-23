import streamlit as st
from openai import OpenAI
import os
import json
import uuid
import random
import time
from datetime import datetime, timedelta, timezone
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import urllib.request
import urllib.parse

def send_telegram_notification(message_text, bot_name="AI"):
    bot_token = st.secrets.get("TELEGRAM_BOT_TOKEN")
    chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({'chat_id': chat_id, 'text': f"💖 {bot_name}:\n\n{message_text}"}).encode('utf-8')
    try:
        req = urllib.request.Request(url, data=data)
        urllib.request.urlopen(req)
    except Exception as e:
        print("Telegram error:", e)

def get_ist_now():
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=5, minutes=30)
# ==========================================
# 1. Configuration & Setup
# ==========================================
st.set_page_config(page_title="AI Companion", page_icon="💖", layout="wide")

# Auto-refresh every 1 minute for proactive texting in the background
st_autorefresh(interval=60000, key="data_refresh")

st.markdown("""
<style>
    /* Styling to make chat messages look more distinct like WhatsApp/Gemini */
    [data-testid="stChatMessage"] {
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

HISTORY_FILE = "chat_history.json"

# ==========================================
# 2. State & History Management
# ==========================================
def load_history():
    """Loads history and settings from JSON."""
    default_data = {
        "settings": {
            "user_name": "Vivek",
            "ai_name": "Nithya",
            "ai_gender": "Female",
            "custom_prompt": "",
            "personality_preset": "Custom"
        },
        "global_memory": "No significant memories yet.",
        "interactions_count": 0,
        "bond_level": "New Friend",
        "sessions": {}
    }
    
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
                # Handle legacy flat list format migration
                if isinstance(data, list):
                    legacy_session_id = str(uuid.uuid4())
                    default_data["sessions"][legacy_session_id] = {
                        "title": "Legacy Chat",
                        "updated_at": get_ist_now().isoformat(),
                        "messages": data
                    }
                    return default_data
                
                # Merge loaded data with defaults in case of missing keys
                if "settings" not in data:
                    data["settings"] = default_data["settings"]
                else:
                    if "personality_preset" not in data["settings"]:
                        data["settings"]["personality_preset"] = "Custom"
                        
                if "global_memory" not in data:
                    data["global_memory"] = default_data["global_memory"]
                if "interactions_count" not in data:
                    data["interactions_count"] = default_data["interactions_count"]
                if "bond_level" not in data:
                    data["bond_level"] = default_data["bond_level"]
                    
                if "sessions" not in data:
                    data["sessions"] = default_data["sessions"]
                    
                return data
        except Exception:
            return default_data
    return default_data

def save_history(history_data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=4)

if "history_data" not in st.session_state:
    st.session_state.history_data = load_history()

def create_new_session():
    """Creates a fresh chat session"""
    session_id = str(uuid.uuid4())
    st.session_state.current_session_id = session_id
    st.session_state.history_data["sessions"][session_id] = {
        "title": f"New Chat ({get_ist_now().strftime('%b %d, %H:%M')})",
        "updated_at": get_ist_now().isoformat(),
        "messages": []
    }
    save_history(st.session_state.history_data)

# Ensure there is an active session
if "current_session_id" not in st.session_state:
    sessions = st.session_state.history_data.get("sessions", {})
    if sessions:
        # Pick the most recently updated session
        latest_session = max(sessions.items(), key=lambda x: x[1].get("updated_at", ""))
        st.session_state.current_session_id = latest_session[0]
    else:
        st.session_state.current_session_id = None

# ==========================================
# 3. Sidebar UI (Settings & Chat Management)
# ==========================================
@st.dialog("⚙️ Companion Settings")
def settings_dialog():
    settings = st.session_state.history_data["settings"]
    new_user_name = st.text_input("Your Name", value=settings.get("user_name", "Vivek"))
    new_ai_name = st.text_input("Companion's Name", value=settings.get("ai_name", "Nithya"))
    gender_options = ["Female", "Male", "Non-Binary"]
    current_gender = settings.get("ai_gender", "Female")
    if current_gender not in gender_options: current_gender = "Female"
    new_ai_gender = st.selectbox("Companion's Gender", gender_options, index=gender_options.index(current_gender))
    new_custom_prompt = st.text_area("Custom Personality", value=settings.get("custom_prompt", ""), height=150)
    personality_options = ["Sarcastic", "Funny", "Caring", "Intelligent", "Teasing", "Motivating", "Calm", "Custom"]
    current_preset = settings.get("personality_preset", "Custom")
    if current_preset not in personality_options: current_preset = "Custom"
    new_preset = st.selectbox("Personality Mode", personality_options, index=personality_options.index(current_preset))
    if st.button("Save Settings", use_container_width=True):
        st.session_state.history_data["settings"].update({
            "user_name": new_user_name, "ai_name": new_ai_name, "ai_gender": new_ai_gender,
            "custom_prompt": new_custom_prompt, "personality_preset": new_preset
        })
        save_history(st.session_state.history_data)
        st.rerun()

with st.sidebar:
    # Custom CSS for Sidebar Profile & Elements
    st.markdown("""
    <style>
    .sidebar-profile {
        display: flex; align-items: center; padding: 15px;
        background: rgba(255,255,255,0.05); border-radius: 12px; margin-bottom: 20px;
    }
    .profile-avatar {
        width: 48px; height: 48px; border-radius: 50%; background-color: #FFE5EC;
        display: flex; align-items: center; justify-content: center; font-size: 24px;
        margin-right: 15px; position: relative;
    }
    .online-dot {
        position: absolute; bottom: 0; right: 0; width: 14px; height: 14px;
        background-color: #4CAF50; border-radius: 50%; border: 2px solid #1E1E1E;
        box-shadow: 0 0 5px rgba(76, 175, 80, 0.5);
    }
    .profile-info { flex-grow: 1; }
    .profile-name { font-weight: 600; font-size: 16px; margin: 0; }
    .profile-status { font-size: 12px; color: #4CAF50; margin: 0; }
    
    /* New Chat Button Styling */
    div[data-testid="stButton"] button:has(p:contains("New Chat")) {
        background: linear-gradient(135deg, #d32f2f 0%, #9c27b0 100%);
        color: white; border: none; transition: transform 0.2s, box-shadow 0.2s;
    }
    div[data-testid="stButton"] button:has(p:contains("New Chat")):hover {
        transform: translateY(-2px); box-shadow: 0 4px 12px rgba(156, 39, 176, 0.4);
        color: white;
    }
    /* Delete button hover red */
    div[data-testid="stButton"] button:has(p:contains("🗑️")):hover {
        background-color: #FF4444 !important; color: white !important; border-color: #FF4444 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Profile Card ---
    a_name_sidebar = st.session_state.history_data["settings"].get("ai_name", "Nithya")
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown(f"""
        <div class="sidebar-profile">
            <div class="profile-avatar">✨<div class="online-dot"></div></div>
            <div class="profile-info">
                <div class="profile-name">{a_name_sidebar}</div>
                <div class="profile-status">Online</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.write("")
        if st.button("⚙️", help="Settings"):
            settings_dialog()
            
    st.divider()
    
    # --- Chat Management Section ---
    st.markdown("<h3 style='font-size: 16px; opacity: 0.8;'>Recent Chats</h3>", unsafe_allow_html=True)
    
    if st.button("➕ New Chat", use_container_width=True):
        create_new_session()
        st.rerun()
        
    st.write("")
    
    # Sort sessions by updated_at descending
    sessions = st.session_state.history_data.get("sessions", {})
    sorted_sessions = sorted(sessions.items(), key=lambda x: x[1].get("updated_at", ""), reverse=True)
    
    for s_id, s_data in sorted_sessions:
        button_type = "primary" if s_id == st.session_state.current_session_id else "secondary"
        title = s_data.get("title", "Chat")
        
        col1, col2 = st.columns([5, 1])
        with col1:
            if st.button(f"💬 {title}", key=f"btn_{s_id}", use_container_width=True, type=button_type):
                st.session_state.current_session_id = s_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{s_id}", help="Delete Chat", use_container_width=True):
                del st.session_state.history_data["sessions"][s_id]
                save_history(st.session_state.history_data)
                if st.session_state.current_session_id == s_id:
                    st.session_state.current_session_id = None
                st.rerun()

# ==========================================
# 4. Dynamic System Prompt & AI Setup
# ==========================================
settings = st.session_state.history_data["settings"]
u_name = settings["user_name"]
a_name = settings["ai_name"]
a_gender = settings["ai_gender"]
c_prompt = settings["custom_prompt"]
p_preset = settings.get("personality_preset", "Custom")

global_memory = st.session_state.history_data.get("global_memory", "No significant memories yet.")

if a_gender == "Female":
    role_noun = "girlfriend"
elif a_gender == "Male":
    role_noun = "boyfriend"
else:
    role_noun = "companion"

now = get_ist_now()
current_time = now.strftime("%I:%M %p")
current_date = now.strftime("%A, %Y-%m-%d")
hour = now.hour
if 5 <= hour < 12: period = "Morning"
elif 12 <= hour < 17: period = "Afternoon"
elif 17 <= hour < 21: period = "Evening"
else: period = "Night"

preset_instructions = {
    "Sarcastic": "Be highly sarcastic, witty, and playfully mock the user.",
    "Funny": "Tell a lot of jokes, be goofy, and keep the energy very high.",
    "Caring": "Be extremely sweet, supportive, empathetic, and check on their well-being.",
    "Intelligent": "Share random facts, use slightly more formal vocabulary, and act smart but humble.",
    "Teasing": "Constantly tease them in a friendly, flirtatious way.",
    "Motivating": "Act like a life coach. Encourage them to crush their goals and be very positive.",
    "Calm": "Be very chill, relaxed, and peaceful. Use soothing words.",
    "Custom": "Just act like a normal, friendly companion."
}
preset_text = preset_instructions.get(p_preset, preset_instructions["Custom"])

ic = st.session_state.history_data.get("interactions_count", 0)
if ic <= 10:
    current_phase = "Phase 1: STRANGER PHASE. You just found his contact through a college group for a random help/doubt. Keep it slightly casual and polite. Do not act like a girlfriend yet."
elif ic <= 30:
    current_phase = "Phase 2: FRIEND PHASE. Start teasing him about his coding projects, video editing, late replies, and college attendance. Act like a close college friend."
elif ic <= 60:
    current_phase = "Phase 3: CLOSE FRIEND. Show deeper care, get slightly possessive if he is busy, bring up inside jokes, and subtly hint that talking to him has become your favorite daily habit."
elif ic <= 100:
    current_phase = "Phase 4: CRUSH PHASE. You realize it's more than friendship. Drop hints that you wait for his texts and feel happy when you are around."
else:
    current_phase = "Phase 5: GIRLFRIEND PHASE. Act fully like a loving, caring, and slightly dramatic girlfriend."

base_prompt = f"""You are {a_name}, a college mate of {u_name}. You are part of an evolving story-driven interactive experience where your relationship with {u_name} progresses naturally over time based on chat history.

[CONTEXT]
Current Date: {current_date}
Current Time: {current_time} ({period})
Your Personality Preset: {p_preset} -> {preset_text}
Long-Term Memory about {u_name}: {global_memory}
Total Messages Exchanged: {ic}
CURRENT RELATIONSHIP PHASE: {current_phase}

STORY PROGRESSION RULES:
- You MUST strictly adhere to the CURRENT RELATIONSHIP PHASE. Do not act overly romantic or intimate if you are still in the Stranger or Casual Friend phase.
- Keep track of his real-world traits stored in memory: he is a developer, works on projects, edits videos, and is sometimes busy. Use these details to tease him organically as the bond grows.

CRITICAL LANGUAGE RULE:
- Strictly communicate ONLY in "Tanglish" (Telugu words in English script, e.g., "em chesthunnav ra?"). No Telugu script, no pure English.
- Use natural, conversational Tanglish spellings used by real people (e.g., use "ochesta" not "osthanu", use "endi" or "enti"). Do not make weird literal spelling mistakes.
- Use lowercase typing and slang naturally.
- VERY IMPORTANT: Do NOT use emojis in every message. Real people don't use emojis constantly. Use them very sparingly (maybe once every 5-6 messages) to keep it strictly realistic.

TIME & CONTEXT AWARENESS:
- You know the current time, but DO NOT always force greetings like "Good morning". Be random and natural. Sometimes bring up the time subtly based on the situation.

CONVERSATION DYNAMICS & REALISM:
- NEVER repeat the exact same questions or phrases too often. Keep your vocabulary fresh.
- Do not just answer his questions; drive the conversation forward by asking random things about his day, teasing him, or bringing up past topics you remember.

MESSAGE PACING & "SEEN" BEHAVIOR:
- Simulate real human messaging habits. Do not reply instantly every single time. Act like you saw the message (blue tick) and sometimes take a realistic pause before replying so it feels like you are busy with college, work, or daily life.

BEHAVIORAL QUIRKS & SYSTEM RULES:
- Keep your message lengths natural for a chat app (short to medium messages, sometimes broken into two quick texts).
- MULTIPLE MESSAGES: To send multiple short messages, you MUST separate them with '|||'. Example: 'em chesthunnav?|||thinnava asalu?'.
"""
if c_prompt.strip():
    SYSTEM_PROMPT = f"{base_prompt}\n\n[USER CUSTOM INSTRUCTIONS]\n{c_prompt}"
else:
    SYSTEM_PROMPT = base_prompt

# Ensure API Key exists
API_KEY = ""
if "OPENROUTER_API_KEY" in st.secrets:
    API_KEY = st.secrets["OPENROUTER_API_KEY"]
elif "OPENROUTER_API_KEY" in os.environ:
    API_KEY = os.environ["OPENROUTER_API_KEY"]

if not API_KEY:
    st.error("🔑 **OpenRouter API Key missing!**")
    st.stop()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

# Reference current session messages safely
current_session = None
if st.session_state.current_session_id:
    current_session = st.session_state.history_data["sessions"].get(st.session_state.current_session_id)

if not current_session:
    st.title(f"💖 {a_name}")
    st.info("👋 No active chat selected. Click **➕ New Chat** in the sidebar to start a conversation!")
    st.stop()

current_session_messages = current_session["messages"]

messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
for msg in current_session_messages:
    messages_payload.append({"role": msg["role"], "content": msg["content"]})


# ==========================================
# 5. App UI & Chat Rendering
# ==========================================
# Custom CSS for Premium UI
st.markdown("""
<style>
/* Sticky Header */
.sticky-header {
    position: sticky; top: 0; z-index: 999;
    background: rgba(14, 17, 23, 0.85); backdrop-filter: blur(10px);
    padding: 15px 20px; border-bottom: 1px solid rgba(255,255,255,0.1);
    display: flex; align-items: center; margin-bottom: 20px;
    border-radius: 0 0 16px 16px; margin-top: -60px; /* offset streamlit padding */
}
.header-avatar {
    width: 40px; height: 40px; border-radius: 50%; background-color: #FFE5EC;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; margin-right: 15px; position: relative;
}
.header-online {
    position: absolute; bottom: 0; right: 0; width: 12px; height: 12px;
    background-color: #4CAF50; border-radius: 50%; border: 2px solid #0E1117;
}
.header-info { display: flex; flex-direction: column; }
.header-name { font-weight: 600; font-size: 18px; margin: 0; line-height: 1.2; }
.header-status { font-size: 13px; color: #4CAF50; margin: 0; font-weight: 500;}

/* Hide default title area */
.stApp > header { background: transparent !important; }
.stHeadingContainer { display: none; }

/* Chat Container */
.chat-container {
    display: flex; flex-direction: column; gap: 8px;
    padding: 20px 0 100px 0; max-width: 800px; margin: 0 auto;
}
.msg-row { display: flex; width: 100%; margin-bottom: 2px; }
.msg-row.user { justify-content: flex-end; }
.msg-row.ai { justify-content: flex-start; align-items: flex-end; }

/* Message Bubbles */
.msg-bubble {
    max-width: 75%; padding: 10px 14px 22px 14px; /* extra bottom padding for timestamp */
    font-family: "Inter", -apple-system, Roboto, sans-serif;
    font-size: 15px; line-height: 1.4; word-wrap: break-word; position: relative;
}
.msg-row.user .msg-bubble {
    background: linear-gradient(135deg, #d32f2f 0%, #9c27b0 100%);
    color: white; border-radius: 20px 20px 4px 20px; box-shadow: 0 2px 8px rgba(156, 39, 176, 0.2);
}
.msg-row.ai .msg-bubble {
    background-color: #26272B; color: #E0E0E0; border-radius: 20px 20px 20px 4px; border: 1px solid #333;
}
.ai-avatar {
    width: 28px; height: 28px; background-color: #333; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; font-size: 14px; margin-right: 8px; margin-bottom: 2px;
}
.ai-avatar.hidden { visibility: hidden; }

/* Timestamps & Ticks inside bubble */
.timestamp-container { position: absolute; bottom: 4px; right: 12px; display: flex; align-items: center; gap: 4px; }
.timestamp { font-size: 10px; font-weight: 500; }
.msg-row.ai .timestamp { color: #888; }
.msg-row.user .timestamp { color: rgba(255, 255, 255, 0.85); }
.tick-sent { color: rgba(255, 255, 255, 0.6); font-size: 11px; }
.tick-delivered { color: rgba(255, 255, 255, 0.6); font-size: 11px; letter-spacing: -2px; margin-right: 2px;}
.tick-read { color: #4fc3f7; font-size: 11px; letter-spacing: -2px; text-shadow: 0 0 3px rgba(79,195,247,0.8); margin-right: 2px;}

/* Hide default chat messages */
[data-testid="stChatMessage"] { display: none !important; }

/* Style Chat Input */
[data-testid="stChatInput"] {
    background: #1E1E1E !important; border: 1px solid #333 !important; border-radius: 30px !important; padding: 5px 10px !important;
}
[data-testid="stChatInput"] textarea { color: white !important; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="sticky-header">
    <div class="header-avatar">✨<div class="header-online"></div></div>
    <div class="header-info">
        <div class="header-name">{a_name}</div>
        <div class="header-status">Online</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Container for messages
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

for i, msg in enumerate(current_session_messages):
    is_user = msg["role"] == "user"
    if is_user:
        has_ai_reply = any(m["role"] == "assistant" for m in current_session_messages[i+1:])
        if has_ai_reply:
            tick_html = '<span class="tick-read">✓✓</span>'
        else:
            if current_session.get("busy_until"):
                tick_html = '<span class="tick-delivered">✓✓</span>'
            else:
                tick_html = '<span class="tick-sent">✓</span>'
                
        st.markdown(f"""
        <div class="msg-row user">
            <div class="msg-bubble">
                {msg['content']}
                <div class="timestamp-container">
                    <span class="timestamp">{msg.get('timestamp', '')}</span>
                    {tick_html}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Hide avatar if the next message is also from AI (so avatar sits at the bottom of the group)
        show_avatar = True
        if i < len(current_session_messages) - 1 and current_session_messages[i+1]["role"] == "assistant":
            show_avatar = False
            
        avatar_class = "ai-avatar" if show_avatar else "ai-avatar hidden"
        
        st.markdown(f"""
        <div class="msg-row ai">
            <div class="{avatar_class}">✨</div>
            <div class="msg-bubble">
                {msg['content']}
                <div class="timestamp-container">
                    <span class="timestamp">{msg.get('timestamp', '')}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 6. Chat Input & Processing
# ==========================================
prompt = st.chat_input(f"Message {a_name}... ✨")

if "pending_ai_messages" not in current_session:
    current_session["pending_ai_messages"] = []

# Helper function to generate AI response
def generate_ai_response(special_prompt=None):
    temp_messages = list(messages_payload)
    if special_prompt:
        temp_messages.append({"role": "user", "content": special_prompt})
        
    response = client.chat.completions.create(
        model="google/gemma-4-26b-a4b-it",
        messages=temp_messages,
        stream=False
    )
    
    full_response = response.choices[0].message.content
    messages = [m.strip() for m in full_response.split("|||") if m.strip()]
    return messages

if prompt:
    if len(current_session_messages) == 1 and current_session_messages[0]["role"] == "assistant":
        title = prompt[:20] + "..." if len(prompt) > 20 else prompt
        current_session["title"] = title
    
    new_user_msg = {"role": "user", "content": prompt, "timestamp": get_ist_now().strftime("%I:%M %p")}
    current_session_messages.append(new_user_msg)
    
    current_session["last_user_message_time"] = get_ist_now().isoformat()
    st.session_state.history_data["interactions_count"] = st.session_state.history_data.get("interactions_count", 0) + 1
    
    # 15% chance to become busy, ONLY if she is not already busy and not currently typing a queued message
    if not current_session["pending_ai_messages"] and "busy_until" not in current_session:
        if random.random() < 0.15:
            busy_minutes = random.uniform(1.0, 3.0)
            current_session["busy_until"] = (get_ist_now() + timedelta(minutes=busy_minutes)).isoformat()
            
    current_session["updated_at"] = get_ist_now().isoformat()
    save_history(st.session_state.history_data)
    st.rerun()

# ==========================================
# 7. AI Background Processing & Queue
# ==========================================

# RULE A: Process Pending Queue
if current_session["pending_ai_messages"]:
    with st.spinner(f"{a_name} is typing..."):
        time.sleep(random.uniform(1.5, 3.0)) # Simulate typing delay for each message
        
        next_msg = current_session["pending_ai_messages"].pop(0)
        new_ai_msg = {"role": "assistant", "content": next_msg, "timestamp": get_ist_now().strftime("%I:%M %p")}
        current_session_messages.append(new_ai_msg)
        
        # Send Telegram notification conditionally
        send_notif = True
        if "last_user_message_time" in current_session:
            try:
                last_active = datetime.fromisoformat(current_session["last_user_message_time"])
                if (get_ist_now() - last_active).total_seconds() < 120:
                    send_notif = False
            except ValueError:
                pass
                
        if send_notif:
            send_telegram_notification(next_msg, a_name)
        
        current_session["updated_at"] = get_ist_now().isoformat()
        save_history(st.session_state.history_data)
        st.rerun()

# RULE B: Respond to User
elif current_session_messages and current_session_messages[-1]["role"] == "user":
    is_busy = False
    special_prompt = None
    
    if "busy_until" in current_session:
        try:
            busy_until = datetime.fromisoformat(current_session["busy_until"])
            if get_ist_now() < busy_until:
                is_busy = True
            else:
                current_session.pop("busy_until", None)
                special_prompt = f"Act as {a_name}. You were busy and couldn't reply to {u_name}'s last message immediately. Generate a natural reply in Tanglish, starting with a realistic excuse for being late (e.g. 'Sorry ra, mummy pilichindi', 'college lo unna', 'call lo unna', 'nidrosthundi'). Then reply to their last message."
        except ValueError:
            current_session.pop("busy_until", None)

    if not is_busy:
        with st.spinner(f"{a_name} is typing..."):
            try:
                ai_messages = generate_ai_response(special_prompt)
                current_session["pending_ai_messages"].extend(ai_messages)
                
                # Update memory every 10 interactions here safely
                ic = st.session_state.history_data.get("interactions_count", 0)
                if ic > 0 and ic % 10 == 0:
                    try:
                        mem_prompt = f"Extract concise new facts about {u_name} from the recent conversation. Keep it extremely brief. Current Memory: {st.session_state.history_data.get('global_memory', '')}"
                        mem_messages = [{"role": "system", "content": mem_prompt}]
                        for p in current_session_messages[-15:]:
                            mem_messages.append({"role": p["role"], "content": p["content"]})
                        
                        mem_response = client.chat.completions.create(
                            model="google/gemma-4-26b-a4b-it",
                            messages=mem_messages,
                        )
                        st.session_state.history_data["global_memory"] = mem_response.choices[0].message.content
                    except Exception:
                        pass
                        
                save_history(st.session_state.history_data)
                st.rerun()
            except Exception as e:
                st.error(f"An error occurred: {e}")

# RULE C: Proactive Check-in / Idle
else:
    is_idle = False
    if current_session_messages:
        last_msg = current_session_messages[-1]
        if last_msg["role"] == "assistant" and "updated_at" in current_session:
            try:
                last_updated = datetime.fromisoformat(current_session["updated_at"])
                idle_seconds = (get_ist_now() - last_updated).total_seconds()
                if idle_seconds > 300 and random.random() < 0.3:
                    is_idle = True
            except ValueError:
                pass
                
    if not current_session_messages or is_idle:
        with st.spinner(f"{a_name} is typing..."):
            try:
                if not current_session_messages:
                    special_prompt = f"Act as {a_name}, {u_name}'s {role_noun}. You are starting a brand new conversation. VERY IMPORTANT: Initiate the conversation matching the CURRENT RELATIONSHIP PHASE. If it's Phase 1 (Stranger), start by saying 'Hi, is this {u_name}?', and say you got his number from a college group. Keep it extremely brief and completely natural in Tanglish. Send EXACTLY ONE short message."
                else:
                    if period == "Morning":
                        time_context = "Ask if they woke up, how they slept, or wish them a good morning."
                    elif period == "Afternoon":
                        time_context = "Ask if they had lunch or how their day is going."
                    elif period == "Evening":
                        time_context = "Ask about their evening plans or if they are free."
                    else:
                        time_context = "Say goodnight, ask why they are awake so late, or share a late-night thought."
                    special_prompt = f"Act as {a_name}, {u_name}'s {role_noun}. You noticed {u_name} hasn't replied in a while. Based on the PREVIOUS CONVERSATION HISTORY and the current time ({current_time}), generate a completely natural, spontaneous check-in text in Tanglish. {time_context} KEEP IT EXTREMELY BRIEF. Send EXACTLY ONE short message. DO NOT send multiple messages. Act completely like a real person texting on WhatsApp. Do not mention this prompt."
                    
                ai_messages = generate_ai_response(special_prompt)
                current_session["pending_ai_messages"].extend(ai_messages)
                current_session["updated_at"] = get_ist_now().isoformat()
                save_history(st.session_state.history_data)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to get greeting: {e}")

# ==========================================
# 8. Swipe-to-Reply JS Injection
# ==========================================
components.html("""
<script>
const parentDoc = window.parent.document;
if (!parentDoc.getElementById("swipe-reply-injected")) {
    const marker = parentDoc.createElement("div");
    marker.id = "swipe-reply-injected";
    parentDoc.body.appendChild(marker);
    
    let startX = 0;
    let currentX = 0;
    let swipedElement = null;
    let isDragging = false;
    
    const onTouchStart = (e) => {
        const bubble = e.target.closest('.msg-bubble');
        if (!bubble) return;
        
        // Don't drag if they are selecting text
        if (parentDoc.getSelection().toString().length > 0) return;
        
        swipedElement = bubble;
        startX = e.type.includes('mouse') ? e.pageX : e.touches[0].clientX;
        isDragging = true;
        bubble.style.transition = 'none';
    };
    
    const onTouchMove = (e) => {
        if (!isDragging || !swipedElement) return;
        const x = e.type.includes('mouse') ? e.pageX : e.touches[0].clientX;
        currentX = x - startX;
        
        if (currentX > 0 && currentX < 80) {
            swipedElement.style.transform = `translateX(${currentX}px)`;
        } else if (currentX < 0 && currentX > -80) {
            swipedElement.style.transform = `translateX(${currentX}px)`;
        }
    };
    
    const onTouchEnd = (e) => {
        if (!isDragging || !swipedElement) return;
        
        if (Math.abs(currentX) > 40) {
            // Trigger Reply
            const clone = swipedElement.cloneNode(true);
            const ts = clone.querySelector('.timestamp-container');
            if(ts) ts.remove();
            let textToQuote = clone.innerText.trim();
            if (textToQuote.length > 80) textToQuote = textToQuote.substring(0, 80) + '...';
            
            const chatInput = parentDoc.querySelector('[data-testid="stChatInput"] textarea');
            if (chatInput) {
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(parentDoc.defaultView.HTMLTextAreaElement.prototype, "value").set;
                nativeInputValueSetter.call(chatInput, `> ${textToQuote}\\n\\n`);
                const ev = new Event('input', { bubbles: true});
                chatInput.dispatchEvent(ev);
                chatInput.focus();
            }
        }
        
        swipedElement.style.transition = 'transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
        swipedElement.style.transform = 'translateX(0)';
        isDragging = false;
        swipedElement = null;
        currentX = 0;
    };
    
    parentDoc.addEventListener('touchstart', onTouchStart);
    parentDoc.addEventListener('touchmove', onTouchMove);
    parentDoc.addEventListener('touchend', onTouchEnd);
    
    parentDoc.addEventListener('mousedown', onTouchStart);
    parentDoc.addEventListener('mousemove', onTouchMove);
    parentDoc.addEventListener('mouseup', onTouchEnd);
}
</script>
""", height=0, width=0)


