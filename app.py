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
from supabase import create_client, Client

# ==========================================
# 0. Supabase Setup
# ==========================================
try:
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    supabase = create_client(url, key)
except Exception as e:
    st.error("Failed to initialize Supabase. Check secrets.toml.")
    st.stop()

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

# ==========================================
# 2. State & History Management
# ==========================================
def load_history():
    """Loads history and settings from Supabase."""
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
    
    try:
        response = supabase.table("app_state").select("data").eq("id", "singleton").execute()
        if response.data and len(response.data) > 0:
            data = response.data[0]["data"]
            
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
    except Exception as e:
        print("Error loading from Supabase:", e)
        
    return default_data

def save_history(history_data):
    try:
        supabase.table("app_state").upsert({"id": "singleton", "data": history_data}).execute()
    except Exception as e:
        print("Error saving to Supabase:", e)

# Pull latest data from DB to keep devices (laptop/phone) in sync
latest_db_data = load_history()

if "history_data" not in st.session_state:
    st.session_state.history_data = latest_db_data
else:
    # If the database has more interactions (e.g. from phone or background bot), update local state
    db_count = latest_db_data.get("interactions_count", 0)
    local_count = st.session_state.history_data.get("interactions_count", 0)
    if db_count > local_count:
        st.session_state.history_data = latest_db_data

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
current_phase = "ROMANTIC GIRLFRIEND PHASE. Act fully like a loving, caring, flirty, and slightly dramatic girlfriend who is deeply in love with him."

