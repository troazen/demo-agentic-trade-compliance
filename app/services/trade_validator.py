"""
Trade validator for pre-compliance trade checks.
"""

from decimal import Decimal
from typing import Dict, Any
import logging

from app.models import db, Trade, Fund, Holding
from app.constants import TradeDirection, TradeStatus, MIN_TRADE_SHARES

logger = logging.getLogger(__name__)


class TradeValidator:
    """Service class for trade validation operations."""
    
    @staticmethod
    def validate_trade_inputs(fund_id: int, ticker: str, direction: str, shares: int) -> Dict[str, Any]:
        """
        Validate basic trade inputs.
        
        Args:
            fund_id: Fund ID
            ticker: Security ticker
            direction: Trade direction
            shares: Number of shares
            
        Returns:
            Dictionary with validation result and error message if invalid
        """
        logger.debug(f"Validating trade inputs: fund_id={fund_id}, ticker={ticker}, direction={direction}, shares={shares}")
        
        # Validate fund_id
        if not isinstance(fund_id, int) or fund_id <= 0:
            error_msg = f"Invalid fund ID: {fund_id}. Fund ID must be a positive integer."
            logger.error(error_msg)
            return {'valid': False, 'error': error_msg}
        
        # Validate ticker
        if not ticker or not isinstance(ticker, str) or not ticker.strip():
            error_msg = f"Invalid ticker: '{ticker}'. Ticker must be a non-empty string."
            logger.error(error_msg)
            return {'valid': False, 'error': error_msg}
        
        # Validate direction
        if direction.upper() not in ['BUY', 'SELL']:
            error_msg = f"Invalid direction: '{direction}'. Direction must be 'BUY' or 'SELL'."
            logger.error(error_msg)
            return {'valid': False, 'error': error_msg}
        
        # Validate shares
        if not isinstance(shares, int) or shares < MIN_TRADE_SHARES:
            error_msg = f"Invalid shares: {shares}. Number of shares must be a positive integer >= {MIN_TRADE_SHARES}."
            logger.error(error_msg)
            return {'valid': False, 'error': error_msg}
        
        logger.debug("Trade inputs validation passed")
        return {'valid': True}
    
    @staticmethod
    def validate_trade_execution(trade: Trade) -> Dict[str, Any]:
        """
        Validate trade execution (cash/shares availability).
        
        Args:
            trade: Trade object to validate
            
        Returns:
            Dictionary with validation result
        """
        logger.debug(f"Validating trade execution for trade {trade.trade_id}")
        
        fund = Fund.query.get(trade.fund_id)
        if not fund:
            logger.error(f"Fund {trade.fund_id} not found")
            return {'valid': False, 'error': 'Fund not found'}
        
        if trade.direction == TradeDirection.BUY:
            return TradeValidator._validate_buy_trade(trade, fund)
        elif trade.direction == TradeDirection.SELL:
            return TradeValidator._validate_sell_trade(trade, fund)
        else:
            logger.error(f"Invalid trade direction: {trade.direction}")
            return {'valid': False, 'error': 'Invalid trade direction'}
    
    @staticmethod
    def _validate_buy_trade(trade: Trade, fund: Fund) -> Dict[str, Any]:
        """
        Validate BUY trade (check sufficient cash).
        
        Args:
            trade: Trade object
            fund: Fund object
            
        Returns:
            Dictionary with validation result
        """
        logger.debug(f"Validating BUY trade {trade.trade_id}")
        
        if not trade.total_value:
            logger.error(f"Trade {trade.trade_id} has no total_value calculated")
            return {'valid': False, 'error': 'Trade value not calculated'}
        
        if fund.cash < trade.total_value:
            shortfall = trade.total_value - fund.cash
            error_msg = (f"You tried to place a BUY order for {int(trade.shares)} shares of {trade.ticker} "
                        f"at a price of ${trade.price:.2f}, which would cost ${trade.total_value:,.2f}; "
                        f"however, the fund only has ${fund.cash:,.2f} in cash, "
                        f"a shortfall of ${shortfall:,.2f}. Please adjust your order to "
                        f"{int(fund.cash / trade.price)} shares or fewer.")
            
            logger.warning(f"BUY trade {trade.trade_id} rejected: insufficient cash. {error_msg}")
            return {'valid': False, 'error': error_msg}
        
        if fund.cash == 0:
            error_msg = "Trading cash is not allowed"
            logger.warning(f"BUY trade {trade.trade_id} rejected: {error_msg}")
            return {'valid': False, 'error': error_msg}
        
        logger.debug(f"BUY trade {trade.trade_id} validation passed")
        return {'valid': True}
    
    @staticmethod
    def _validate_sell_trade(trade: Trade, fund: Fund) -> Dict[str, Any]:
        """
        Validate SELL trade (check sufficient shares).
        
        Args:
            trade: Trade object
            fund: Fund object
            
        Returns:
            Dictionary with validation result
        """
        logger.debug(f"Validating SELL trade {trade.trade_id}")
        
        # Find existing holding
        holding = Holding.query.filter_by(
            fund_id = trade.fund_id,
            ticker = trade.ticker
        ).first()
        
        if not holding:
            error_msg = f"You tried to place a SELL order for {int(trade.shares)} shares of {trade.ticker}, but the fund does not hold this security."
            logger.warning(f"SELL trade {trade.trade_id} rejected: {error_msg}")
            return {'valid': False, 'error': error_msg}
        
        if holding.shares < trade.shares:
            error_msg = (f"You tried to place a SELL order for {int(trade.shares)} shares of {trade.ticker} "
                        f"at a price of ${trade.price:.2f}, which would be worth ${trade.total_value:,.2f}; "
                        f"however, the fund only holds {int(holding.shares)} shares. "
                        f"Please adjust your order to {int(holding.shares)} shares or fewer.")
            
            logger.warning(f"SELL trade {trade.trade_id} rejected: insufficient shares. {error_msg}")
            return {'valid': False, 'error': error_msg}
        
        logger.debug(f"SELL trade {trade.trade_id} validation passed")
        return {'valid': True}
    
    @staticmethod
    def validate_trade_cancellation(trade_id: int) -> bool:
        """
        Validate that a trade can be cancelled.
        
        Args:
            trade_id: Trade ID to validate
            
        Returns:
            True if can be cancelled, False otherwise
        """
        logger.debug(f"Validating trade cancellation for trade {trade_id}")
        
        trade = Trade.query.get(trade_id)
        if not trade:
            logger.error(f"Trade {trade_id} not found")
            return False
        
        # Can only cancel pending trades
        if trade.is_completed():
            logger.warning(f"Cannot cancel completed trade {trade_id} with status {trade.status.value}")
            return False
        
        logger.debug(f"Trade {trade_id} can be cancelled")
        return True
