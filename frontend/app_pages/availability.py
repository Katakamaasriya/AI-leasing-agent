import pandas as pd
import pydeck as pdk
import streamlit as st
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from frontend.ui import api, select_property

st.title("Live availability")
st.caption("Only inventory refreshed within the last five minutes can be quoted.")
property_ = select_property()
availability = api(f"/properties/{property_['id']}/availability")
units, freshness = availability["units"], availability["freshness"]
if not freshness["fresh"]:
    st.error("Inventory is not fresh enough to quote. Open Units and save every currently available unit before responding.")
else:
    st.success("Inventory is current and safe to quote.")
st.caption(f"Oldest available-unit update: {freshness['synced_at'] or 'not available'} UTC · age {freshness['age_seconds'] or '—'} seconds")
if units:
    df = pd.DataFrame(units)[["unit_number", "beds", "baths", "square_feet", "monthly_rent", "available_date", "floor_plan", "amenities", "inventory_synced_at"]]
    df["monthly_rent"] = df["monthly_rent"].map("${:,.0f}".format)
    st.dataframe(df, hide_index=True)
else:
    st.info("No units are currently marked available.")
map_df = pd.DataFrame([property_])
st.pydeck_chart(pdk.Deck(initial_view_state=pdk.ViewState(latitude=property_["latitude"], longitude=property_["longitude"], zoom=12), layers=[pdk.Layer("ScatterplotLayer", map_df, get_position="[longitude, latitude]", get_radius=180, get_fill_color=[18, 130, 100], pickable=True)], tooltip={"text": "{name}\n{address}"}))
