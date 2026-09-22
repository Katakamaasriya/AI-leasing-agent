from datetime import datetime
import pandas as pd
import requests
import streamlit as st
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend.ui import api, select_property

st.title("Units")
st.caption("Maintain availability, pricing, amenities, and floor plans used by the agent.")
property_ = select_property()
units = api(f"/properties/{property_['id']}/units")
if units:
    st.dataframe(pd.DataFrame(units)[["unit_number", "status", "beds", "baths", "square_feet", "monthly_rent", "available_date", "floor_plan", "amenities", "inventory_synced_at"]], hide_index=True)
with st.expander("Add unit"):
    with st.form("add_unit", clear_on_submit=True):
        number = st.text_input("Unit number")
        floor_plan = st.text_input("Floor plan")
        a, b, c = st.columns(3)
        beds = a.number_input("Bedrooms", min_value=0, max_value=10, value=1)
        baths = b.number_input("Bathrooms", min_value=0.5, max_value=10.0, value=1.0, step=0.5)
        square_feet = c.number_input("Square feet", min_value=1, value=700)
        rent, available = st.columns(2)
        monthly_rent = rent.number_input("Monthly rent ($)", min_value=1.0, value=1500.0, step=25.0)
        available_date = available.date_input("Available date", value=datetime.now().date())
        status = st.selectbox("Status", ["available", "held", "leased", "offline"])
        amenities = st.text_input("Amenities", placeholder="Pool, balcony, in-unit laundry")
        add = st.form_submit_button("Add unit", type="primary")
    if add:
        try:
            api("/units", "post", json={"property_id": property_["id"], "unit_number": number, "floor_plan": floor_plan, "beds": beds, "baths": baths, "square_feet": square_feet, "monthly_rent": monthly_rent, "available_date": datetime.combine(available_date, datetime.min.time()).isoformat(), "status": status, "amenities": [item.strip() for item in amenities.split(",") if item.strip()]})
            st.success("Unit added.")
            st.rerun()
        except requests.HTTPError as error:
            st.error(error.response.json().get("detail", "Unable to add unit."))
if units:
    st.subheader("Edit unit")
    current = st.selectbox("Select unit", units, format_func=lambda unit: f"{unit['unit_number']} · {unit['status']} · ${unit['monthly_rent']:,.0f}")
    with st.form("edit_unit"):
        unit_number = st.text_input("Unit number", value=current["unit_number"])
        floor_plan = st.text_input("Floor plan", value=current["floor_plan"])
        x, y, z = st.columns(3)
        beds = x.number_input("Bedrooms", min_value=0, max_value=10, value=current["beds"])
        baths = y.number_input("Bathrooms", min_value=0.5, max_value=10.0, value=float(current["baths"]), step=0.5)
        square_feet = z.number_input("Square feet", min_value=1, value=current["square_feet"])
        rent, available = st.columns(2)
        monthly_rent = rent.number_input("Monthly rent ($)", min_value=1.0, value=float(current["monthly_rent"]), step=25.0)
        available_date = available.date_input("Available date", value=datetime.fromisoformat(current["available_date"]).date())
        status = st.selectbox("Status", ["available", "held", "leased", "offline"], index=["available", "held", "leased", "offline"].index(current["status"]))
        amenities = st.text_input("Amenities", value=", ".join(current["amenities"]))
        save = st.form_submit_button("Save unit", type="primary")
    if save:
        api(f"/units/{current['id']}", "put", json={"unit_number": unit_number, "floor_plan": floor_plan, "beds": beds, "baths": baths, "square_feet": square_feet, "monthly_rent": monthly_rent, "available_date": datetime.combine(available_date, datetime.min.time()).isoformat(), "status": status, "amenities": [item.strip() for item in amenities.split(",") if item.strip()]})
        st.success("Unit saved. Its inventory timestamp has been refreshed.")
        st.rerun()
