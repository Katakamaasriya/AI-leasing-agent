import os
import requests
import streamlit as st

API = os.getenv("LEASING_API_URL", "http://127.0.0.1:8000")

def api(path, method="get", **kwargs):
    timeout = kwargs.pop("timeout", 30)
    response = getattr(requests, method)(f"{API}{path}", timeout=timeout, **kwargs)
    response.raise_for_status()
    return response.json()

def properties_or_stop():
    try:
        return api("/properties")
    except requests.RequestException:
        st.error("The API is offline. In another terminal run: python -m uvicorn backend.main:app --reload")
        st.stop()

def select_property(label="Property"):
    properties = properties_or_stop()
    if not properties:
        st.info("Add a property first.")
        st.stop()
    return st.selectbox(label, properties, format_func=lambda item: f"{item['name']} — {item['address']}")
