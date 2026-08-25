import streamlit as st

st.set_page_config(page_title="AI Leasing & Tenant Communication Agent", page_icon=":material/apartment:", layout="wide")
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] {
        background: #f7f8f5;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 1380px;
        padding: 2.2rem 3.2rem 4rem;
    }
    [data-testid="stSidebar"] {
        border-right: 1px solid #d0ddd7;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #52616b;
    }
    h1, h2, h3 {
        letter-spacing: 0;
    }
    h1 {
        color: #17212b;
        margin-bottom: 0.35rem;
    }
    h2, h3 {
        color: #24434a;
    }
    [data-testid="stCaptionContainer"] {
        color: #66737d;
    }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #d7e0dc;
        background: rgba(255, 255, 255, 0.58);
    }
    [data-testid="stMetric"] {
        padding: 1rem 1.1rem;
        border: 1px solid #d7e0dc;
        border-radius: 8px;
        background: #ffffff;
    }
    [data-testid="stMetricLabel"] {
        color: #66737d;
    }
    [data-testid="stMetricValue"] {
        color: #0f766e;
    }
    [data-testid="stDataFrame"] {
        border: 1px solid #d7e0dc;
        border-radius: 8px;
        overflow: hidden;
    }
    [data-testid="stChatMessage"] {
        border: 1px solid #e1e8e4;
        border-radius: 8px;
        margin-bottom: 0.7rem;
        background: #ffffff;
    }
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
        line-height: 1.55;
    }
    button[kind="primary"] {
        font-weight: 600;
    }
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    textarea {
        background: #ffffff;
    }
    @media (max-width: 800px) {
        [data-testid="stMainBlockContainer"] {
            padding: 1.4rem 1rem 3rem;
        }
        h1 {
            font-size: 30px;
        }
    }
</style>
""", unsafe_allow_html=True)
pages = st.navigation([
    st.Page("app_pages/availability.py", title="Live availability", icon=":material/home_work:"),
    st.Page("app_pages/properties.py", title="Properties", icon=":material/apartment:"),
    st.Page("app_pages/units.py", title="Units", icon=":material/door_front:"),
    st.Page("app_pages/leads.py", title="Leads", icon=":material/person_add:"),
    st.Page("app_pages/ai_agent.py", title="AI leasing agent", icon=":material/robot_2:"),
    st.Page("app_pages/qualification.py", title="Qualification & handoff", icon=":material/fact_check:"),
    st.Page("app_pages/tours.py", title="Tours", icon=":material/event:"),
    st.Page("app_pages/metrics.py", title="Team metrics", icon=":material/monitoring:"),
])
with st.sidebar:
    st.caption("AI Leasing & Tenant Communication Agent")
    st.caption("Manual inventory is the current source of truth.")
pages.run()
