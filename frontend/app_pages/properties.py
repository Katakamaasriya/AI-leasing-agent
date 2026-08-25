import pandas as pd
import streamlit as st
from frontend.ui import api, properties_or_stop

st.title("Properties")
st.caption("Add the properties that your leasing team manages.")
properties = properties_or_stop()
if properties:
    st.dataframe(pd.DataFrame(properties)[["id", "name", "address", "income_multiplier", "pet_policy"]], hide_index=True)
with st.form("add_property", clear_on_submit=True):
    name = st.text_input("Property name")
    address = st.text_input("Street address")
    left, right = st.columns(2)
    latitude = left.number_input("Latitude", min_value=-90.0, max_value=90.0, value=30.2672, format="%.6f")
    longitude = right.number_input("Longitude", min_value=-180.0, max_value=180.0, value=-97.7431, format="%.6f")
    income_multiplier = st.number_input("Published income requirement (times rent)", min_value=0.0, max_value=10.0, value=3.0, step=0.1)
    pet_policy = st.text_area("Published pet policy", placeholder="Example: Cats and dogs welcome; published breed and weight limits apply.")
    submitted = st.form_submit_button("Add property", type="primary")
if submitted:
    try:
        api("/properties", "post", json={"name": name, "address": address, "latitude": latitude, "longitude": longitude, "income_multiplier": income_multiplier, "pet_policy": pet_policy})
        st.success("Property added.")
        st.rerun()
    except Exception as error:
        st.error(f"Could not add property: {error}")
