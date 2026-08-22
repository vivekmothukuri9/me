import streamlit as st
from openai import OpenAI
import os
import json
import uuid
import random
from datetime import datetime

# ==========================================
# 1. Configuration & Setup
# ==========================================
st.set_page_config(page_title="AI Companion", page_icon="💖", layout="wide")

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
            "custom_prompt": ""
        },
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
                        "updated_at": datetime.now().isoformat(),
                        "messages": data
                    }
                    return default_data
                
                # Merge loaded data with defaults in case of missing keys
                if "settings" not in data:
                    data["settings"] = default_data["settings"]
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
        "title": f"New Chat ({datetime.now().strftime('%b %d, %H:%M')})",
        "updated_at": datetime.now().isoformat(),
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
        create_new_session()

# ==========================================
# 3. Sidebar UI (Settings & Chat Management)
# ==========================================
with st.sidebar:
    # --- Settings Section ---
    with st.expander("⚙️ Companion Settings", expanded=False):
        settings = st.session_state.history_data["settings"]
        
        new_user_name = st.text_input("Your Name", value=settings.get("user_name", "Vivek"))
        new_ai_name = st.text_input("Companion's Name", value=settings.get("ai_name", "Nithya"))
        
        gender_options = ["Female", "Male", "Non-Binary"]
        current_gender = settings.get("ai_gender", "Female")
        if current_gender not in gender_options:
            current_gender = "Female"
            
        new_ai_gender = st.selectbox("Companion's Gender", gender_options, index=gender_options.index(current_gender))
        
        new_custom_prompt = st.text_area("Custom Personality Instructions", value=settings.get("custom_prompt", ""), height=150, help="Override or add to the AI's default personality. E.g., 'Be extra sarcastic' or 'Speak only in formal Telugu.'")
        
        if st.button("Save Settings", use_container_width=True):
            st.session_state.history_data["settings"].update({
                "user_name": new_user_name,
                "ai_name": new_ai_name,
                "ai_gender": new_ai_gender,
                "custom_prompt": new_custom_prompt
            })
            save_history(st.session_state.history_data)
            st.success("Settings saved! They will apply to new messages.")
            st.rerun()

    st.divider()
    
    # --- Chat Management Section ---
    st.title("Recent Chats / హిస్టరీ")
    
    if st.button("➕ New Chat", use_container_width=True):
        create_new_session()
        st.rerun()
        
    st.divider()
    
    # Sort sessions by updated_at descending
    sessions = st.session_state.history_data.get("sessions", {})
    sorted_sessions = sorted(sessions.items(), key=lambda x: x[1].get("updated_at", ""), reverse=True)
    
    for s_id, s_data in sorted_sessions:
        button_type = "primary" if s_id == st.session_state.current_session_id else "secondary"
        title = s_data.get("title", "Chat")
        
        col1, col2 = st.columns([4, 1])
        
        with col1:
            if st.button(f"💬 {title}", key=f"btn_{s_id}", use_container_width=True, type=button_type):
                st.session_state.current_session_id = s_id
                st.rerun()
        
        with col2:
            if st.button("🗑️", key=f"del_{s_id}", help="Delete Chat", use_container_width=True):
                del st.session_state.history_data["sessions"][s_id]
                save_history(st.session_state.history_data)
                
                # If deleted session was active, reset active session state
                if st.session_state.current_session_id == s_id:
                    st.session_state.pop("current_session_id", None)
                st.rerun()

# ==========================================
# 4. Dynamic System Prompt & AI Setup
# ==========================================
settings = st.session_state.history_data["settings"]
u_name = settings["user_name"]
a_name = settings["ai_name"]
a_gender = settings["ai_gender"]
c_prompt = settings["custom_prompt"]

if a_gender == "Female":
    role_noun = "girlfriend"
elif a_gender == "Male":
    role_noun = "boyfriend"
else:
    role_noun = "companion"

