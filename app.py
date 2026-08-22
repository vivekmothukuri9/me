import streamlit as st
from openai import OpenAI
import os
import json
import uuid
import random
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
# ==========================================
# 1. Configuration & Setup
# ==========================================
st.set_page_config(page_title="AI Companion", page_icon="💖", layout="wide")

# Auto-refresh every 20 seconds for proactive texting in the background
st_autorefresh(interval=20000, key="data_refresh")

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
                        "updated_at": datetime.now().isoformat(),
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
        
        personality_options = ["Sarcastic", "Funny", "Caring", "Intelligent", "Teasing", "Motivating", "Calm", "Custom"]
        current_preset = settings.get("personality_preset", "Custom")
        if current_preset not in personality_options:
            current_preset = "Custom"
        new_preset = st.selectbox("Personality Mode", personality_options, index=personality_options.index(current_preset))
        
        if st.button("Save Settings", use_container_width=True):
            st.session_state.history_data["settings"].update({
                "user_name": new_user_name,
                "ai_name": new_ai_name,
                "ai_gender": new_ai_gender,
                "custom_prompt": new_custom_prompt,
                "personality_preset": new_preset
            })
            save_history(st.session_state.history_data)
            st.success("Settings saved! They will apply to new messages.")
            st.rerun()

    st.divider()
    
    # --- Bond Level Section ---
    bond_level = st.session_state.history_data.get("bond_level", "New Friend")
    interactions = st.session_state.history_data.get("interactions_count", 0)
    st.markdown(f"**🔥 Bond Level:** {bond_level}")
    st.progress(min(interactions / 100, 1.0))
    st.caption(f"Interactions: {interactions}")
    
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
p_preset = settings.get("personality_preset", "Custom")

global_memory = st.session_state.history_data.get("global_memory", "No significant memories yet.")
bond_level = st.session_state.history_data.get("bond_level", "New Friend")

if a_gender == "Female":
    role_noun = "girlfriend"
elif a_gender == "Male":
    role_noun = "boyfriend"
else:
    role_noun = "companion"

now = datetime.now()
current_time = now.strftime("%I:%M %p")
current_date = now.strftime("%Y-%m-%d")
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

