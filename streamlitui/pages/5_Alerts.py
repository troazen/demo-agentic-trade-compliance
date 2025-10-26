"""
Alerts page for viewing and managing compliance alerts.
"""

import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlitui.api_client import api_client
from streamlitui.utils.formatting import format_datetime, format_percentage

st.title("Alerts")
st.markdown("View and manage compliance rule alerts")

# Filters
col1, col2, col3 = st.columns(3)

with col1:
    fund_filter = st.selectbox(
        "Filter by fund",
        options = ['All'] + [str(f) for f in api_client.get_funds()]
    )

with col2:
    status_filter = st.selectbox(
        "Filter by status",
        options = ['All', 'Pending', 'Overridden', 'Cancelled']
    )

with col3:
    limit_filter = st.number_input("Limit results", min_value = 10, max_value = 1000, value = 100)

try:
    # Prepare filters
    fund_id = None if fund_filter == 'All' else int(fund_filter.split('(')[0])
    status = None if status_filter == 'All' else status_filter.lower()
    
    # Get alerts
    alerts = api_client.get_alerts(fund_id = fund_id, status = status, limit = limit_filter)
    
    if not alerts:
        st.info("No alerts found matching the filters.")
        return
    
    # Display alerts in a table
    alerts_data = []
    for alert in alerts:
        alerts_data.append({
            'Alert ID': alert.get('alert_id'),
            'Fund': alert.get('fund_name', 'N/A'),
            'Rule': alert.get('rule_name', 'N/A'),
            'Trade ID': alert.get('trade_id', 'N/A'),
            'Calculated %': format_percentage(alert.get('calculated_percentage', 0)) if alert.get('calculated_percentage') is not None else 'N/A',
            'Status': alert.get('status', 'N/A'),
            'Override Reason': alert.get('override_reason', 'N/A')[:50] if alert.get('override_reason') else 'N/A',
            'Created': format_datetime(alert.get('created_at'))
        })
    
    st.dataframe(alerts_data, use_container_width = True, hide_index = True)
    
    # Detailed view
    st.markdown("---")
    st.subheader("Alert Details")
    
    selected_alert_id = st.selectbox(
        "Select an alert to view details",
        options = [a.get('alert_id') for a in alerts],
        key = "alert_selector"
    )
    
    if selected_alert_id:
        try:
            alert_details = api_client.get_alert(selected_alert_id)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Alert ID:** {alert_details.get('alert_id')}")
                st.markdown(f"**Fund:** {alert_details.get('fund_name', 'N/A')}")
                st.markdown(f"**Rule:** {alert_details.get('rule_name', 'N/A')}")
                st.markdown(f"**Trade ID:** {alert_details.get('trade_id', 'N/A')}")
            
            with col2:
                st.markdown(f"**Status:** {alert_details.get('status', 'N/A')}")
                st.markdown(f"**Calculated %:** {format_percentage(alert_details.get('calculated_percentage', 0)) if alert_details.get('calculated_percentage') is not None else 'N/A'}")
                st.markdown(f"**Created:** {format_datetime(alert_details.get('created_at'))}")
            
            if alert_details.get('override_reason'):
                st.markdown(f"**Override Reason:** {alert_details.get('override_reason')}")
        
        except Exception as e:
            st.error(f"Error loading alert details: {e}")

except Exception as e:
    st.error(f"Error loading alerts: {e}")

