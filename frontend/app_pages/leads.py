import pandas as pd
import streamlit as st
from frontend.ui import api, select_property

st.title("Leads")
st.caption("Manually add a prospect or record an inquiry received from any channel.")
property_ = select_property("Property for this lead")
with st.form("new_lead", clear_on_submit=True):
    name = st.text_input("Prospect name")
    contact = st.text_input("Phone number or email")
    channel = st.selectbox("Source channel", ["phone", "sms", "email", "listing_site"])
    message = st.text_area("Inquiry or staff note")
    st.subheader("Initial housing needs")
    budget_monthly = st.number_input("Monthly budget", min_value=0.0, step=100.0, value=0.0)
    bedrooms = st.selectbox("Bedrooms", ["Not specified", "Studio", "1", "2", "3", "4"])
    preferred_location = st.text_input("Preferred location")
    amenities = st.multiselect("Desired amenities", ["gym", "fitness center", "pool", "balcony", "parking", "pet park", "in-unit laundry", "elevator", "storage"])
    desired_move_in = st.date_input("Desired move-in date", value=None)
    pet_status = st.selectbox("Pet", ["Not specified", "No pet", "Has a pet"])
    add = st.form_submit_button("Add lead", type="primary")
if add:
    try:
        profile_message = message.strip()
        structured_needs = []
        if budget_monthly: structured_needs.append(f"Budget ${budget_monthly:,.0f}/month")
        if bedrooms != "Not specified": structured_needs.append("Studio" if bedrooms == "Studio" else f"{bedrooms} bedroom")
        if preferred_location.strip(): structured_needs.append(f"Preferred location: {preferred_location.strip()}")
        if amenities: structured_needs.append("Amenities: " + ", ".join(amenities))
        if desired_move_in: structured_needs.append(f"Move-in: {desired_move_in.isoformat()}")
        if pet_status != "Not specified": structured_needs.append(pet_status)
        if structured_needs:
            profile_message = (profile_message + " | " if profile_message else "") + "; ".join(structured_needs)
        result = api("/inquiries", "post", json={
            "name": name, "contact": contact, "channel": channel, "message": profile_message,
            "property_id": property_["id"], "budget_monthly": budget_monthly or None,
            "bedrooms": None if bedrooms == "Not specified" else (0 if bedrooms == "Studio" else int(bedrooms)),
            "preferred_location": preferred_location or None, "amenities": amenities,
            "desired_move_in": desired_move_in.isoformat() if desired_move_in else None,
            "has_pet": None if pet_status == "Not specified" else pet_status == "Has a pet",
        })
        st.success(f"Lead #{result['lead_id']} added to conversation #{result['conversation_id']}.")
        st.rerun()
    except Exception as error:
        st.error(f"Could not add lead: {error}")
leads = api("/leads", params={"property_id": property_["id"]})
if leads:
    st.subheader("Lead register")
    st.dataframe(pd.DataFrame(leads)[["id", "name", "contact", "channel", "message", "created_at", "qualification_status", "human_requested"]], hide_index=True)
