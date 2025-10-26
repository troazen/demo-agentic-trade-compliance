"""
Session state management utilities.
"""

import streamlit as st
import logging

logger = logging.getLogger(__name__)


def init_session_state():
    """
    Initialize session state variables.
    """
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.selected_fund_id = None
        st.session_state.selected_rule_id = None
        st.session_state.selected_security_ticker = None
        st.session_state.compliance_results = None
        st.session_state.trade_dialog_open = False
        st.session_state.last_refresh = None
        logger.debug("Session state initialized")


def get_selected_fund_id() -> int:
    """
    Get the currently selected fund ID.
    
    Returns:
        Selected fund ID or None
    """
    return st.session_state.get('selected_fund_id')


def set_selected_fund_id(fund_id: int):
    """
    Set the currently selected fund ID.
    
    Args:
        fund_id: Fund ID to set
    """
    st.session_state.selected_fund_id = fund_id
    logger.debug(f"Set selected fund ID to {fund_id}")


def get_selected_rule_id() -> int:
    """
    Get the currently selected rule ID.
    
    Returns:
        Selected rule ID or None
    """
    return st.session_state.get('selected_rule_id')


def set_selected_rule_id(rule_id: int):
    """
    Set the currently selected rule ID.
    
    Args:
        rule_id: Rule ID to set
    """
    st.session_state.selected_rule_id = rule_id
    logger.debug(f"Set selected rule ID to {rule_id}")


def get_compliance_results():
    """
    Get stored compliance check results.
    
    Returns:
        Compliance results dictionary or None
    """
    return st.session_state.get('compliance_results')


def set_compliance_results(results: dict):
    """
    Store compliance check results.
    
    Args:
        results: Compliance results dictionary
    """
    st.session_state.compliance_results = results
    logger.debug("Set compliance results")


def clear_compliance_results():
    """
    Clear stored compliance check results.
    """
    if 'compliance_results' in st.session_state:
        del st.session_state.compliance_results
        logger.debug("Cleared compliance results")


def refresh_data():
    """
    Mark data as needing refresh.
    """
    import time
    st.session_state.last_refresh = time.time()
    logger.debug("Marked data for refresh")


def clear_selection():
    """
    Clear all selected items.
    """
    st.session_state.selected_fund_id = None
    st.session_state.selected_rule_id = None
    st.session_state.selected_security_ticker = None
    logger.debug("Cleared all selections")

