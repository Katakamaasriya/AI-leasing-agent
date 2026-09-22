import streamlit as st
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend.ui import api


st.title("AI Leasing Agent")
st.caption("Your intelligent leasing assistant - available 24/7 to help prospects find their perfect home, answer questions, and schedule tours.")
leads = api("/leads")

if not leads:
    st.info("Add a lead before starting a conversation.")
    st.stop()

lead = st.selectbox("Select a prospect to assist", leads, format_func=lambda item: f"#{item['id']} — {item['name']} ({item['channel']})")

# Display lead info
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Lead ID", lead["id"])
with col2:
    st.metric("Channel", lead["channel"])
with col3:
    st.metric("Status", lead["qualification_status"])

# Show current needs profile if available
if lead.get("needs_profile"):
    with st.expander("Current prospect preferences"):
        st.json(lead["needs_profile"])

st.success("Connected to the leasing database", icon=":material/database:")
st.info("💡 Tip: The AI can help with availability, pricing, amenities, unit matching, tour scheduling, and general questions. It always offers human handoff when needed.")

if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = {}
messages = st.session_state.ai_messages.setdefault(lead["id"], [])

# Welcome message for new conversations
if not messages:
    with st.chat_message("assistant"):
        st.write(f"Hello! I'm your AI leasing assistant. I'm here to help {lead['name']} find their perfect home. I can tell you about available units, pricing, amenities, help schedule tours, and answer questions about our properties. What would you like to know?")
    messages.append({"role": "assistant", "content": f"Hello! I'm your AI leasing assistant. I'm here to help {lead['name']} find their perfect home. I can tell you about available units, pricing, amenities, help schedule tours, and answer questions about our properties. What would you like to know?"})

for message in messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

prompt = st.chat_input("Ask about availability, pricing, amenities, schedule a tour, or general questions")
if prompt:
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    try:
        result = api("/agent/chat", "post", json={"lead_id": lead["id"], "prompt": prompt})
        messages.append({"role": "assistant", "content": result["reply"]})
        lead["needs_profile"] = result.get("needs_profile", lead.get("needs_profile", {}))
        with st.chat_message("assistant"):
            st.write(result["reply"])
            
            # Show additional context
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"Response source: {result.get('provider', 'database')}")
            with col2:
                st.caption("Human handoff available: ✅")
            
            if result.get("inventory_fresh"):
                st.success("Live inventory is fresh and current", icon=":material/verified:")
            else:
                st.warning("Live inventory needs refresh - pricing/availability may not be current", icon=":material/warning:")
                
    except Exception as error:
        st.error(f"Could not generate a response: {error}")
        st.caption("The backend API may be offline. Start it with: uvicorn backend.main:app --reload")