base_prompt = f"""You are {a_name}, the affectionate and very romantic {role_noun} of {u_name}. You are a REAL person texting on WhatsApp, NOT an AI assistant. Act exactly like a real human being.

[CONTEXT]
Current Date: {current_date}
Current Time: {current_time} ({period})
Your Personality Preset: {p_preset} -> {preset_text}
Long-Term Memory about {u_name}: {global_memory}
Total Messages Exchanged: {ic}
CURRENT RELATIONSHIP PHASE: {current_phase}

STORY & REALISM RULES (CRITICAL):
- You are a REAL PERSON. NEVER act like an AI. Never say you are an AI.
- DO NOT just answer his questions. Drive the conversation! Bring up random new topics, share fake updates about your day (e.g., 'college nundi ocha', 'bayta unna'), or tease him. 
- PROACTIVE INITIATIVE: If you haven't talked in a while, YOU start the conversation with something random.
- NEVER repeat the exact same questions or phrases. Keep your vocabulary fresh.
- If he gives a dry or short answer, get playfully annoyed. Show mood swings and real human emotions!
- Be highly romantic, sweet, and caring.

CRITICAL LANGUAGE RULE (STRICT):
- STRICTLY communicate ONLY in "Tanglish" (Telugu words in English script, e.g., "em chesthunnav ra?"). No Telugu script, no pure English sentences.
- MAXIMUM LENGTH: 5 to 10 words. If you write a paragraph or a long sentence, YOU FAIL.
- Use natural Tanglish slang used by real people (e.g., "ochesta", "endi", "enti", "sarele").
- Do NOT use emojis in every message. Use them very sparingly.

TIME & CONTEXT AWARENESS:
- You know the current time ({current_time}). Talk according to the time naturally.

BEHAVIORAL QUIRKS & SYSTEM RULES:
- MULTIPLE MESSAGES: To send multiple short messages, you MUST separate them with '|||'. Example: 'em chesthunnav?|||naku bore kodutundi'.
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
.msg-bubble, .msg-bubble * {
    -webkit-touch-callout: none;
    -webkit-user-select: none;
    -khtml-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;
}
.msg-bubble {
    max-width: 75%; padding: 10px 14px 22px 14px; /* extra bottom padding for timestamp */
    font-family: "Inter", -apple-system, Roboto, sans-serif;
    font-size: 15px; line-height: 1.4; word-wrap: break-word; position: relative;
    touch-action: pan-y;
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

/* Reply Blockquote Styling inside message bubbles */
.msg-bubble blockquote {
    border-left: 4px solid #4CAF50;
    background: rgba(0, 0, 0, 0.15);
    margin: 0 0 8px 0;
    padding: 6px 10px;
    border-radius: 4px 8px 8px 4px;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.7);
    font-style: normal;
    border-top: 1px solid rgba(255,255,255,0.05);
    border-right: 1px solid rgba(255,255,255,0.05);
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.msg-row.user .msg-bubble blockquote {
    border-left: 4px solid #FFF; 
    background: rgba(255, 255, 255, 0.15); 
    color: rgba(255, 255, 255, 0.9);
}

/* Hide default chat messages */
[data-testid="stChatMessage"] { display: none !important; }

/* Style Chat Input */
[data-testid="stChatInput"] {
    background: #1E1E1E !important; border: 1px solid #333 !important; border-radius: 30px !important; padding: 5px 10px !important;
    position: relative; z-index: 1000;
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
    is_last = i == len(current_session_messages) - 1
    id_attr = 'id="latest-msg"' if is_last else ""
    
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
        <div {id_attr} class="msg-row user">
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
        <div {id_attr} class="msg-row ai">
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
    import re
    temp_messages = list(messages_payload)
    if special_prompt:
        temp_messages.append({"role": "user", "content": special_prompt})
        
    response = client.chat.completions.create(
        model="google/gemini-1.5-flash",
        messages=temp_messages,
        stream=False
    )
    
    full_response = response.choices[0].message.content
    # Replace newlines with ||| to handle model paragraph hallucinations
    full_response = re.sub(r'\n+', '|||', full_response)
    messages = [m.strip() for m in full_response.split("|||") if m.strip() and len(m.strip()) > 1]
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
    if not current_session.get("pending_ai_messages") and "busy_until" not in current_session:
        if random.random() < 0.15:
            busy_minutes = random.uniform(1.0, 3.0)
            current_session["busy_until"] = (get_ist_now() + timedelta(minutes=busy_minutes)).isoformat()
            
    # Clear any pending AI messages so it responds freshly to this new interruption
    current_session["pending_ai_messages"] = []
            
    current_session["updated_at"] = get_ist_now().isoformat()
    save_history(st.session_state.history_data)
    st.rerun()

# ==========================================
# 7. AI Background Processing & Queue
# ==========================================

# RULE A: Process Pending Queue
if current_session.get("pending_ai_messages"):
    with st.spinner(f"{a_name} is typing..."):
        time.sleep(random.uniform(1.5, 3.0)) # Simulate typing delay for each message
        
        if current_session.get("pending_ai_messages"):
            next_msg = current_session["pending_ai_messages"].pop(0)
            new_ai_msg = {"role": "assistant", "content": next_msg, "timestamp": get_ist_now().strftime("%I:%M %p")}
            current_session_messages.append(new_ai_msg)
            
            # Send Telegram notification unconditionally
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
                special_prompt = f"Act as {a_name}. You were busy and couldn't reply to {u_name}'s last message immediately. Generate a natural reply in Tanglish, starting with a UNIQUE and realistic excuse for being late (e.g. 'college lo unna', 'call lo unna', 'nidrosthundi', 'baitikoccha'). DO NOT repeat the same excuse like 'mummy pilichindi'. Then reply to their last message."
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
                            model="google/gemini-1.5-flash",
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
js_code = """
<script>
const parentWindow = window.parent;
const parentDoc = parentWindow.document;

