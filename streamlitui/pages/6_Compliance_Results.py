"""
Compliance Results page for portfolio compliance check results.
"""

import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlitui.api_client import api_client
from streamlitui.utils.formatting import format_datetime, format_percentage
from streamlitui.utils.session_state import get_compliance_results, clear_compliance_results

st.title("Compliance Results")
st.markdown("Portfolio compliance check results")

# Get results from session state
results = get_compliance_results()

if not results:
    # Show fund selection UI
    st.markdown("### Run Compliance Check")
    st.markdown("Select a fund to run a compliance check.")
    
    try:
        # Get all funds for selection
        funds = api_client.get_funds()
        
        if not funds:
            st.warning("No funds found. Please create a fund first.")
        else:
            # Create fund selection dropdown
            fund_options = {f"{fund.get('fund_name')} (ID: {fund.get('fund_id')})": fund.get('fund_id') for fund in funds}
            selected_fund_display = st.selectbox(
                "Select a fund to check",
                options = list(fund_options.keys()),
                index = 0 if fund_options else None
            )
            
            selected_fund_id = fund_options.get(selected_fund_display) if selected_fund_display else None
            
            col1, col2 = st.columns([1, 4])
            with col1:
                run_check_button = st.button("Run Compliance Check", type = "primary", use_container_width = True)
            
            if run_check_button and selected_fund_id:
                with st.spinner("Running compliance check..."):
                    try:
                        results = api_client.run_compliance_check(selected_fund_id)
                        if results and results.get('success'):
                            # Store results in session state
                            st.session_state.compliance_results = results
                            st.rerun()
                        else:
                            error_msg = results.get('error', 'Compliance check failed') if results else 'No response from server'
                            st.error(f"Compliance check failed: {error_msg}")
                    except Exception as e:
                        st.error(f"Error running compliance check: {e}")
    except Exception as e:
        st.error(f"Error loading funds: {e}")
else:
    # Display results
    try:
        st.markdown(f"### Fund: {results.get('fund_name', 'N/A')}")
        st.markdown(f"**Rules Checked:** {results.get('rules_checked', 0)}")
        st.markdown(f"**Alerts Found:** {results.get('alerts_count', 0)}")
        st.markdown(f"**Status:** {'Alerted' if results.get('alerted', False) else 'Passed'}")
        
        if results.get('alerts'):
            st.markdown("### Alerts")
            alerts_data = []
            for alert in results.get('alerts', []):
                alerts_data.append({
                    'Rule': alert.get('rule_name', 'N/A'),
                    'Alert Message': alert.get('alert_message', 'N/A'),
                    'Calculated %': format_percentage(alert.get('calculated_percentage', 0)) if alert.get('calculated_percentage') is not None else 'N/A',
                    'Holdings Triggered': alert.get('holdings_triggered', 'N/A')
                })
            
            st.dataframe(alerts_data, width = 'stretch', hide_index = True)
        else:
            st.success("No compliance alerts found. All rules passed.")
        
        st.markdown("---")
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Run Another Check"):
                clear_compliance_results()
                st.rerun()
        
        with col2:
            if st.button("Back to Funds"):
                clear_compliance_results()
                st.switch_page("pages/2_Funds.py")
    
    except Exception as e:
        st.error(f"Error displaying compliance results: {e}")
