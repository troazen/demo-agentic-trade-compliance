"""
Trade service for managing trade operations.
"""

from decimal import Decimal
from typing import Optional, Dict, Any, List
import logging

from sqlalchemy.orm import Session

from app.models import db, Trade, Fund, Security
from app.constants import TradeStatus, TradeDirection
from app.services.security_service import SecurityService
from app.services.trade_validator import TradeValidator

logger = logging.getLogger(__name__)


class TradeService:
    """Service class for trade-related operations."""
    
    @staticmethod
    def create_trade(fund_id: int, ticker: str, direction: str, shares: int) -> Optional[Trade]:
        """
        Create a new trade record.
        
        Args:
            fund_id: Fund ID
            ticker: Security ticker
            direction: Trade direction ('BUY' or 'SELL')
            shares: Number of shares (positive integer)
            
        Returns:
            Created Trade object or None if creation failed
        """
        logger.debug(f"Creating trade: {direction} {shares} shares of {ticker} for fund {fund_id}")
        
        # Validate inputs
        validation_result = TradeValidator.validate_trade_inputs(fund_id, ticker, direction, shares)
        if not validation_result['valid']:
            logger.error(f"Trade input validation failed: {validation_result['error']}")
            return None
        
        # Convert direction string to enum
        try:
            direction_enum = TradeDirection(direction.upper())
        except ValueError:
            logger.error(f"Invalid trade direction: {direction}")
            return None
        
        # Verify fund exists
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return None
        
        # Verify security exists
        if not SecurityService.validate_security_exists(ticker):
            logger.error(f"Security {ticker} not found")
            return None
        
        try:
            trade = Trade(
                fund_id = fund_id,
                ticker = ticker,
                direction = direction_enum,
                shares = Decimal(str(shares))
            )
            db.session.add(trade)
            db.session.commit()
            
            logger.info(f"Created trade {trade.trade_id}: {direction} {shares} shares of {ticker}")
            return trade
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create trade: {e}")
            return None
    
    @staticmethod
    def get_trade_by_id(trade_id: int) -> Optional[Trade]:
        """
        Get trade by ID.
        
        Args:
            trade_id: Trade ID to retrieve
            
        Returns:
            Trade object or None if not found
        """
        logger.debug(f"Retrieving trade {trade_id}")
        
        trade = Trade.query.get(trade_id)
        if trade:
            logger.debug(f"Found trade: {trade.direction.value} {trade.shares} shares of {trade.ticker}")
        else:
            logger.warning(f"Trade {trade_id} not found")
        
        return trade
    
    @staticmethod
    def get_trades_for_fund(fund_id: int) -> List[Trade]:
        """
        Get all trades for a fund.
        
        Args:
            fund_id: Fund ID to get trades for
            
        Returns:
            List of Trade objects
        """
        logger.debug(f"Retrieving trades for fund {fund_id}")
        
        trades = Trade.query.filter_by(fund_id = fund_id).order_by(Trade.created_at.desc()).all()
        logger.debug(f"Retrieved {len(trades)} trades for fund {fund_id}")
        return trades
    
    @staticmethod
    def get_trades_by_status(status: str) -> List[Trade]:
        """
        Get trades by status.
        
        Args:
            status: Trade status to filter by
            
        Returns:
            List of Trade objects
        """
        logger.debug(f"Retrieving trades with status {status}")
        
        try:
            status_enum = TradeStatus(status)
            trades = Trade.query.filter_by(status = status_enum).order_by(Trade.created_at.desc()).all()
            logger.debug(f"Retrieved {len(trades)} trades with status {status}")
            return trades
        except ValueError:
            logger.error(f"Invalid trade status: {status}")
            return []
    
    @staticmethod
    def update_trade_status(trade_id: int, new_status: str) -> bool:
        """
        Update trade status.
        
        Args:
            trade_id: Trade ID to update
            new_status: New status string
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Updating trade {trade_id} status to {new_status}")
        
        trade = Trade.query.get(trade_id)
        if not trade:
            logger.error(f"Trade {trade_id} not found")
            return False
        
        try:
            status_enum = TradeStatus(new_status)
            trade.update_status(status_enum)
            db.session.commit()
            
            logger.info(f"Updated trade {trade_id} status to {new_status}")
            return True
        except ValueError:
            logger.error(f"Invalid trade status: {new_status}")
            return False
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update trade {trade_id} status: {e}")
            return False
    
    @staticmethod
    def calculate_trade_value(trade: Trade) -> Optional[Decimal]:
        """
        Calculate trade value and update trade record.
        
        Args:
            trade: Trade object to calculate value for
            
        Returns:
            Trade value as Decimal, or None if calculation failed
        """
        logger.debug(f"Calculating trade value for trade {trade.trade_id}")
        
        # Get current price
        current_price = SecurityService.get_current_price(trade.ticker)
        if not current_price:
            logger.error(f"No current price available for {trade.ticker}")
            return None
        
        # Calculate total value
        total_value = current_price * trade.shares
        
        try:
            # Update trade with price and value
            trade.price = current_price
            trade.total_value = total_value
            db.session.commit()
            
            logger.info(f"Trade {trade.trade_id} value calculated: {total_value} ({trade.shares} shares @ {current_price})")
            return total_value
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update trade {trade.trade_id} value: {e}")
            return None
    
    @staticmethod
    def process_trade_flow(trade_id: int) -> Dict[str, Any]:
        """
        Process a trade through the complete flow.
        
        Args:
            trade_id: Trade ID to process
            
        Returns:
            Dictionary with processing result
        """
        logger.debug(f"Processing trade flow for trade {trade_id}")
        
        trade = Trade.query.get(trade_id)
        if not trade:
            logger.error(f"Trade {trade_id} not found")
            return {'success': False, 'error': 'Trade not found'}
        
        # Step 1: Update status to validating
        trade.update_status(TradeStatus.VALIDATING)
        db.session.commit()
        
        # Step 2: Calculate trade value
        trade_value = TradeService.calculate_trade_value(trade)
        if not trade_value:
            trade.update_status(TradeStatus.INVALID)
            db.session.commit()
            return {'success': False, 'error': 'Unable to calculate trade value'}
        
        # Step 3: Validate trade (cash/shares checks)
        validation_result = TradeValidator.validate_trade_execution(trade)
        if not validation_result['valid']:
            trade.update_status(TradeStatus.INVALID)
            db.session.commit()
            return {'success': False, 'error': validation_result['error']}
        
        # Step 4: Update status to compliance
        trade.update_status(TradeStatus.COMPLIANCE)
        db.session.commit()
        
        logger.info(f"Trade {trade_id} ready for compliance checking")
        return {
            'success': True, 
            'trade_id': trade_id,
            'status': TradeStatus.COMPLIANCE.value,
            'trade_value': float(trade_value)
        }
    
    @staticmethod
    def get_trade_summary(trade_id: int) -> Optional[Dict[str, Any]]:
        """
        Get trade summary with all details.
        
        Args:
            trade_id: Trade ID to get summary for
            
        Returns:
            Trade summary dictionary or None if not found
        """
        logger.debug(f"Getting trade summary for trade {trade_id}")
        
        trade = Trade.query.get(trade_id)
        if not trade:
            logger.warning(f"Trade {trade_id} not found")
            return None
        
        summary = trade.to_dict()
        
        # Add additional calculated fields
        if trade.price and trade.shares:
            summary['calculated_value'] = float(trade.price * trade.shares)
        
        logger.debug(f"Retrieved trade summary for trade {trade_id}")
        return summary
