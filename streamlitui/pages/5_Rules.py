"""
Rules page for managing compliance rules.
"""

import streamlit as st
import sys
import os
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlitui.api_client import api_client
from streamlitui.utils.formatting import format_datetime, format_percentage, format_boolean

logger = logging.getLogger(__name__)


def _render_rule_form(rule_to_edit = None):
    """Render the rule creation/editing form."""
    is_edit_mode = rule_to_edit is not None
    
    # Initialize session state for rule name validation
    form_key = f"rule_form_{rule_to_edit.get('rule_id') if rule_to_edit else 'new'}"
    if f'{form_key}_last_checked_name' not in st.session_state:
        st.session_state[f'{form_key}_last_checked_name'] = None
    if f'{form_key}_name_error' not in st.session_state:
        st.session_state[f'{form_key}_name_error'] = None
    if f'{form_key}_name_validated' not in st.session_state:
        st.session_state[f'{form_key}_name_validated'] = False
    
    with st.form("rule_form", clear_on_submit = False):
        # Basic information
        col1, col2 = st.columns([3, 1])
        
        with col1:
            rule_name = st.text_input(
                "Rule Name *",
                value = rule_to_edit.get('rule_name', '') if rule_to_edit else '',
                help = "Unique name for this compliance rule",
                key = f"{form_key}_rule_name_input"
            )
        
        with col2:
            # Check name button
            check_name_button = st.form_submit_button("Check Name", use_container_width = True)
        
        # Check rule name if button clicked or if name has changed
        rule_name_stripped = rule_name.strip() if rule_name else ''
        should_check = False
        
        if check_name_button:
            should_check = True
        elif rule_name_stripped and rule_name_stripped != st.session_state[f'{form_key}_last_checked_name']:
            # Only check if name is different from what we last checked and not the original name
            original_name = rule_to_edit.get('rule_name', '') if rule_to_edit else ''
            if rule_name_stripped != original_name:
                should_check = True
        
        if should_check and rule_name_stripped:
            # Check name availability
            try:
                exclude_id = rule_to_edit.get('rule_id') if rule_to_edit else None
                name_check = api_client.check_rule_name(rule_name_stripped, exclude_rule_id = exclude_id)
                
                if not name_check.get('available', True):
                    st.session_state[f'{form_key}_name_error'] = name_check.get('message', 'Rule name already exists')
                    st.session_state[f'{form_key}_name_validated'] = True
                else:
                    st.session_state[f'{form_key}_name_error'] = None
                    st.session_state[f'{form_key}_name_validated'] = True
                
                st.session_state[f'{form_key}_last_checked_name'] = rule_name_stripped
            except Exception as e:
                # Don't block on check errors, just log
                logger.warning(f"Error checking rule name: {e}")
                st.session_state[f'{form_key}_name_error'] = None
        
        # Show validation error if exists
        name_error = st.session_state.get(f'{form_key}_name_error')
        if name_error:
            st.error(f"⚠️ {name_error}")
        elif st.session_state.get(f'{form_key}_name_validated') and rule_name_stripped and not name_error:
            st.success("✓ Rule name is available")
        
        alert_message = st.text_area(
            "Alert Message *",
            value = rule_to_edit.get('alert_message', '') if rule_to_edit else '',
            help = "Message displayed when this rule triggers an alert"
        )
        
        # Denominator selection
        denominator_options = {
            'total_assets': 'Total Assets',
            'net_assets': 'Net Assets',
            'total_assets_ex_cash': 'Total Assets Ex Cash',
            'prohibit': 'Prohibit',
            'shares_outstanding_fe': 'Shares Outstanding (For Each)'
        }
        
        current_denominator = rule_to_edit.get('denominator', 'total_assets') if rule_to_edit else 'total_assets'
        denominator = st.selectbox(
            "Denominator *",
            options = list(denominator_options.keys()),
            format_func = lambda x: denominator_options[x],
            index = list(denominator_options.keys()).index(current_denominator) if current_denominator in denominator_options else 0
        )
        
        is_prohibit = (denominator == 'prohibit')
        
        # Alert configuration (not for prohibit rules)
        col1, col2 = st.columns(2)
        
        with col1:
            if not is_prohibit:
                alert_if_options = ['above', 'below']
                current_alert_if = rule_to_edit.get('alert_if', 'above') if rule_to_edit else 'above'
                alert_if = st.selectbox(
                    "Alert If *",
                    options = alert_if_options,
                    index = alert_if_options.index(current_alert_if) if current_alert_if in alert_if_options else 0,
                    help = "Alert when percentage is above or below the threshold"
                )
            else:
                alert_if = None
                # Show disabled selectbox to indicate it's not used
                st.selectbox(
                    "Alert If",
                    options = ['above', 'below'],
                    index = 0,
                    disabled = True,
                    help = "Prohibit rules don't use alert conditions"
                )
                st.caption("ℹ️ Prohibit rules don't use alert conditions")
        
        with col2:
            if not is_prohibit:
                current_alert_level = rule_to_edit.get('alert_level', 0.0) if rule_to_edit else 0.0
                alert_level = st.number_input(
                    "Alert Level (%) *",
                    min_value = 0.0,
                    max_value = 100.0,
                    value = float(current_alert_level) if current_alert_level is not None else 0.0,
                    step = 0.1,
                    help = "Percentage threshold for triggering alerts"
                )
            else:
                alert_level = None
                # Show disabled input with placeholder to indicate it's not used
                st.number_input(
                    "Alert Level (%)",
                    min_value = 0.0,
                    max_value = 100.0,
                    value = 0.0,
                    step = 0.1,
                    disabled = True,
                    help = "Prohibit rules don't use alert levels"
                )
                st.caption("ℹ️ Prohibit rules don't use alert levels")
        
        # Rule logic
        st.markdown("### Rule Logic")
        st.markdown("Enter SQL WHERE clause logic (without the WHERE keyword). Leave empty to apply to all securities.")
        
        # Schema viewer button
        col1, col2 = st.columns([1, 1])
        with col1:
            show_schema_button = st.form_submit_button("📋 Show Database Schema", use_container_width = True)
        with col2:
            validate_button = st.form_submit_button("🔍 Validate Logic", use_container_width = True)
        
        # Show schema if button clicked
        if show_schema_button:
            try:
                schema_response = api_client.get_database_schema()
                if schema_response and schema_response.get('success'):
                    schema_dataframe = schema_response.get('schema_dataframe', [])
                    if schema_dataframe:
                        st.markdown("#### Database Schema")
                        st.markdown("*Use this reference when writing SQL logic for rules*")
                        st.dataframe(
                            schema_dataframe,
                            width = 'stretch',
                            height = 400,
                            hide_index = True
                        )
                    else:
                        st.warning("No schema information available")
                else:
                    error_msg = schema_response.get('error', 'Failed to load schema') if schema_response else 'No response from server'
                    st.error(f"Failed to load database schema: {error_msg}")
            except Exception as e:
                st.error(f"Error loading database schema: {e}")
        
        current_logic = rule_to_edit.get('logic', '') if rule_to_edit else ''
        logic = st.text_area(
            "SQL Logic",
            value = current_logic if current_logic else '',
            height = 150,
            help = "SQL WHERE clause logic. Example: issuers.gics_sector = 'Information Technology'"
        )
        if validate_button:
            if logic and logic.strip():
                validation_result = api_client.validate_rule_logic(logic)
                if validation_result.get('valid', False):
                    st.success("✓ Logic is valid")
                else:
                    st.error(f"✗ Logic validation failed: {validation_result.get('error', 'Unknown error')}")
            else:
                st.info("Empty logic is valid (applies to all securities)")
        
        # Mode flags
        st.markdown("### Compliance Modes")
        col1, col2 = st.columns(2)
        
        with col1:
            trade_mode = st.checkbox(
                "Trade Compliance Mode",
                value = rule_to_edit.get('trade_compliance_mode', True) if rule_to_edit else True,
                help = "Run this rule when trades are placed"
            )
        
        with col2:
            portfolio_mode = st.checkbox(
                "Portfolio Compliance Mode",
                value = rule_to_edit.get('portfolio_compliance_mode', True) if rule_to_edit else True,
                help = "Run this rule during batch portfolio compliance checks"
            )
        
        # Fund attachments
        st.markdown("### Fund Attachments")
        try:
            all_funds = api_client.get_funds()
            fund_options = {f.get('fund_id'): f.get('fund_name') for f in all_funds}
            
            current_attached_funds = rule_to_edit.get('attached_funds', []) if rule_to_edit else []
            current_fund_ids = [f.get('fund_id') for f in current_attached_funds if isinstance(f, dict)]
            
            selected_fund_ids = st.multiselect(
                "Attach to Funds",
                options = list(fund_options.keys()),
                default = current_fund_ids,
                format_func = lambda x: fund_options.get(x, f'Fund {x}'),
                help = "Select funds this rule should apply to"
            )
        except Exception as e:
            st.error(f"Error loading funds: {e}")
            selected_fund_ids = []
        
        # Form buttons
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            submit_button = st.form_submit_button("💾 Save Rule", use_container_width = True)
        
        with col2:
            cancel_button = st.form_submit_button("❌ Cancel", use_container_width = True)
        
        if submit_button:
            # Validate required fields
            if not rule_name or not rule_name.strip():
                st.error("Rule name is required")
            elif name_error:
                # Don't allow submission if rule name already exists
                st.error(f"Cannot save: {name_error}")
            elif not alert_message or not alert_message.strip():
                st.error("Alert message is required")
            elif not is_prohibit and alert_level is None:
                st.error("Alert level is required for non-prohibit rules")
            else:
                try:
                    # Prepare logic (empty string if None or empty)
                    logic_value = logic.strip() if logic and logic.strip() else None
                    
                    # Prepare alert_level (None for prohibit rules)
                    alert_level_value = None if is_prohibit else alert_level
                    alert_if_value = None if is_prohibit else alert_if
                    
                    if is_edit_mode:
                        # Update existing rule
                        success = api_client.update_rule(
                            rule_id = rule_to_edit.get('rule_id'),
                            rule_name = rule_name.strip(),
                            alert_message = alert_message.strip(),
                            logic = logic_value,
                            denominator = denominator,
                            alert_if = alert_if_value,
                            alert_level = alert_level_value,
                            trade_compliance_mode = trade_mode,
                            portfolio_compliance_mode = portfolio_mode
                        )
                        
                        if success:
                            st.success("Rule updated successfully!")
                            
                            # Update fund attachments
                            rule_id = rule_to_edit.get('rule_id')
                            
                            # Get current attachments
                            current_attached = set(current_fund_ids)
                            new_attached = set(selected_fund_ids)
                            
                            # Detach funds that were removed
                            to_detach = current_attached - new_attached
                            if to_detach:
                                api_client.detach_rule_from_funds(rule_id, list(to_detach))
                            
                            # Attach funds that were added
                            to_attach = new_attached - current_attached
                            if to_attach:
                                api_client.attach_rule_to_funds(rule_id, list(to_attach))
                            
                            st.session_state.show_rule_form = False
                            st.session_state.editing_rule_id = None
                            st.rerun()
                        else:
                            st.error("Failed to update rule. Please check the error messages above.")
                    else:
                        # Create new rule
                        try:
                            new_rule = api_client.create_rule(
                                rule_name = rule_name.strip(),
                                alert_message = alert_message.strip(),
                                denominator = denominator,
                                logic = logic_value,
                                alert_if = alert_if_value,
                                alert_level = alert_level_value,
                                trade_compliance_mode = trade_mode,
                                portfolio_compliance_mode = portfolio_mode
                            )
                            
                            if new_rule:
                                st.success("Rule created successfully!")
                                
                                # Attach to selected funds
                                rule_id = new_rule.get('rule_id')
                                if rule_id and selected_fund_ids:
                                    api_client.attach_rule_to_funds(rule_id, selected_fund_ids)
                                
                                st.session_state.show_rule_form = False
                                st.session_state.editing_rule_id = None
                                st.rerun()
                            else:
                                st.error("Failed to create rule. Rule name may already exist or validation failed.")
                        except Exception as e:
                            # The exception message should contain the specific error from the API
                            error_msg = str(e)
                            st.error(f"Failed to create rule: {error_msg}")
                
                except Exception as e:
                    st.error(f"Error saving rule: {e}")
        
        if cancel_button:
            st.session_state.show_rule_form = False
            st.session_state.editing_rule_id = None
            st.rerun()


