"""
Dashboard page with summary statistics and recent activity.
"""

import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlitui.api_client import api_client
from streamlitui.utils.formatting import format_currency, format_datetime

st.title("Dashboard")
st.markdown("Overview of funds, securities, rules, and recent activity")

try:
    # Get summary data
    funds = api_client.get_funds()
    securities = api_client.get_securities()
    rules = api_client.get_rules()
    
    # Filter active rules
    active_rules = [r for r in rules if r.get('active', False)]
    
    # Calculate total assets
    total_assets = sum(f.get('cash', 0) for f in funds)
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Funds", len(funds))
    
    with col2:
        st.metric("Total Securities", len(securities))
    
    with col3:
        st.metric("Active Rules", len(active_rules))
    
    with col4:
        st.metric("Total Assets", format_currency(total_assets))
    
    st.markdown("---")
    
    # Recent alerts
    st.subheader("Recent Alerts")
    try:
        alerts = api_client.get_alerts(limit = 10)
        
        if alerts:
            alerts_data = []
            for alert in alerts[:10]:
                alerts_data.append({
                    'Alert ID': alert.get('alert_id'),
                    'Fund': alert.get('fund_name', 'N/A'),
                    'Rule': alert.get('rule_name', 'N/A'),
                    'Status': alert.get('status', 'N/A'),
                    'Calculated %': f"{alert.get('calculated_percentage', 0):.2f}%" if alert.get('calculated_percentage') is not None else '-',
                    'Created': format_datetime(alert.get('created_at'))
                })
            
            st.dataframe(alerts_data, use_container_width = True, hide_index = True)
        else:
            st.info("No recent alerts")
    except Exception as e:
        st.error(f"Error loading alerts: {e}")
    
    st.markdown("---")
    
    # Recent trades
    st.subheader("Recent Trades")
    try:
        trades = api_client.get_alerts(limit = 10)
        
        if trades:
            trades_data = []
            for trade in trades[:10]:
                trades_data.append({
                    'Trade ID': trade.get('trade_id'),
                    'Fund': trade.get('fund_name', 'N/A'),
                    'Ticker': trade.get('ticker', 'N/A'),
                    'Direction': trade.get('direction', 'N/A'),
                    'Shares': trade.get('shares', 0),
                    'Status': trade.get('status', 'N/A'),
                    'Created': format_datetime(trade.get('created_at'))
                })
            
            st.dataframe(trades_data, use_container_width = True, hide_index = True)
        else:
            st.info("No recent trades")
    except Exception as e:
        st.error(f"Error loading trades: {e}")

except Exception as e:
    st.error(f"Error loading dashboard data: {e}")