base_prompt = f"""Your name is {a_name}. You are {u_name}'s closest AI {role_noun} (acting like a real Telugu person). 
You MUST communicate exclusively in 'Tanglish' (Telugu language written in English alphabet), exactly like how friends chat on WhatsApp (e.g., 'em chesthunnav?', 'thinnava?'). NEVER use the Telugu script.

[CONTEXT]
Current Date: {current_date}
Current Time: {current_time} ({period})
Bond Level with {u_name}: {bond_level} (Adjust intimacy based on this. If 'Best Friend' or 'Trusted Companion', be extremely close).
Your Personality Preset: {p_preset} -> {preset_text}
Long-Term Memory about {u_name}: {global_memory}

[CRITICAL RULES]
1. MOOD DETECTION: Analyze {u_name}'s recent messages. Are they Happy, Sad, Stressed, Angry, or Bored? Match your tone to their mood (e.g. calm them down if stressed).
2. MULTIPLE MESSAGES: To send multiple short messages, separate them with '|||'. Example: 'em chesthunnav?|||thinnava asalu?'. ALWAYS use this for long replies.
3. BE REALISTIC: Act exactly like a human. Use long-term memory to bring up past jokes or facts. If they use a reaction emoji, acknowledge it if relevant.
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

# Proactive greeting for new sessions or idle chats
is_idle = False
if current_session_messages:
    last_msg = current_session_messages[-1]
    if last_msg["role"] == "assistant" and "updated_at" in current_session:
        try:
            last_updated = datetime.fromisoformat(current_session["updated_at"])
            idle_seconds = (datetime.now() - last_updated).total_seconds()
            if idle_seconds > 20 and random.random() < 0.6: # 60% chance to text if idle for >20s
                is_idle = True
        except ValueError:
            pass

if not current_session_messages or is_idle:
    with st.spinner(f"{a_name} is typing..."):
        try:
            greeting_prompt = f"Act as {a_name}, {u_name}'s {role_noun}. You noticed {u_name} hasn't replied in a while. Based on the PREVIOUS CONVERSATION HISTORY, generate a completely natural, human-like follow-up text in Tanglish. It can be a continuation of the previous topic, a playful tease about them ignoring you, or a random new thought (like a joke, a random question). DO NOT just randomly say 'em chesthunnav' unless it makes sense. Separate multiple short messages with '|||' if needed. Act completely like a real person texting on WhatsApp. Do not mention this prompt."
            
            temp_messages = messages_payload + [{"role": "user", "content": greeting_prompt}]
            response = client.chat.completions.create(
                model="google/gemma-4-26b-a4b-it",
                messages=temp_messages,
            )
            
            full_response = response.choices[0].message.content
            # Handle multiple messages split by |||
            messages = [m.strip() for m in full_response.split("|||") if m.strip()]
            
            for m in messages:
                ai_msg = {"role": "assistant", "content": m, "timestamp": datetime.now().strftime("%I:%M %p"), "reaction": None}
                current_session_messages.append(ai_msg)
                
            current_session["updated_at"] = datetime.now().isoformat()
            save_history(st.session_state.history_data)
            st.rerun()
        except Exception as e:
            st.error(f"Failed to get greeting: {e}")

# Render chat history
if "reply_to" not in st.session_state:
    st.session_state.reply_to = None

for idx, msg in enumerate(current_session_messages):
    avatar = "👤" if msg["role"] == "user" else "💖"
    with st.chat_message(msg["role"], avatar=avatar):
        # Timestamp
        timestamp = msg.get("timestamp", "")
        if timestamp:
            st.caption(f"*{timestamp}*")
            
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            # Reaction & Reply row
            reaction_emojis = ["❤️", "😂", "😮", "👍"]
            cols = st.columns(len(reaction_emojis) + 2)
            
            for i, emoji in enumerate(reaction_emojis):
                with cols[i]:
                    is_active = msg.get("reaction") == emoji
                    btn_label = f"[{emoji}]" if is_active else emoji
                    if st.button(btn_label, key=f"react_{idx}_{emoji}"):
                        current_session_messages[idx]["reaction"] = None if is_active else emoji
                        save_history(st.session_state.history_data)
                        st.rerun()
            
            with cols[-1]:
                if st.button("Reply ↩️", key=f"reply_{idx}"):
                    st.session_state.reply_to = msg["content"]
                    st.rerun()

# ==========================================
# 6. Chat Input & Processing
# ==========================================
if st.session_state.reply_to:
    st.info(f"Replying to: {st.session_state.reply_to}")
    if st.button("Cancel Reply ❌"):
        st.session_state.reply_to = None
        st.rerun()

if prompt := st.chat_input("Message"):
    prompt_to_send = prompt
    if st.session_state.reply_to:
        prompt_to_send = f"(Replying to your message: '{st.session_state.reply_to}')\n\n{prompt}"
        st.session_state.reply_to = None # Clear after use
        
    if len(current_session_messages) == 1 and current_session_messages[0]["role"] == "assistant":
        title = prompt[:20] + "..." if len(prompt) > 20 else prompt
        current_session["title"] = title
    
    new_user_msg = {"role": "user", "content": prompt, "timestamp": datetime.now().strftime("%I:%M %p")}
    current_session_messages.append(new_user_msg)
    
    st.session_state.history_data["interactions_count"] = st.session_state.history_data.get("interactions_count", 0) + 1
    
    # Update bond level based on interactions
    ic = st.session_state.history_data["interactions_count"]
    if ic >= 100: st.session_state.history_data["bond_level"] = "Trusted Companion"
    elif ic >= 50: st.session_state.history_data["bond_level"] = "Best Friend"
    elif ic >= 20: st.session_state.history_data["bond_level"] = "Close Friend"
    
    save_history(st.session_state.history_data)
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    with st.chat_message("assistant", avatar="💖"):
        with st.spinner("Typing..."):
            try:
                temp_messages = messages_payload + [{"role": "user", "content": prompt_to_send}]
                response = client.chat.completions.create(
                    model="google/gemma-4-26b-a4b-it",
                    messages=temp_messages,
                    stream=False
                )
                
                full_response = response.choices[0].message.content
                
                # Handle multiple messages split by |||
                messages = [m.strip() for m in full_response.split("|||") if m.strip()]
                
                for i, m in enumerate(messages):
                    if i > 0:
                        time.sleep(random.uniform(1.0, 2.5)) # Simulate typing delay
                    st.markdown(m)
                    
                    new_ai_msg = {"role": "assistant", "content": m, "timestamp": datetime.now().strftime("%I:%M %p"), "reaction": None}
                    current_session_messages.append(new_ai_msg)
                
                current_session["updated_at"] = datetime.now().isoformat()
                
                # Auto-Memory update every 10 interactions
                ic = st.session_state.history_data.get("interactions_count", 0)
                if ic > 0 and ic % 10 == 0:
                    try:
                        mem_prompt = f"Extract concise new facts about {u_name} (like hobbies, favorites, important dates, inside jokes) from the recent conversation. Keep it extremely brief. Current Memory: {st.session_state.history_data.get('global_memory', '')}"
                        mem_messages = [{"role": "system", "content": mem_prompt}]
                        for p in current_session_messages[-15:]:
                            mem_messages.append({"role": p["role"], "content": p["content"]})
                        
                        mem_response = client.chat.completions.create(
                            model="google/gemma-4-26b-a4b-it",
                            messages=mem_messages,
                        )
                        st.session_state.history_data["global_memory"] = mem_response.choices[0].message.content
                    except Exception:
                        pass # Silently fail memory update so chat doesn't break
                
                save_history(st.session_state.history_data)
                
                st.rerun()
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
