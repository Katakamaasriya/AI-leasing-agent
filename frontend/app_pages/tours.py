from datetime import datetime
import requests
import streamlit as st
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend.ui import api, select_property

st.title("Tours")
st.caption("Check the shared schedule and send a confirmation when a tour is booked.")
property_ = select_property()
leads = api("/leads", params={"property_id": property_["id"]})
with st.form("tour"):
    selected_lead = st.selectbox("Link to lead (optional)", [None] + leads, format_func=lambda item: "No linked lead" if item is None else f"#{item['id']} · {item['name']}")
    name = st.text_input("Prospect name", value=selected_lead["name"] if selected_lead else "")
    contact = st.text_input("Phone number or email", value=selected_lead["contact"] if selected_lead else "")
    date = st.date_input("Tour date", min_value=datetime.now().date())
    time = st.time_input("Tour time")
    book = st.form_submit_button("Check and schedule tour", type="primary")
if book:
    try:
        result = api("/tours", "post", json={"property_id": property_["id"], "prospect_name": name, "prospect_contact": contact, "starts_at": datetime.combine(date, time).isoformat(), "lead_id": selected_lead["id"] if selected_lead else None})
        st.success(result["confirmation"]["message"])
    except requests.HTTPError as error:
        st.error(error.response.json().get("detail", "Unable to schedule tour."))
