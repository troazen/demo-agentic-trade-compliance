"""
Trade executor for processing completed trades.
"""

from decimal import Decimal
from typing import Dict, Any
import logging

from app.models import db, Trade, Fund
from app.constants import TradeStatus, TradeDirection
from app.services.holdings_service import HoldingsService

logger = logging.getLogger(__name__)


class TradeExecutor:
    """Service class for trade execution operations."""
    
    @staticmethod
    def execute_trade(trade: Trade) -> Dict[str, Any]:
        """
        Execute a trade by applying changes to holdings and cash.
        
        Args:
            trade: Trade object to execute
            
        Returns:
            Dictionary with execution result
        """
        logger.debug(f"Executing trade {trade.trade_id}")
        
        try:
            # Apply staged holdings changes to actual holdings
            if not HoldingsService.apply_staging_to_holdings(trade):
                logger.error(f"Failed to apply staging holdings for trade {trade.trade_id}")
                return {'success': False, 'error': 'Failed to apply holdings changes'}
            
            # Update fund cash
            if not TradeExecutor._update_fund_cash(trade):
                logger.error(f"Failed to update fund cash for trade {trade.trade_id}")
                return {'success': False, 'error': 'Failed to update fund cash'}
            
            # Update trade status to processed
            trade.update_status(TradeStatus.PROCESSED)
            db.session.commit()
            
            logger.info(f"Successfully executed trade {trade.trade_id}")
            return {
                'success': True,
                'trade_id': trade.trade_id,
                'status': TradeStatus.PROCESSED.value,
                'message': 'Trade executed successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to execute trade {trade.trade_id}: {e}")
            return {'success': False, 'error': f'Execution failed: {str(e)}'}
    
    @staticmethod
    def _update_fund_cash(trade: Trade) -> bool:
        """
        Update fund cash based on trade direction.
        
        Args:
            trade: Trade object
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Updating fund cash for trade {trade.trade_id}")
        
        if not trade.total_value:
            logger.error(f"Trade {trade.trade_id} has no total_value")
            return False
        
        fund = Fund.query.get(trade.fund_id)
        if not fund:
            logger.error(f"Fund {trade.fund_id} not found")
            return False
        
        try:
            if trade.direction == TradeDirection.BUY:
                # Decrease cash for BUY
                fund.cash -= trade.total_value
                logger.debug(f"Fund {trade.fund_id} cash decreased by {trade.total_value} to {fund.cash}")
            elif trade.direction == TradeDirection.SELL:
                # Increase cash for SELL
                fund.cash += trade.total_value
                logger.debug(f"Fund {trade.fund_id} cash increased by {trade.total_value} to {fund.cash}")
            else:
                logger.error(f"Invalid trade direction: {trade.direction}")
                return False
            
            db.session.commit()
            logger.info(f"Updated fund {trade.fund_id} cash to {fund.cash}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update fund cash for trade {trade.trade_id}: {e}")
            return False
    
    @staticmethod
    def cancel_trade(trade: Trade) -> Dict[str, Any]:
        """
        Cancel a trade.
        
        Args:
            trade: Trade object to cancel
            
        Returns:
            Dictionary with cancellation result
        """
        logger.debug(f"Cancelling trade {trade.trade_id}")
        
        try:
            # Clean up staging holdings if they exist
            HoldingsService.get_staging_holdings_for_trade(trade.fund_id, trade.trade_id)
            # Note: HoldingsService.apply_staging_to_holdings already cleans up staging
            
            # Update trade status to cancelled
            trade.update_status(TradeStatus.CANCELLED)
            db.session.commit()
            
            logger.info(f"Successfully cancelled trade {trade.trade_id}")
            return {
                'success': True,
                'trade_id': trade.trade_id,
                'status': TradeStatus.CANCELLED.value,
                'message': 'Trade cancelled successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to cancel trade {trade.trade_id}: {e}")
            return {'success': False, 'error': f'Cancellation failed: {str(e)}'}
    
    @staticmethod
    def get_trade_execution_summary(trade: Trade) -> Dict[str, Any]:
        """
        Get summary of trade execution details.
        
        Args:
            trade: Trade object
            
        Returns:
            Dictionary with execution summary
        """
        logger.debug(f"Getting execution summary for trade {trade.trade_id}")
        
        summary = {
            'trade_id': trade.trade_id,
            'fund_id': trade.fund_id,
            'ticker': trade.ticker,
            'direction': trade.direction.value,
            'shares': int(trade.shares),
            'price': float(trade.price) if trade.price else None,
            'total_value': float(trade.total_value) if trade.total_value else None,
            'status': trade.status.value,
            'created_at': trade.created_at.isoformat(),
            'updated_at': trade.updated_at.isoformat()
        }
        
        # Add fund and security names if available
        if trade.fund:
            summary['fund_name'] = trade.fund.fund_name
            summary['fund_cash_after'] = float(trade.fund.cash)
        
        if trade.security:
            summary['security_name'] = trade.security.name
        
        logger.debug(f"Generated execution summary for trade {trade.trade_id}")
        return summary
