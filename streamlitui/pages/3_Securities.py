"""
Securities page for viewing and searching securities.
"""

import streamlit as st
import sys
import os
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlitui.api_client import api_client
from streamlitui.utils.formatting import format_currency, format_datetime, format_shares

st.title("Securities")
st.markdown("View and search available securities")

# Initialize session state for selected ticker
if 'selected_security_ticker' not in st.session_state:
    st.session_state.selected_security_ticker = None

# Search bar
search_query = st.text_input("Search by ticker or issuer name", value = "")

try:
    if search_query:
        securities = api_client.search_securities(search_query)
    else:
        securities = api_client.get_securities()
    
    if not securities:
        st.info("No securities found.")
    else:
        st.markdown("### Securities List")
        st.markdown("*Click a 'View' button to see details below*")
        
        # Create a scrollable container using CSS
        # Inject CSS that will make the container scrollable
        st.markdown("""
            <style>
            .securities-table-wrapper {
                max-height: 50vh;
                overflow-y: auto;
                overflow-x: hidden;
                border: 1px solid rgba(250, 250, 250, 0.2);
                border-radius: 0.5rem;
                padding: 1rem;
                margin: 1rem 0;
            }
            </style>
        """, unsafe_allow_html = True)
        
        # Start the scrollable wrapper
        st.markdown('<div class="securities-table-wrapper">', unsafe_allow_html = True)
        
        # Display header row
        header_cols = st.columns([1, 3, 2, 1, 2, 2, 2, 1])
        with header_cols[0]:
            st.markdown("**Ticker**")
        with header_cols[1]:
            st.markdown("**Name**")
        with header_cols[2]:
            st.markdown("**Issuer**")
        with header_cols[3]:
            st.markdown("**Type**")
        with header_cols[4]:
            st.markdown("**Price**")
        with header_cols[5]:
            st.markdown("**Shares**")
        with header_cols[6]:
            st.markdown("**Market Cap**")
        with header_cols[7]:
            st.markdown("**Action**")
        
        st.markdown("---")
        
        # Display securities in rows with buttons
        for idx, security in enumerate(securities):
            ticker = security.get('ticker')
            
            # Create columns for the row
            cols = st.columns([1, 3, 2, 1, 2, 2, 2, 1])
            
            with cols[0]:
                st.write(f"**{ticker}**")
            with cols[1]:
                st.write(security.get('name', 'N/A'))
            with cols[2]:
                st.write(security.get('issuer_name', 'N/A'))
            with cols[3]:
                st.write(security.get('type', 'N/A'))
            with cols[4]:
                st.write(format_currency(security.get('current_price', 0)))
            with cols[5]:
                st.write(format_shares(security.get('shares_outstanding', 0)))
            with cols[6]:
                st.write(format_currency(security.get('market_cap', 0)))
            with cols[7]:
                if st.button("View", key = f"view_{ticker}_{idx}", use_container_width = True):
                    st.session_state.selected_security_ticker = ticker
                    st.rerun()
        
        # Close the scrollable wrapper
        st.markdown('</div>', unsafe_allow_html = True)
        
        # Clear selection button
        if st.session_state.selected_security_ticker:
            if st.button("Clear Selection"):
                st.session_state.selected_security_ticker = None
                st.rerun()
        
        # Detailed view based on selected ticker
        selected_ticker = st.session_state.selected_security_ticker
        
        if selected_ticker:
            st.markdown("---")
            st.subheader(f"Security Details: {selected_ticker}")
            
            try:
                security_details = api_client.get_security(selected_ticker)
                
                if not security_details:
                    st.warning(f"Security details not found for ticker '{selected_ticker}'. The security may not exist in the database or may be missing required data.")
                else:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Ticker:** {security_details.get('ticker', 'N/A')}")
                        st.markdown(f"**Name:** {security_details.get('name', 'N/A')}")
                        st.markdown(f"**Type:** {security_details.get('type', 'N/A')}")
                        st.markdown(f"**Price:** {format_currency(security_details.get('current_price', 0))}")
                    
                    with col2:
                        st.markdown(f"**Issuer:** {security_details.get('issuer_name', 'N/A')}")
                        st.markdown(f"**Shares Outstanding:** {format_shares(security_details.get('shares_outstanding', 0))}")
                        st.markdown(f"**Market Cap:** {format_currency(security_details.get('market_cap', 0))}")
                    
                    # Issuer details
                    if security_details.get('issuer'):
                        st.markdown("### Issuer Information")
                        issuer = security_details.get('issuer')
                        
                        issuer_col1, issuer_col2 = st.columns(2)
                        
                        with issuer_col1:
                            st.markdown(f"**GICS Sector:** {issuer.get('gics_sector', 'N/A') if isinstance(issuer, dict) else 'N/A'}")
                            st.markdown(f"**GICS Industry:** {issuer.get('gics_industry', 'N/A') if isinstance(issuer, dict) else 'N/A'}")
                        
                        with issuer_col2:
                            st.markdown(f"**Country:** {issuer.get('country_domicile', 'N/A') if isinstance(issuer, dict) else 'N/A'}")
                            st.markdown(f"**Incorporation:** {issuer.get('country_incorporation', 'N/A') if isinstance(issuer, dict) else 'N/A'}")
            
            except Exception as e:
                st.error(f"Error loading security details: {e}")

except Exception as e:
    st.error(f"Error loading securities: {e}")
