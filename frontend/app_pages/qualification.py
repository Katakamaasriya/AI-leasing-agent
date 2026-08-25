from datetime import datetime
import requests
import streamlit as st
from frontend.ui import api, select_property

st.title("Qualification & human handoff")
st.caption("Evaluate only published, objective criteria. This tool does not approve or deny an applicant.")
property_ = select_property()
leads = api("/leads", params={"property_id": property_["id"]})
units = [unit for unit in api(f"/properties/{property_['id']}/units") if unit["status"] == "available"]
if not leads or not units:
    st.info("Add at least one lead and one available unit before qualification.")
    st.stop()
lead = st.selectbox("Lead", leads, format_func=lambda item: f"#{item['id']} · {item['name']} · {item['qualification_status']}")
with st.form("qualify"):
    unit = st.selectbox("Available unit", units, format_func=lambda item: f"{item['unit_number']} · ${item['monthly_rent']:,.0f}")
    income = st.number_input("Verified monthly income", min_value=1.0, value=1.0, step=100.0, help="Enter the prospect's verified monthly income. It must be greater than $0.")
    move_in = st.date_input("Desired move-in date", min_value=datetime.now().date())
    has_pet = st.checkbox("Prospect has a pet")
    pet_type = st.text_input("Pet type, if voluntarily provided") if has_pet else None
    evaluate = st.form_submit_button("Evaluate published criteria", type="primary")
if evaluate:
    try:
        result = api(f"/leads/{lead['id']}/qualify", "post", json={"unit_id": unit["id"], "monthly_income": income, "desired_move_in": datetime.combine(move_in, datetime.min.time()).isoformat(), "has_pet": has_pet, "pet_type": pet_type})
        st.info(f"Outcome: {result['status'].replace('_', ' ')}")
        st.write(result["notes"])
    except requests.HTTPError as error:
        detail = error.response.json().get("detail", "Unable to evaluate the qualification criteria.")
        st.error(f"Please correct the qualification details: {detail}")
if st.button("Request human follow-up"):
    api(f"/leads/{lead['id']}/handoff", "post", json={"reason": "Leasing-console escalation"})
    st.success("Human follow-up queued.")
