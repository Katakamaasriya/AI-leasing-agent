import streamlit as st

from frontend.ui import api


st.title("AI leasing agent")
st.caption("Full operations mode: ask about leads, properties, units, inventory, tours, or a prospect's needs.")
leads = api("/leads")

if not leads:
    st.info("Add a lead before starting a conversation.")
    st.stop()

lead = st.selectbox("Prospect", leads, format_func=lambda item: f"#{item['id']} — {item['name']} ({item['channel']})")
with st.container(border=True):
    st.subheader("Analyzed lead needs")
    st.caption("Needs are updated from explicit statements in the conversation.")
    profile = lead.get("needs_profile") or {}
    st.write("No needs recorded yet." if not profile else profile)
if "ai_messages" not in st.session_state:
    st.session_state.ai_messages = {}
messages = st.session_state.ai_messages.setdefault(lead["id"], [])

for message in messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

prompt = st.chat_input("Ask about location, budget, home size, amenities, availability, or tours")
if prompt:
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    try:
        result = api("/ai/respond", "post", json={"lead_id": lead["id"], "message": prompt})
        messages.append({"role": "assistant", "content": result["reply"]})
        lead["needs_profile"] = result["needs_profile"]
        with st.chat_message("assistant"):
            st.write(result["reply"])
            if result["provider"] == "fallback":
                st.caption("Fallback mode: configure OPENAI_API_KEY to enable model responses.")
            if result["human_handoff_available"]:
                st.caption("Human handoff is available for this conversation.")
    except Exception as error:
        st.error(f"Could not generate a response: {error}")