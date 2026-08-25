import numpy as np
import streamlit as st
from frontend.ui import api

st.title("Team metrics")
st.caption("Track engagement and the performance of the leasing workflow.")
metrics = api("/metrics")
a, b, c, d = st.columns(4)
a.metric("Median response", f"{metrics['response_time_minutes'] if metrics['response_time_minutes'] is not None else '—'} min")
b.metric("Lead to tour", f"{float(np.nan_to_num(metrics['lead_to_tour_rate'])):.1f}%")
c.metric("After-hours captured", metrics["after_hours_capture"])
d.metric("Tour show-up", f"{float(np.nan_to_num(metrics['tour_show_up_rate'])):.1f}%")
st.caption(f"Audited workflow events: {metrics['audited_events']}")
