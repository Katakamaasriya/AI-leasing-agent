import sys
from pathlib import Path

# Add project root to Python path for Azure deployment
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import streamlit as st

st.set_page_config(
    page_title="AI Leasing & Tenant Communication Agent", 
    page_icon="🏠", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern CSS styling
st.markdown("""
<style>
    /* Global styles */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    [data-testid="stAppViewContainer"] {
        background: #f8fafc;
    }
    
    [data-testid="stMainBlockContainer"] {
        max-width: 1400px;
        padding: 2rem 2.5rem 3rem;
        background: rgba(255, 255, 255, 0.95);
        border-radius: 16px;
        margin: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        border-right: none;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
        color: #e2e8f0;
    }
    
    /* Typography */
    h1, h2, h3 {
        letter-spacing: -0.025em;
        font-weight: 700;
    }
    
    h1 {
        color: #1e293b;
        margin-bottom: 0.5rem;
        font-size: 2.25rem;
    }
    
    h2, h3 {
        color: #334155;
    }
    
    [data-testid="stCaptionContainer"] {
        color: #64748b;
        font-size: 0.95rem;
    }
    
    /* Cards and containers */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #e2e8f0;
        background: rgba(255, 255, 255, 0.8);
        border-radius: 12px;
        padding: 1.5rem;
    }
    
    /* Metrics */
    [data-testid="stMetric"] {
        padding: 1.25rem 1.5rem;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    [data-testid="stMetricLabel"] {
        color: #64748b;
        font-weight: 600;
        font-size: 0.875rem;
    }
    
    [data-testid="stMetricValue"] {
        color: #0f766e;
        font-weight: 700;
        font-size: 1.875rem;
    }
    
    /* Dataframes */
    [data-testid="stDataFrame"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    /* Chat messages */
    [data-testid="stChatMessage"] {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        margin-bottom: 1rem;
        background: #ffffff;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    
    [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p {
        line-height: 1.6;
    }
    
    /* Buttons */
    button[kind="primary"] {
        background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
        color: white;
        font-weight: 600;
        border-radius: 8px;
        transition: all 0.2s;
    }
    
    button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(15, 118, 110, 0.4);
    }
    
    /* Form elements */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    textarea {
        background: #ffffff;
        border-color: #cbd5e1;
        border-radius: 8px;
    }
    
    div[data-baseweb="select"] > div:focus,
    div[data-baseweb="input"] > div:focus,
    textarea:focus {
        border-color: #0f766e;
        box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.1);
    }
    
    /* Responsive design */
    @media (max-width: 800px) {
        [data-testid="stMainBlockContainer"] {
            padding: 1.5rem 1rem 2rem;
            margin: 0.5rem;
        }
        
        h1 {
            font-size: 1.75rem;
        }
        
        [data-testid="stMetric"] {
            padding: 1rem;
        }
    }
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #f1f5f9;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #cbd5e1;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)
pages = st.navigation([
    st.Page("app_pages/availability.py", title="Live availability", icon="🏠"),
    st.Page("app_pages/properties.py", title="Properties", icon="🏢"),
    st.Page("app_pages/units.py", title="Units", icon="🚪"),
    st.Page("app_pages/leads.py", title="Leads", icon="👤"),
    st.Page("app_pages/ai_agent.py", title="AI leasing agent", icon="🤖"),
    st.Page("app_pages/qualification.py", title="Qualification & handoff", icon="✅"),
    st.Page("app_pages/tours.py", title="Tours", icon="📅"),
    st.Page("app_pages/metrics.py", title="Team metrics", icon="📊"),
])

with st.sidebar:
    st.markdown("<div style='text-align: center; padding: 20px 0;'><h1 style='color: white; font-size: 1.5rem; margin: 0;'>🏠 AI Leasing Agent</h1><p style='color: #94a3b8; font-size: 0.875rem; margin: 8px 0 0;'>24/7 Intelligent Property Assistant</p></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("<div style='padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px; margin: 10px 0;'><p style='color: #e2e8f0; font-size: 0.8rem; margin: 0;'>✨ AI-Powered</p><p style='color: #94a3b8; font-size: 0.75rem; margin: 4px 0 0;'>Azure OpenAI Integration</p></div>", unsafe_allow_html=True)
    
    st.markdown("<div style='padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px; margin: 10px 0;'><p style='color: #e2e8f0; font-size: 0.8rem; margin: 0;'>📧 Multi-Channel</p><p style='color: #94a3b8; font-size: 0.75rem; margin: 4px 0 0;'>Email & Web Chat</p></div>", unsafe_allow_html=True)
    
    st.markdown("<div style='padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px; margin: 10px 0;'><p style='color: #e2e8f0; font-size: 0.8rem; margin: 0;'>📅 Smart Scheduling</p><p style='color: #94a3b8; font-size: 0.75rem; margin: 4px 0 0;'>Microsoft 365 Calendar</p></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.caption("🚀 Production-Ready Deployment")
    st.caption("☁️ Azure Cloud Native")
    st.caption("🔒 Enterprise Security")

pages.run()