st.title("Compliance Rules")
st.markdown("Manage compliance rules for funds")

# Initialize session state for rule editing
if 'editing_rule_id' not in st.session_state:
    st.session_state.editing_rule_id = None
if 'show_rule_form' not in st.session_state:
    st.session_state.show_rule_form = False

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
    
    # Ensure all_rules is a list (handle None or other unexpected types)
    if all_rules is None:
        all_rules = []
    if not isinstance(all_rules, list):
        logger.warning(f"Expected list from get_rules(), got {type(all_rules)}: {all_rules}")
        all_rules = []
    
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
    
    # Action buttons - always show, even when no rules
    col1, col2, col3 = st.columns([1, 1, 1])
    with col3:
        if st.button("➕ New Rule", use_container_width = True):
            st.session_state.editing_rule_id = None
            st.session_state.show_rule_form = True
            st.rerun()
    
    # Rule form (create or edit) - show regardless of whether rules exist
    if st.session_state.show_rule_form:
        st.markdown("---")
        if st.session_state.editing_rule_id:
            st.subheader("Edit Rule")
            # Get full rule details for editing
            rule_to_edit = api_client.get_rule(st.session_state.editing_rule_id)
            if not rule_to_edit:
                st.error(f"Rule {st.session_state.editing_rule_id} not found")
                st.session_state.show_rule_form = False
                st.session_state.editing_rule_id = None
                st.rerun()
        else:
            st.subheader("Create New Rule")
            rule_to_edit = None
        
        _render_rule_form(rule_to_edit)
    
    if not filtered_rules:
        st.info("No rules found matching the filters. Click 'New Rule' above to create your first compliance rule.")
    else:
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
        
        st.dataframe(rules_data, width = 'stretch', hide_index = True)
        
        # Rule details
        st.markdown("---")
        st.subheader("Rule Details")
        
        selected_rule_id = st.selectbox(
            "Select a rule to view details",
            options = [r.get('rule_id') for r in filtered_rules],
            format_func = lambda x: next((f"{r['rule_name']} (ID: {r['rule_id']})" for r in filtered_rules if r['rule_id'] == x), f'Rule {x}')
        )
        
        if selected_rule_id:
            # Edit button
            if st.button("✏️ Edit Rule", key = f"edit_{selected_rule_id}"):
                st.session_state.editing_rule_id = selected_rule_id
                st.session_state.show_rule_form = True
                st.rerun()
        
        # Rule details view
        if selected_rule_id and not st.session_state.show_rule_form:
            try:
                rule_details = api_client.get_rule(selected_rule_id)
                
                if not rule_details:
                    st.warning(f"Rule details not found for rule ID '{selected_rule_id}'. The rule may not exist in the database or may be missing required data.")
                else:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Rule Name:** {rule_details.get('rule_name', 'N/A')}")
                        st.markdown(f"**Alert Message:** {rule_details.get('alert_message', 'N/A')}")
                        st.markdown(f"**Denominator:** {rule_details.get('denominator', 'N/A')}")
                        st.markdown(f"**Alert If:** {rule_details.get('alert_if', 'N/A')}")
                        st.markdown(f"**Alert Level:** {format_percentage(rule_details.get('alert_level', 0)) if rule_details.get('alert_level') is not None else 'N/A'}")
                    
                    with col2:
                        st.markdown(f"**Trade Mode:** {format_boolean(rule_details.get('trade_compliance_mode', False))}")
                        st.markdown(f"**Portfolio Mode:** {format_boolean(rule_details.get('portfolio_compliance_mode', False))}")
                        st.markdown(f"**Active:** {format_boolean(rule_details.get('active', False))}")
                    
                    # Rule Logic
                    st.markdown("### Rule Logic")
                    rule_logic = rule_details.get('logic')
                    if rule_logic and rule_logic.strip():
                        st.code(rule_logic, language = 'sql')
                    else:
                        st.info("No logic specified (rule applies to all securities)")
                    
                    # Attached funds
                    attached_funds = rule_details.get('attached_funds')
                    if attached_funds and isinstance(attached_funds, list) and len(attached_funds) > 0:
                        st.markdown("### Attached Funds")
                        for fund in attached_funds:
                            if isinstance(fund, dict):
                                st.markdown(f"- {fund.get('fund_name', 'N/A')} (ID: {fund.get('fund_id', 'N/A')})")
                            else:
                                st.markdown(f"- {fund}")
                    else:
                        st.info("This rule is not attached to any funds.")
            
            except Exception as e:
                st.error(f"Error loading rule details: {e}")

except Exception as e:
    st.error(f"Error loading rules: {e}")
