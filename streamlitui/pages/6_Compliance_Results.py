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
    st.warning("No compliance results available. Please run a compliance check from the Funds page.")
    
    # Allow manual entry for testing
    if st.checkbox("Enter test fund ID"):
        test_fund_id = st.number_input("Fund ID", min_value = 1, value = 1)
        if st.button("Run Compliance Check"):
            try:
                results = api_client.run_compliance_check(test_fund_id)
                if results:
                    st.session_state.compliance_results = results
                    st.rerun()
            except Exception as e:
                st.error(f"Error running compliance check: {e}")
    return

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
        
        st.dataframe(alerts_data, use_container_width = True, hide_index = True)
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

