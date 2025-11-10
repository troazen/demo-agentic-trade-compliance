"""
Trade page for placing and managing trades.
"""

import streamlit as st
import sys
import os
import logging
import json
from typing import Optional, Dict, Any, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlitui.api_client import api_client
from streamlitui.utils.formatting import format_currency, format_datetime, format_percentage, format_shares, format_status

logger = logging.getLogger(__name__)


def _render_fund_selection() -> Optional[int]:
    """Render fund selection section and return selected fund ID."""
    st.markdown("### Select Fund")
    
    try:
        funds = api_client.get_funds()
        
        if not funds:
            st.info("No funds found. Please create a fund first.")
            return None
        
        # Display funds in a table
        funds_data = []
        for fund in funds:
            funds_data.append({
                'Fund ID': fund.get('fund_id'),
                'Fund Name': fund.get('fund_name'),
                'Cash': format_currency(fund.get('cash', 0)),
                'Holdings Count': fund.get('holdings_count', 0)
            })
        
        st.dataframe(funds_data, width = 'stretch', hide_index = True)
        
        # Fund selection dropdown
        fund_options = {f"{f.get('fund_name')} (ID: {f.get('fund_id')})": f.get('fund_id') for f in funds}
        selected_fund_display = st.selectbox(
            "Select a fund to trade",
            options = list(fund_options.keys()),
            index = 0 if fund_options else None,
            key = "fund_selector"
        )
        
        selected_fund_id = fund_options.get(selected_fund_display) if selected_fund_display else None
        
        return selected_fund_id
        
    except Exception as e:
        st.error(f"Error loading funds: {e}")
        logger.error(f"Error loading funds: {e}", exc_info = True)
        return None


