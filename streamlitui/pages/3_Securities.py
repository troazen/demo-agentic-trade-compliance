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
        st.markdown("*Select a security from the table below to view details*")
        
        # Prepare securities data for dataframe
        securities_data = []
        for security in securities:
            securities_data.append({
                'Ticker': security.get('ticker', 'N/A'),
                'Name': security.get('name', 'N/A'),
                'Issuer': security.get('issuer_name', 'N/A'),
                'Type': security.get('type', 'N/A'),
                'Price': format_currency(security.get('current_price', 0)),
                'Shares': format_shares(security.get('shares_outstanding', 0)),
                'Market Cap': format_currency(security.get('market_cap', 0))
            })
        
        # Display securities in a scrollable dataframe
        st.dataframe(
            securities_data,
            width = 'stretch',
            height = 400,
            hide_index = True
        )
        
        # Security selection dropdown
        st.markdown("---")
        security_options = {f"{s.get('ticker')} - {s.get('name', 'N/A')}": s.get('ticker') for s in securities}
        selected_security_display = st.selectbox(
            "Select a security to view details",
            options = list(security_options.keys()),
            index = 0 if security_options else None,
            key = "security_selector"
        )
        
        if selected_security_display:
            selected_ticker = security_options.get(selected_security_display)
            if selected_ticker:
                st.session_state.selected_security_ticker = selected_ticker
        
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
