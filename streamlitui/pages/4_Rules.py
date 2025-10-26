"""
Rules page for managing compliance rules.
"""

import streamlit as st
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlitui.api_client import api_client
from streamlitui.utils.formatting import format_datetime, format_percentage, format_boolean

st.title("Compliance Rules")
st.markdown("Manage compliance rules for funds")

# Filters
col1, col2 = st.columns(2)

with col1:
    fund_filter = st.text_input("Filter by fund name (leave empty for all)")
    show_unattached = st.checkbox("Show unattached rules", value = False)

with col2:
    rule_search = st.text_input("Search by rule name")

try:
    # Get all rules
    all_rules = api_client.get_rules(search_query = rule_search if rule_search else None)
    
    # Filter by fund
    filtered_rules = []
    if fund_filter:
        for rule in all_rules:
            # Check if rule is attached to matching fund
            attached_funds = rule.get('attached_funds', [])
            if any(fund_filter.lower() in str(f.get('fund_name', '')).lower() for f in attached_funds):
                filtered_rules.append(rule)
            elif show_unattached and not attached_funds:
                filtered_rules.append(rule)
    else:
        if show_unattached:
            filtered_rules = [r for r in all_rules if not r.get('attached_funds')]
        else:
            filtered_rules = all_rules
    
    if not filtered_rules:
        st.info("No rules found matching the filters.")
        return
    
    # Display rules in a table
    rules_data = []
    for rule in filtered_rules:
        rules_data.append({
            'Rule ID': rule.get('rule_id'),
            'Rule Name': rule.get('rule_name'),
            'Denominator': rule.get('denominator', 'N/A'),
            'Alert If': rule.get('alert_if', 'N/A'),
            'Alert Level': f"{rule.get('alert_level', 0):.2f}%" if rule.get('alert_level') is not None else 'N/A',
            'Trade Mode': format_boolean(rule.get('trade_compliance_mode', False)),
            'Portfolio Mode': format_boolean(rule.get('portfolio_compliance_mode', False)),
            'Active': format_boolean(rule.get('active', False)),
            'Attached Funds': len(rule.get('attached_funds', [])),
            'Created': format_datetime(rule.get('created_at'))
        })
    
    st.dataframe(rules_data, use_container_width = True, hide_index = True)
    
    # Rule details
    st.markdown("---")
    st.subheader("Rule Details")
    
    selected_rule_id = st.selectbox(
        "Select a rule to view details",
        options = [r.get('rule_id') for r in filtered_rules],
        format_func = lambda x: next((f"{r['rule_name']} (ID: {r['rule_id']})" for r in filtered_rules if r['rule_id'] == x), f'Rule {x}')
    )
    
    if selected_rule_id:
        try:
            rule_details = api_client.get_rule(selected_rule_id)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Rule Name:** {rule_details.get('rule_name')}")
                st.markdown(f"**Alert Message:** {rule_details.get('alert_message', 'N/A')}")
                st.markdown(f"**Denominator:** {rule_details.get('denominator', 'N/A')}")
                st.markdown(f"**Alert If:** {rule_details.get('alert_if', 'N/A')}")
                st.markdown(f"**Alert Level:** {format_percentage(rule_details.get('alert_level', 0)) if rule_details.get('alert_level') is not None else 'N/A'}")
            
            with col2:
                st.markdown(f"**Trade Mode:** {format_boolean(rule_details.get('trade_compliance_mode', False))}")
                st.markdown(f"**Portfolio Mode:** {format_boolean(rule_details.get('portfolio_compliance_mode', False))}")
                st.markdown(f"**Active:** {format_boolean(rule_details.get('active', False))}")
                st.markdown(f"**Logic:** {rule_details.get('logic', 'N/A')}")
            
            # Attached funds
            if rule_details.get('attached_funds'):
                st.markdown("### Attached Funds")
                for fund in rule_details.get('attached_funds', []):
                    st.markdown(f"- {fund.get('fund_name', 'N/A')} (ID: {fund.get('fund_id')})")
            else:
                st.info("This rule is not attached to any funds.")
        
        except Exception as e:
            st.error(f"Error loading rule details: {e}")

except Exception as e:
    st.error(f"Error loading rules: {e}")