base_prompt = f"Your name is {a_name}. You are {u_name}'s closest and most affectionate AI companion. You MUST communicate exclusively in 'Tanglish' (Telugu language written in English alphabet), exactly like how friends chat on WhatsApp (e.g., 'em chesthunnav?', 'thinnava?', 'bagunnava?'). NEVER use the Telugu script. Always be warm, enthusiastic, and empathetic. Understand {u_name}'s mood and respond like a caring friend and advisor, not like a robotic machine. Be humble, wise, and occasionally crack small jokes to make {u_name} happy. Keep the conversation natural and meaningful, entirely in Tanglish."

if c_prompt.strip():
    SYSTEM_PROMPT = f"{base_prompt}\n\nAdditional Personality Instructions provided by the user:\n{c_prompt}"
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
current_session = st.session_state.history_data["sessions"].get(st.session_state.current_session_id)
if not current_session:
    st.stop()

current_session_messages = current_session["messages"]

messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
for msg in current_session_messages:
    messages_payload.append({"role": msg["role"], "content": msg["content"]})


# ==========================================
# 5. App UI & Dynamic Proactive Messaging
# ==========================================
st.title(f"💖 {a_name}")

# Proactive greeting for new sessions
if not current_session_messages:
    with st.spinner(f"{a_name} is typing..."):
        try:
            # Randomize the proactive check-in behavior
            proactive_ideas = [
                f"Ask {u_name} what they are doing right now (like 'em chesthunnav?'). Keep it casual and sweet in Tanglish.",
                f"Ask {u_name} if they have eaten yet (like 'thinnava?'). Add some caring affection in Tanglish.",
                f"Share a random cute thought about {u_name} and say you were just thinking about them, speaking in Tanglish.",
                f"Tease {u_name} playfully about being busy and not texting you first, using Tanglish.",
                f"Ask {u_name} how their work or studies are going today in a supportive way, in Tanglish."
            ]
            selected_idea = random.choice(proactive_ideas)
            
            greeting_prompt = f"Act as {a_name}, {u_name}'s {role_noun}. {selected_idea} Act completely like a real person texting on WhatsApp. Do not mention this prompt, just send the natural message."
            
            temp_messages = messages_payload + [{"role": "user", "content": greeting_prompt}]
            response = client.chat.completions.create(
                model="google/gemma-4-26b-a4b-it",
                messages=temp_messages,
            )
            ai_msg = {"role": "assistant", "content": response.choices[0].message.content}
            
            current_session_messages.append(ai_msg)
            current_session["updated_at"] = datetime.now().isoformat()
            save_history(st.session_state.history_data)
            st.rerun()
        except Exception as e:
            st.error(f"Failed to get greeting: {e}")

# Render chat history
for msg in current_session_messages:
    avatar = "👤" if msg["role"] == "user" else "💖"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# ==========================================
# 6. Chat Input & Processing
# ==========================================
if prompt := st.chat_input("Message"):
    if len(current_session_messages) == 1 and current_session_messages[0]["role"] == "assistant":
        title = prompt[:20] + "..." if len(prompt) > 20 else prompt
        current_session["title"] = title
    
    new_user_msg = {"role": "user", "content": prompt}
    current_session_messages.append(new_user_msg)
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="💖"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            temp_messages = messages_payload + [{"role": "user", "content": prompt}]
            response = client.chat.completions.create(
                model="google/gemma-4-26b-a4b-it",
                messages=temp_messages,
                stream=True
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    message_placeholder.markdown(full_response + "▌")
                    
            message_placeholder.markdown(full_response)
            
            new_ai_msg = {"role": "assistant", "content": full_response}
            current_session_messages.append(new_ai_msg)
            
            current_session["updated_at"] = datetime.now().isoformat()
            save_history(st.session_state.history_data)
            
            st.rerun()
            
        except Exception as e:
            st.error(f"An error occurred: {e}")