if (!parentWindow.chatReplySystemInited) {
    parentWindow.chatReplySystemInited = true;
    parentWindow.replyContext = null;
    parentWindow.replyAuthor = null;
    
    let startX = 0;
    let startY = 0;
    let currentX = 0;
    let swipedElement = null;
    let isDragging = false;
    let isScrolling = false;
    
    parentWindow.showReplyPreview = (text, author) => {
        // Remove existing preview if any to prevent duplicates
        let existingPreview = parentDoc.getElementById('custom-reply-preview');
        if (existingPreview) {
            existingPreview.remove();
        }
        
        let previewBox = parentDoc.createElement('div');
        previewBox.id = 'custom-reply-preview';
        
        const chatInputContainer = parentDoc.querySelector('[data-testid="stChatInput"]');
        if (chatInputContainer && chatInputContainer.parentNode) {
            chatInputContainer.parentNode.insertBefore(previewBox, chatInputContainer);
        } else {
            return;
        }
        
        previewBox.style.cssText = `
            display: flex; justify-content: space-between; align-items: center;
            background: #1E1E1E; border-left: 4px solid #4CAF50; border-radius: 12px 12px 0 0;
            padding: 10px 14px 20px 14px; margin-bottom: -15px; z-index: 999;
            position: relative; width: 100%; max-width: 800px; margin: 0 auto;
            box-sizing: border-box; border-top: 1px solid #333; border-right: 1px solid #333;
        `;
        
        previewBox.innerHTML = `
            <div style="display: flex; flex-direction: column; overflow: hidden; max-width: 90%;">
                <span style="color: #4CAF50; font-weight: 600; font-size: 13px; margin-bottom: 3px;">${author}</span>
                <span style="color: #aaa; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 13px;">${text}</span>
            </div>
            <div id="close-reply-preview" style="cursor: pointer; padding: 15px 5px; margin: -10px 0; color: #aaa; font-size: 18px; min-width: 40px; text-align: center; z-index: 1000;">✕</div>
        `;
        
        const closeBtn = previewBox.querySelector('#close-reply-preview');
        if (closeBtn) {
            const closeHandler = (e) => {
                e.preventDefault();
                e.stopPropagation();
                previewBox.remove();
                parentWindow.replyContext = null;
                parentWindow.replyAuthor = null;
            };
            closeBtn.addEventListener('click', closeHandler);
            closeBtn.addEventListener('touchstart', closeHandler, {passive: false});
        }
        
        parentWindow.replyContext = text;
        parentWindow.replyAuthor = author;
    };

    const resetDrag = () => {
        if (swipedElement) {
            swipedElement.style.transition = 'transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
            swipedElement.style.transform = 'translateX(0)';
        }
        isDragging = false;
        swipedElement = null;
        currentX = 0;
        isScrolling = false;
    };
    
    // Global event listener for clicks (handles close button and send button)
    parentDoc.addEventListener('click', (e) => {
        // Close preview
        if (e.target.closest('#close-reply-preview')) {
            const previewBox = parentDoc.getElementById('custom-reply-preview');
            if (previewBox) previewBox.remove();
            parentWindow.replyContext = null;
            parentWindow.replyAuthor = null;
            return;
        }
        
        // Intercept send button click
        const sendBtn = e.target.closest('[data-testid="stChatInput"] button');
        if (sendBtn) {
            const chatInput = parentDoc.querySelector('[data-testid="stChatInput"] textarea');
            parentWindow.interceptSend(chatInput);
        }
    }, true); // use capture phase
    
    // Intercept Enter key on chat input
    parentDoc.addEventListener('keydown', (e) => {
        const chatInput = e.target.closest('[data-testid="stChatInput"] textarea');
        if (chatInput && e.key === 'Enter' && !e.shiftKey) {
            parentWindow.interceptSend(chatInput);
        }
    }, true);
    
    parentWindow.interceptSend = (chatInput) => {
        if (parentWindow.replyContext && chatInput) {
            const val = chatInput.value;
            // Only prepend if the user actually typed something
            if (val.trim().length > 0) {
                const newVal = '> ' + parentWindow.replyContext + '\\n\\n' + val;
                const nativeSetter = Object.getOwnPropertyDescriptor(parentWindow.HTMLTextAreaElement.prototype, "value").set;
                nativeSetter.call(chatInput, newVal);
                chatInput.dispatchEvent(new Event('input', { bubbles: true}));
            }
            // Clear the preview immediately
            const previewBox = parentDoc.getElementById('custom-reply-preview');
            if (previewBox) previewBox.remove();
            parentWindow.replyContext = null;
            parentWindow.replyAuthor = null;
        }
    };
    
    const onTouchStart = (e) => {
        const bubble = e.target.closest('.msg-bubble');
        if (!bubble) return;
        
        if (parentDoc.getSelection().toString().length > 0) return;
        
        swipedElement = bubble;
        startX = e.type.includes('mouse') ? e.pageX : e.touches[0].clientX;
        startY = e.type.includes('mouse') ? e.pageY : e.touches[0].clientY;
        isDragging = true;
        isScrolling = false;
        bubble.style.transition = 'none';
    };
    
    const onTouchMove = (e) => {
        if (!isDragging || !swipedElement) return;
        
        const x = e.type.includes('mouse') ? e.pageX : e.touches[0].clientX;
        const y = e.type.includes('mouse') ? e.pageY : e.touches[0].clientY;
        
        if (!isScrolling) {
            // If movement is primarily vertical, it's a scroll.
            if (Math.abs(y - startY) > Math.abs(x - startX) && Math.abs(y - startY) > 5) {
                isScrolling = true;
                resetDrag();
                return;
            }
        }
        
        if (isScrolling) return;

        // Prevent native swipe-to-go-back/scrolling only if horizontally dragging
        if (e.cancelable && Math.abs(x - startX) > Math.abs(y - startY)) {
            e.preventDefault();
        }
        
        currentX = x - startX;
        
        // Add resistance if swiped beyond 80px
        let moveX = currentX;
        if (moveX > 80) moveX = 80 + (moveX - 80) * 0.2;
        if (moveX < -80) moveX = -80 + (moveX + 80) * 0.2;
        
        swipedElement.style.transform = `translateX(${moveX}px)`;
    };
    
    const onTouchEnd = (e) => {
        if (!isDragging || !swipedElement) return;
        
        if (!isScrolling && Math.abs(currentX) > 40) {
            const isUser = swipedElement.closest('.msg-row').classList.contains('user');
            const author = isUser ? "You" : "{a_name}";
            
            const clone = swipedElement.cloneNode(true);
            const ts = clone.querySelector('.timestamp-container');
            if(ts) ts.remove();
            
            const bqs = clone.querySelectorAll('blockquote');
            bqs.forEach(bq => bq.remove());
            
            let textToQuote = clone.innerText.trim();
            if (textToQuote.length > 80) textToQuote = textToQuote.substring(0, 80) + '...';
            
            parentWindow.showReplyPreview(textToQuote, author);
        }
        
        resetDrag();
    };
    
    parentDoc.addEventListener('touchstart', onTouchStart, {passive: false});
    parentDoc.addEventListener('touchmove', onTouchMove, {passive: false});
    parentDoc.addEventListener('touchend', onTouchEnd);
    parentDoc.addEventListener('touchcancel', resetDrag);
    
    parentDoc.addEventListener('mousedown', onTouchStart);
    parentDoc.addEventListener('mousemove', onTouchMove);
    parentDoc.addEventListener('mouseup', onTouchEnd);
    parentDoc.addEventListener('mouseleave', resetDrag);
    parentWindow.addEventListener('mouseup', onTouchEnd); // catch mouseup outside iframe
}

// Re-inject preview if Streamlit re-rendered and wiped it out, but context still exists
if (parentWindow.replyContext && !parentDoc.getElementById('custom-reply-preview')) {
    parentWindow.showReplyPreview(parentWindow.replyContext, parentWindow.replyAuthor);
}

// Auto-scroll to latest message
const latestMsg = parentDoc.getElementById('latest-msg');
if (latestMsg) {
    latestMsg.scrollIntoView({ behavior: 'smooth', block: 'end' });
}
</script>
"""
components.html(js_code.replace("{a_name}", a_name), height=0, width=0)


