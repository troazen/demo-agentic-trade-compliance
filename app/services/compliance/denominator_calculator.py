"""
Denominator calculator for compliance rule calculations.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
import logging

from sqlalchemy import text

from app.models import db, Fund
from app.constants import DenominatorType

logger = logging.getLogger(__name__)


class DenominatorCalculator:
    """Service class for calculating compliance rule denominators."""
    
    @staticmethod
    def calculate_denominator(fund_id: int, trade_id: int, denominator_type: DenominatorType) -> Optional[Decimal]:
        """
        Calculate denominator value for a compliance rule.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            denominator_type: Type of denominator to calculate
            
        Returns:
            Denominator value as Decimal, or None if calculation failed
        """
        logger.debug(f"Calculating {denominator_type.value} denominator for fund {fund_id}, trade {trade_id}")
        
        if denominator_type == DenominatorType.TOTAL_ASSETS:
            return DenominatorCalculator._calculate_total_assets(fund_id, trade_id)
        elif denominator_type == DenominatorType.NET_ASSETS:
            return DenominatorCalculator._calculate_net_assets(fund_id, trade_id)
        elif denominator_type == DenominatorType.TOTAL_ASSETS_EX_CASH:
            return DenominatorCalculator._calculate_total_assets_ex_cash(fund_id, trade_id)
        elif denominator_type == DenominatorType.PROHIBIT:
            return Decimal('1')  # Prohibit rules don't use percentage calculations
        elif denominator_type == DenominatorType.SHARES_OUTSTANDING_FE:
            return Decimal('1')  # For Each rules calculate per holding
        else:
            logger.error(f"Unknown denominator type: {denominator_type}")
            return None
    
    @staticmethod
    def _calculate_total_assets(fund_id: int, trade_id: int) -> Optional[Decimal]:
        """
        Calculate total assets (holdings market value + cash).
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            
        Returns:
            Total assets as Decimal
        """
        logger.debug(f"Calculating total assets for fund {fund_id}, trade {trade_id}")
        
        # Get fund cash
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return None
        
        cash = fund.cash
        
        # Calculate holdings market value
        holdings_value = DenominatorCalculator._calculate_holdings_market_value(fund_id, trade_id)
        if holdings_value is None:
            return None
        
        total_assets = holdings_value + cash
        logger.debug(f"Total assets for fund {fund_id}: {total_assets} (holdings: {holdings_value}, cash: {cash})")
        return total_assets
    
    @staticmethod
    def _calculate_net_assets(fund_id: int, trade_id: int) -> Optional[Decimal]:
        """
        Calculate net assets (alias for total assets).
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            
        Returns:
            Net assets as Decimal
        """
        return DenominatorCalculator._calculate_total_assets(fund_id, trade_id)
    
    @staticmethod
    def _calculate_total_assets_ex_cash(fund_id: int, trade_id: int) -> Optional[Decimal]:
        """
        Calculate total assets excluding cash.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            
        Returns:
            Total assets ex cash as Decimal
        """
        logger.debug(f"Calculating total assets ex cash for fund {fund_id}, trade {trade_id}")
        
        holdings_value = DenominatorCalculator._calculate_holdings_market_value(fund_id, trade_id)
        if holdings_value is None:
            return None
        
        logger.debug(f"Total assets ex cash for fund {fund_id}: {holdings_value}")
        return holdings_value
    
    @staticmethod
    def _calculate_holdings_market_value(fund_id: int, trade_id: int) -> Optional[Decimal]:
        """
        Calculate total market value of holdings.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            
        Returns:
            Total holdings market value as Decimal
        """
        logger.debug(f"Calculating holdings market value for fund {fund_id}, trade {trade_id}")
        
        # Build query to get holdings with current prices
        if trade_id == 0:
            # Portfolio compliance - use actual holdings
            query = text("""
                SELECT h.ticker, h.shares, sp.price
                FROM holdings h
                INNER JOIN (
                    SELECT ticker, price
                    FROM securities_price
                    WHERE price_date = (
                        SELECT MAX(price_date)
                        FROM securities_price sp2
                        WHERE sp2.ticker = securities_price.ticker
                    )
                ) sp ON h.ticker = sp.ticker
                WHERE h.fund_id = :fund_id
            """)
        else:
            # Trade compliance - use staging holdings
            query = text("""
                SELECT hs.ticker, hs.shares, sp.price
                FROM holdings_staging hs
                INNER JOIN (
                    SELECT ticker, price
                    FROM securities_price
                    WHERE price_date = (
                        SELECT MAX(price_date)
                        FROM securities_price sp2
                        WHERE sp2.ticker = securities_price.ticker
                    )
                ) sp ON hs.ticker = sp.ticker
                WHERE hs.fund_id = :fund_id AND hs.trade_id = :trade_id
            """)
        
        try:
            if trade_id == 0:
                result = db.session.execute(query, {'fund_id': fund_id}).fetchall()
            else:
                result = db.session.execute(query, {'fund_id': fund_id, 'trade_id': trade_id}).fetchall()
            
            total_value = Decimal('0.00')
            for row in result:
                market_value = Decimal(str(row.shares)) * Decimal(str(row.price))
                total_value += market_value
                logger.debug(f"Holding {row.ticker}: {row.shares} shares @ {row.price} = {market_value}")
            
            logger.debug(f"Total holdings market value for fund {fund_id}: {total_value}")
            return total_value
            
        except Exception as e:
            logger.error(f"Failed to calculate holdings market value for fund {fund_id}: {e}")
            return None
    
    @staticmethod
    def get_holdings_for_fe_calculation(fund_id: int, trade_id: int) -> List[Dict[str, Any]]:
        """
        Get holdings data for For Each calculations.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            
        Returns:
            List of holdings with shares and shares outstanding
        """
        logger.debug(f"Getting holdings for FE calculation for fund {fund_id}, trade {trade_id}")
        
        if trade_id == 0:
            # Portfolio compliance - use actual holdings
            query = text("""
                SELECT h.ticker, h.shares, s.shares_outstanding
                FROM holdings h
                INNER JOIN securities s ON h.ticker = s.ticker
                WHERE h.fund_id = :fund_id
            """)
        else:
            # Trade compliance - use staging holdings
            query = text("""
                SELECT hs.ticker, hs.shares, s.shares_outstanding
                FROM holdings_staging hs
                INNER JOIN securities s ON hs.ticker = s.ticker
                WHERE hs.fund_id = :fund_id AND hs.trade_id = :trade_id
            """)
        
        try:
            if trade_id == 0:
                result = db.session.execute(query, {'fund_id': fund_id}).fetchall()
            else:
                result = db.session.execute(query, {'fund_id': fund_id, 'trade_id': trade_id}).fetchall()
            
            holdings = []
            for row in result:
                holdings.append({
                    'ticker': row.ticker,
                    'shares': Decimal(str(row.shares)),
                    'shares_outstanding': row.shares_outstanding
                })
            
            logger.debug(f"Retrieved {len(holdings)} holdings for FE calculation")
            return holdings
            
        except Exception as e:
            logger.error(f"Failed to get holdings for FE calculation: {e}")
            return []
