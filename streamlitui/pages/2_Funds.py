"""
Funds page for viewing and managing funds.
"""

import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlitui.api_client import api_client
from streamlitui.utils.formatting import format_currency, format_datetime

st.title("Funds")
st.markdown("View and manage investment funds")

try:
    # Get all funds
    funds = api_client.get_funds()
    
    if not funds:
        st.info("No funds found. Create a fund to get started.")
    else:
        # Display funds in a table
        funds_data = []
        for fund in funds:
            funds_data.append({
                'Fund ID': fund.get('fund_id'),
                'Fund Name': fund.get('fund_name'),
                'Cash': format_currency(fund.get('cash', 0)),
                'Holdings Count': fund.get('holdings_count', 0),
                'Created': format_datetime(fund.get('created_at'))
            })
        
        st.dataframe(funds_data, use_container_width = True, hide_index = True)
        
        # Selected fund details
        st.markdown("---")
        st.subheader("Fund Details")
        
        selected_fund_id = st.selectbox(
            "Select a fund to view details",
            options = [f.get('fund_id') for f in funds],
            format_func = lambda x: next((f['fund_name'] for f in funds if f['fund_id'] == x), f'Fund {x}')
        )
        
        if selected_fund_id:
            try:
                fund_details = api_client.get_fund(selected_fund_id)
                
                if not fund_details:
                    st.warning(f"Fund details not found for fund ID '{selected_fund_id}'. The fund may not exist in the database or may be missing required data.")
                else:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Fund Name", fund_details.get('fund_name', 'N/A'))
                        st.metric("Cash", format_currency(fund_details.get('cash', 0)))
                    
                    with col2:
                        st.metric("Holdings", fund_details.get('holdings_count', 0))
                        st.metric("Created", format_datetime(fund_details.get('created_at')))
                    
                    # Holdings table
                    if fund_details.get('holdings'):
                        st.markdown("### Holdings")
                        holdings_data = []
                        for holding in fund_details.get('holdings', []):
                            holdings_data.append({
                                'Ticker': holding.get('ticker') if isinstance(holding, dict) else 'N/A',
                                'Name': holding.get('name', 'N/A') if isinstance(holding, dict) else 'N/A',
                                'Shares': holding.get('shares', 0) if isinstance(holding, dict) else 0,
                                'Price': format_currency(holding.get('current_price', 0)) if isinstance(holding, dict) else format_currency(0),
                                'Market Value': format_currency(holding.get('market_value', 0)) if isinstance(holding, dict) else format_currency(0)
                            })
                        
                        st.dataframe(holdings_data, use_container_width = True, hide_index = True)
            
            except Exception as e:
                st.error(f"Error loading fund details: {e}")

except Exception as e:
    st.error(f"Error loading funds: {e}")
