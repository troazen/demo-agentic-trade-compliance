"""
Main Streamlit application entry point.
"""

import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlitui.config import PAGE_TITLE, PAGE_ICON, LAYOUT
from streamlitui.utils.session_state import init_session_state

# Configure page
st.set_page_config(
    page_title = PAGE_TITLE,
    page_icon = PAGE_ICON,
    layout = LAYOUT,
    initial_sidebar_state = "expanded"
)

# Initialize session state
init_session_state()

# Main title
st.title("Investment Operations Compliance System")
st.markdown("*Trade and Portfolio Compliance Monitoring System*")

# Display connection status
try:
    from streamlitui.api_client import api_client
    api_client.get_funds()  # Test connection
    st.sidebar.success("✓ Connected to backend API")
except Exception as e:
    st.sidebar.error(f"✗ Cannot connect to backend API: {e}")
    st.warning("Please ensure the backend server is running on http://localhost:5000")

# Main content area - will be handled by page routing
st.info("Please navigate using the sidebar to access different sections.")

# Footer
st.markdown("---")
st.markdown("**Investment Operations Compliance System** v1.0")