def _render_fund_details(fund_id: int) -> Optional[Dict[str, Any]]:
    """Render fund details and holdings display."""
    try:
        fund_details = api_client.get_fund(fund_id)
        
        if not fund_details:
            st.warning(f"Fund details not found for fund ID '{fund_id}'.")
            return None
        
        # Fund summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Fund Name", fund_details.get('fund_name', 'N/A'))
        
        with col2:
            st.metric("Cash", format_currency(fund_details.get('cash', 0)))
        
        with col3:
            st.metric("Holdings Count", fund_details.get('holdings_count', 0))
        
        # Edit cash button
        if st.button("💰 Edit Cash", key = f"edit_cash_{fund_id}"):
            st.session_state[f'edit_cash_{fund_id}'] = True
            st.rerun()
        
        # Edit cash form
        if st.session_state.get(f'edit_cash_{fund_id}', False):
            with st.form(f"edit_cash_form_{fund_id}"):
                current_cash = float(fund_details.get('cash', 0))
                new_cash = st.number_input(
                    "New Cash Amount",
                    min_value = 0.0,
                    value = current_cash,
                    step = 1000.0,
                    format = "%.2f"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("💾 Save", use_container_width = True):
                        try:
                            success = api_client.update_fund_cash(fund_id, new_cash)
                            if success:
                                st.success("Cash updated successfully!")
                                st.session_state[f'edit_cash_{fund_id}'] = False
                                st.rerun()
                            else:
                                st.error("Failed to update cash")
                        except Exception as e:
                            st.error(f"Error updating cash: {e}")
                            logger.error(f"Error updating cash: {e}", exc_info = True)
                
                with col2:
                    if st.form_submit_button("❌ Cancel", use_container_width = True):
                        st.session_state[f'edit_cash_{fund_id}'] = False
                        st.rerun()
        
        # Holdings table
        st.markdown("### Holdings")
        holdings = fund_details.get('holdings', [])
        
        if holdings:
            holdings_data = []
            for holding in holdings:
                if isinstance(holding, dict):
                    holdings_data.append({
                        'Ticker': holding.get('ticker', 'N/A'),
                        'Name': holding.get('name', 'N/A'),
                        'Shares': format_shares(holding.get('shares', 0)),
                        'Price': format_currency(holding.get('current_price', 0)),
                        'Market Value': format_currency(holding.get('market_value', 0))
                    })
            
            st.dataframe(holdings_data, width = 'stretch', hide_index = True)
        else:
            st.info("No holdings found for this fund.")
        
        return fund_details
        
    except Exception as e:
        st.error(f"Error loading fund details: {e}")
        logger.error(f"Error loading fund details: {e}", exc_info = True)
        return None


def _render_sell_trade_form(fund_id: int, ticker: str, current_shares: float) -> None:
    """Render SELL trade form for an existing holding."""
    st.markdown(f"### SELL {ticker}")
    
    # Get current price for the security
    try:
        current_price = api_client.get_security_price(ticker)
        if current_price is None:
            current_price = 0.0
    except Exception as e:
        logger.warning(f"Error getting price for {ticker}: {e}")
        current_price = 0.0
    
    with st.form(f"sell_trade_form_{fund_id}_{ticker}"):
        st.markdown(f"**Current Shares:** {format_shares(current_shares)}")
        
        shares_to_sell = st.number_input(
            "Shares to Sell",
            min_value = 1,
            max_value = int(current_shares),
            value = int(current_shares),
            step = 1,
            help = f"Maximum: {format_shares(current_shares)} shares"
        )
        
        # Calculate and display estimated proceeds
        if current_price > 0:
            estimated_proceeds = shares_to_sell * current_price
            st.markdown(f"**Current Price:** {format_currency(current_price)}")
            st.markdown(f"**Estimated Proceeds:** {format_currency(estimated_proceeds)}")
        else:
            st.info("Price information not available for this security")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submit_button = st.form_submit_button("📤 Submit SELL Order", use_container_width = True, type = "primary")
        
        with col2:
            cancel_button = st.form_submit_button("❌ Cancel", use_container_width = True)
        
        if cancel_button:
            st.session_state.show_trade_form = False
            st.session_state.trade_form_type = None
            st.session_state.selected_ticker = None
            st.rerun()
        
        if submit_button:
            if shares_to_sell > current_shares:
                st.error(f"Cannot sell more shares than held. Maximum: {format_shares(current_shares)}")
            elif shares_to_sell <= 0:
                st.error("Shares to sell must be greater than 0")
            else:
                _handle_trade_submission(fund_id, ticker, "SELL", int(shares_to_sell))


def _render_buy_existing_form(fund_id: int, ticker: str) -> None:
    """Render BUY trade form for an existing holding."""
    st.markdown(f"### BUY {ticker}")
    
    # Get current price for the security
    try:
        current_price = api_client.get_security_price(ticker)
        if current_price is None:
            current_price = 0.0
    except Exception as e:
        logger.warning(f"Error getting price for {ticker}: {e}")
        current_price = 0.0
    
    with st.form(f"buy_existing_form_{fund_id}_{ticker}"):
        shares_to_buy = st.number_input(
            "Shares to Buy",
            min_value = 1,
            value = 100,
            step = 1
        )
        
        # Calculate and display estimated total price
        if current_price > 0:
            estimated_total = shares_to_buy * current_price
            st.markdown(f"**Current Price:** {format_currency(current_price)}")
            st.markdown(f"**Estimated Total:** {format_currency(estimated_total)}")
        else:
            st.info("Price information not available for this security")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submit_button = st.form_submit_button("📥 Submit BUY Order", use_container_width = True, type = "primary")
        
        with col2:
            cancel_button = st.form_submit_button("❌ Cancel", use_container_width = True)
        
        if cancel_button:
            st.session_state.show_trade_form = False
            st.session_state.trade_form_type = None
            st.session_state.selected_ticker = None
            st.rerun()
        
        if submit_button:
            if shares_to_buy <= 0:
                st.error("Shares to buy must be greater than 0")
            else:
                _handle_trade_submission(fund_id, ticker, "BUY", int(shares_to_buy))


def _render_buy_new_form(fund_id: int) -> None:
    """Render BUY trade form for a new security."""
    st.markdown("### New BUY Order")
    
    # Initialize session state for selected security
    form_key = "buy_new_form"
    if f'{form_key}_selected_security' not in st.session_state:
        st.session_state[f'{form_key}_selected_security'] = None
    
    # Security search (outside form so it updates immediately)
    search_query = st.text_input(
        "Search Security (Ticker or Issuer Name)",
        help = "Enter ticker symbol or issuer name to search",
        key = f"{form_key}_search"
    )
    
    selected_security = None
    
    if search_query:
        try:
            securities = api_client.search_securities(search_query)
            
            if securities:
                security_options = {f"{s.get('ticker')} - {s.get('name', 'N/A')}": s for s in securities}
                
                # Get previously selected security if it still exists in options
                previous_selection = st.session_state.get(f'{form_key}_selected_security')
                default_index = 0
                if previous_selection:
                    previous_display = f"{previous_selection.get('ticker')} - {previous_selection.get('name', 'N/A')}"
                    if previous_display in security_options:
                        default_index = list(security_options.keys()).index(previous_display)
                
                selected_display = st.selectbox(
                    "Select Security",
                    options = list(security_options.keys()),
                    index = default_index,
                    key = f"{form_key}_selectbox"
                )
                selected_security = security_options.get(selected_display) if selected_display else None
                
                # Store selected security in session state
                if selected_security:
                    st.session_state[f'{form_key}_selected_security'] = selected_security
            else:
                st.info("No securities found matching your search.")
                # Clear selected security if no results
                st.session_state[f'{form_key}_selected_security'] = None
        except Exception as e:
            st.error(f"Error searching securities: {e}")
            logger.error(f"Error searching securities: {e}", exc_info = True)
    else:
        # Use stored selected security if search is empty
        selected_security = st.session_state.get(f'{form_key}_selected_security')
    
    if selected_security:
        ticker = selected_security.get('ticker')
        st.markdown(f"**Selected:** {ticker} - {selected_security.get('name', 'N/A')}")
        st.markdown(f"**Current Price:** {format_currency(selected_security.get('current_price', 0))}")
    
    # Trade form
    with st.form("buy_new_form"):
        shares_to_buy = st.number_input(
            "Shares to Buy",
            min_value = 1,
            value = 100,
            step = 1,
            disabled = not selected_security,
            key = f"{form_key}_shares"
        )
        
        # Calculate and display estimated total price
        if selected_security:
            current_price = selected_security.get('current_price', 0) or 0
            if current_price > 0:
                estimated_total = shares_to_buy * current_price
                st.markdown(f"**Estimated Total:** {format_currency(estimated_total)}")
            else:
                st.info("Price information not available for this security")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submit_button = st.form_submit_button("📥 Submit BUY Order", use_container_width = True, type = "primary", disabled = not selected_security)
        
        with col2:
            cancel_button = st.form_submit_button("❌ Cancel", use_container_width = True)
        
        if cancel_button:
            st.session_state.show_trade_form = False
            st.session_state.trade_form_type = None
            if f'{form_key}_selected_security' in st.session_state:
                del st.session_state[f'{form_key}_selected_security']
            st.rerun()
        
        if submit_button and selected_security:
            ticker = selected_security.get('ticker')
            if shares_to_buy <= 0:
                st.error("Shares to buy must be greater than 0")
            else:
                _handle_trade_submission(fund_id, ticker, "BUY", int(shares_to_buy))


def _handle_trade_submission(fund_id: int, ticker: str, direction: str, shares: int) -> None:
    """Handle trade submission and check for compliance alerts."""
    try:
        with st.spinner(f"Submitting {direction} order for {shares} shares of {ticker}..."):
            try:
                response = api_client.create_trade(fund_id, ticker, direction, shares)
                
                if response.get('success'):
                    trade = response.get('trade')
                    trade_id = trade.get('trade_id') if trade else None
                    
                    if trade_id:
                        # Check if alerts were returned (403 response)
                        alerts = response.get('alerts', [])
                        if alerts:
                            # Trade has alerts - show modal immediately
                            st.session_state.pending_trade_id = trade_id
                            st.session_state.show_alert_modal = True
                            st.rerun()
                        else:
                            # Check trade status for compliance alerts
                            _check_trade_status_and_show_alerts(trade_id, fund_id)
                    else:
                        st.error("Trade created but no trade ID returned")
                else:
                    error_msg = response.get('error', 'Failed to create trade')
                    st.error(f"Failed to create trade: {error_msg}")
                    logger.error(f"Trade creation failed: {error_msg}")
            except Exception as api_error:
                # Check if this is a 403 response (alerts found)
                error_str = str(api_error)
                if "403" in error_str or "compliance alerts" in error_str.lower():
                    # Try to get trade ID from error or check status
                    # The trade was created but has alerts
                    # We need to get the trade ID somehow - for now, check recent trades
                    try:
                        trades = api_client.get_trades_for_fund(fund_id)
                        if trades:
                            latest_trade = trades[0]  # Most recent trade
                            trade_id = latest_trade.get('trade_id')
                            if trade_id:
                                st.session_state.pending_trade_id = trade_id
                                st.session_state.show_alert_modal = True
                                st.rerun()
                    except:
                        pass
                
                st.error(f"Error submitting trade: {api_error}")
                logger.error(f"Error submitting trade: {api_error}", exc_info = True)
                
    except Exception as e:
        st.error(f"Error submitting trade: {e}")
        logger.error(f"Error submitting trade: {e}", exc_info = True)


def _check_trade_status_and_show_alerts(trade_id: int, fund_id: int) -> None:
    """Check trade status and show alert modal if needed."""
    try:
        # Get trade details to check status
        trade = api_client.get_trade(trade_id)
        
        if not trade:
            st.error(f"Trade {trade_id} not found")
            return
        
        trade_status = trade.get('status', '').lower()
        
        if trade_status == 'alert':
            # Trade has compliance alerts - show modal
            st.session_state.pending_trade_id = trade_id
            st.session_state.show_alert_modal = True
            st.rerun()
        elif trade_status == 'processed':
            # Trade processed successfully
            st.success(f"✅ Trade executed successfully! Trade ID: {trade_id}")
            st.session_state.show_trade_form = False
            st.session_state.trade_form_type = None
            st.session_state.selected_ticker = None
            st.rerun()
        elif trade_status == 'invalid':
            # Trade validation failed
            error_msg = trade.get('error', 'Trade validation failed')
            st.error(f"Trade validation failed: {error_msg}")
        else:
            # Other status - show info
            st.info(f"Trade status: {format_status(trade_status)}")
            
    except Exception as e:
        st.error(f"Error checking trade status: {e}")
        logger.error(f"Error checking trade status: {e}", exc_info = True)


def _render_compliance_alert_modal(trade_id: int) -> None:
    """Render compliance alert modal/popup (PRD Line 265)."""
    st.markdown("---")
    st.markdown("### ⚠️ Compliance Alert - Trade Requires Action")
    
    try:
        # Get trade details
        trade = api_client.get_trade(trade_id)
        if trade:
            st.markdown(f"**Trade ID:** {trade_id}")
            st.markdown(f"**Ticker:** {trade.get('ticker', 'N/A')}")
            st.markdown(f"**Direction:** {trade.get('direction', 'N/A')}")
            st.markdown(f"**Shares:** {format_shares(trade.get('shares', 0))}")
        
        # Get alerts for this trade
        alerts = api_client.get_alerts(trade_id = trade_id)
        
        if not alerts:
            st.warning("No alerts found for this trade")
            return
        
        st.markdown("---")
        st.markdown("**The following compliance rules were triggered:**")
        
        # Store override reasons in session state
        if f'override_reasons_{trade_id}' not in st.session_state:
            st.session_state[f'override_reasons_{trade_id}'] = {}
        
        # Display each alert
        for alert in alerts:
            alert_id = alert.get('alert_id')
            rule_name = alert.get('rule_name', 'N/A')
            alert_message = alert.get('alert_message', 'N/A')
            calculated_percentage = alert.get('calculated_percentage')
            holdings_triggered = alert.get('holdings_triggered', '')
            
            with st.expander(f"🔴 {rule_name}", expanded = True):
                st.markdown(f"**Alert Message:** {alert_message}")
                
                if calculated_percentage is not None:
                    st.markdown(f"**Calculated Percentage:** {format_percentage(calculated_percentage)}")
                else:
                    st.markdown("**Calculated Percentage:** N/A (Prohibit rule)")
                
                # Display holdings that triggered the alert
                if holdings_triggered:
                    try:
                        holdings_list = json.loads(holdings_triggered) if isinstance(holdings_triggered, str) else holdings_triggered
                        if holdings_list:
                            st.markdown("**Holdings that triggered this alert:**")
                            for holding in holdings_list:
                                if isinstance(holding, dict):
                                    ticker = holding.get('ticker', 'N/A')
                                    name = holding.get('name', 'N/A')
                                    shares = holding.get('shares', 0)
                                    st.markdown(f"- {ticker} ({name}): {format_shares(shares)} shares")
                                else:
                                    st.markdown(f"- {holding}")
                    except Exception as e:
                        logger.warning(f"Error parsing holdings_triggered: {e}")
                        st.markdown(f"**Holdings:** {holdings_triggered}")
                
                # Override reason field (optional per PRD)
                override_reason = st.text_area(
                    f"Override Reason (Optional) - Alert {alert_id}",
                    value = st.session_state[f'override_reasons_{trade_id}'].get(alert_id, ''),
                    key = f"override_reason_{alert_id}",
                    help = "Optional reason for overriding this alert"
                )
                
                # Store in session state
                st.session_state[f'override_reasons_{trade_id}'][alert_id] = override_reason
        
        st.markdown("---")
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Override & Proceed", use_container_width = True, type = "primary"):
                _handle_alert_override(trade_id)
        
        with col2:
            if st.button("❌ Cancel Trade", use_container_width = True):
                _handle_trade_cancel(trade_id)
        
    except Exception as e:
        st.error(f"Error loading alerts: {e}")
        logger.error(f"Error loading alerts: {e}", exc_info = True)


def _handle_alert_override(trade_id: int) -> None:
    """Handle alert override and proceed with trade."""
    try:
        # Get override reasons from session state
        override_reasons = st.session_state.get(f'override_reasons_{trade_id}', {})
        
        # Format for API: {alert_id: {'reason': 'override reason'}}
        alerts_dict = {}
        for alert_id, reason in override_reasons.items():
            alerts_dict[alert_id] = {'reason': reason if reason else 'User override'}
        
        with st.spinner("Processing override..."):
            success = api_client.override_trade(trade_id, alerts_dict)
            
            if success:
                st.success("✅ Trade alerts overridden and trade processed successfully!")
                # Clear session state
                st.session_state.pending_trade_id = None
                st.session_state.show_alert_modal = False
                st.session_state.show_trade_form = False
                st.session_state.trade_form_type = None
                st.session_state.selected_ticker = None
                if f'override_reasons_{trade_id}' in st.session_state:
                    del st.session_state[f'override_reasons_{trade_id}']
                st.rerun()
            else:
                st.error("Failed to override trade alerts")
                
    except Exception as e:
        st.error(f"Error overriding alerts: {e}")
        logger.error(f"Error overriding alerts: {e}", exc_info = True)


def _handle_trade_cancel(trade_id: int) -> None:
    """Handle trade cancellation."""
    try:
        with st.spinner("Cancelling trade..."):
            success = api_client.cancel_trade(trade_id)
            
            if success:
                st.info("Trade cancelled")
                # Clear session state
                st.session_state.pending_trade_id = None
                st.session_state.show_alert_modal = False
                st.session_state.show_trade_form = False
                st.session_state.trade_form_type = None
                st.session_state.selected_ticker = None
                if f'override_reasons_{trade_id}' in st.session_state:
                    del st.session_state[f'override_reasons_{trade_id}']
                st.rerun()
            else:
                st.error("Failed to cancel trade")
                
    except Exception as e:
        st.error(f"Error cancelling trade: {e}")
        logger.error(f"Error cancelling trade: {e}", exc_info = True)


def _render_trade_history(fund_id: int) -> None:
    """Render trade history for the fund."""
    st.markdown("---")
    st.markdown("### Trade History")
    
    try:
        trades = api_client.get_trades_for_fund(fund_id)
        
        if trades:
            trades_data = []
            for trade in trades:
                trades_data.append({
                    'Trade ID': trade.get('trade_id'),
                    'Ticker': trade.get('ticker', 'N/A'),
                    'Direction': trade.get('direction', 'N/A'),
                    'Shares': format_shares(trade.get('shares', 0)),
                    'Status': format_status(trade.get('status', 'N/A')),
                    'Created': format_datetime(trade.get('created_at'))
                })
            
            st.dataframe(trades_data, width = 'stretch', hide_index = True)
        else:
            st.info("No trades found for this fund.")
            
    except Exception as e:
        st.error(f"Error loading trade history: {e}")
        logger.error(f"Error loading trade history: {e}", exc_info = True)


# Main page
st.title("Place Trade")
st.markdown("Place BUY or SELL orders for fund holdings")

# Initialize session state
if 'selected_fund_id' not in st.session_state:
    st.session_state.selected_fund_id = None
if 'show_trade_form' not in st.session_state:
    st.session_state.show_trade_form = False
if 'trade_form_type' not in st.session_state:
    st.session_state.trade_form_type = None
if 'selected_ticker' not in st.session_state:
    st.session_state.selected_ticker = None
if 'pending_trade_id' not in st.session_state:
    st.session_state.pending_trade_id = None
if 'show_alert_modal' not in st.session_state:
    st.session_state.show_alert_modal = False

# Fund selection
selected_fund_id = _render_fund_selection()

if selected_fund_id:
    st.session_state.selected_fund_id = selected_fund_id
    
    # Fund details and holdings
    st.markdown("---")
    fund_details = _render_fund_details(selected_fund_id)
    
    if fund_details:
        # Trade form selection
        st.markdown("---")
        st.markdown("### Place Trade")
        
        # Check if alert modal should be shown
        if st.session_state.show_alert_modal and st.session_state.pending_trade_id:
            _render_compliance_alert_modal(st.session_state.pending_trade_id)
        else:
            # Show trade form if requested
            if st.session_state.show_trade_form:
                if st.session_state.trade_form_type == 'SELL' and st.session_state.selected_ticker:
                    # Get current shares for this holding
                    holdings = fund_details.get('holdings', [])
                    current_shares = 0
                    for holding in holdings:
                        if isinstance(holding, dict) and holding.get('ticker') == st.session_state.selected_ticker:
                            current_shares = holding.get('shares', 0)
                            break
                    
                    if current_shares > 0:
                        _render_sell_trade_form(selected_fund_id, st.session_state.selected_ticker, current_shares)
                    else:
                        st.error(f"No shares held for {st.session_state.selected_ticker}")
                        st.session_state.show_trade_form = False
                        st.rerun()
                
                elif st.session_state.trade_form_type == 'BUY_EXISTING' and st.session_state.selected_ticker:
                    _render_buy_existing_form(selected_fund_id, st.session_state.selected_ticker)
                
                elif st.session_state.trade_form_type == 'BUY_NEW':
                    _render_buy_new_form(selected_fund_id)
                
                else:
                    st.session_state.show_trade_form = False
                    st.rerun()
            else:
                # Action buttons for placing trades
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📥 New BUY Order", use_container_width = True, type = "primary"):
                        st.session_state.show_trade_form = True
                        st.session_state.trade_form_type = 'BUY_NEW'
                        st.session_state.selected_ticker = None
                        st.rerun()
                
                # Holdings with action buttons
                holdings = fund_details.get('holdings', [])
                if holdings:
                    st.markdown("#### Place Trade on Existing Holdings")
                    
                    for holding in holdings:
                        if isinstance(holding, dict):
                            ticker = holding.get('ticker', 'N/A')
                            name = holding.get('name', 'N/A')
                            shares = holding.get('shares', 0)
                            
                            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                            
                            with col1:
                                st.markdown(f"**{ticker}** - {name} ({format_shares(shares)} shares)")
                            
                            with col2:
                                if st.button("📥 BUY", key = f"buy_{ticker}", use_container_width = True):
                                    st.session_state.show_trade_form = True
                                    st.session_state.trade_form_type = 'BUY_EXISTING'
                                    st.session_state.selected_ticker = ticker
                                    st.rerun()
                            
                            with col3:
                                if shares > 0:
                                    if st.button("💲 SELL", key = f"sell_{ticker}", use_container_width = True):
                                        st.session_state.show_trade_form = True
                                        st.session_state.trade_form_type = 'SELL'
                                        st.session_state.selected_ticker = ticker
                                        st.rerun()
                                else:
                                    st.button("💲 SELL", key = f"sell_{ticker}", use_container_width = True, disabled = True)
                            
                            with col4:
                                st.markdown("")  # Spacer
            
            # Trade history
            _render_trade_history(selected_fund_id)

