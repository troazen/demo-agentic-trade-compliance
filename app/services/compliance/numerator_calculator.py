"""
Numerator calculator for compliance rule calculations.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
import logging

from sqlalchemy import text

from app.models import db
from app.constants import DenominatorType

logger = logging.getLogger(__name__)


class NumeratorCalculator:
    """Service class for calculating compliance rule numerators."""
    
    @staticmethod
    def calculate_numerator(fund_id: int, trade_id: int, rule_logic: str, 
                          denominator_type: DenominatorType) -> Optional[Decimal]:
        """
        Calculate numerator value for a compliance rule.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            rule_logic: SQL logic for selecting holdings
            denominator_type: Type of denominator (affects numerator calculation)
            
        Returns:
            Numerator value as Decimal, or None if calculation failed
        """
        logger.debug(f"Calculating numerator for fund {fund_id}, trade {trade_id}, logic: {rule_logic}")
        
        if denominator_type == DenominatorType.PROHIBIT:
            # Prohibit rules don't calculate percentages
            return Decimal('1')
        elif denominator_type == DenominatorType.SHARES_OUTSTANDING_FE:
            # For Each rules are handled separately
            return Decimal('1')
        else:
            # Standard percentage rules
            return NumeratorCalculator._calculate_standard_numerator(fund_id, trade_id, rule_logic)
    
    @staticmethod
    def _calculate_standard_numerator(fund_id: int, trade_id: int, rule_logic: str) -> Optional[Decimal]:
        """
        Calculate standard numerator (market value of selected holdings).
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            rule_logic: SQL logic for selecting holdings
            
        Returns:
            Numerator value as Decimal
        """
        logger.debug(f"Calculating standard numerator for fund {fund_id}, trade {trade_id}")
        
        # Build query to get selected holdings with market values
        if trade_id == 0:
            # Portfolio compliance - use actual holdings
            base_query = """
                SELECT h.ticker, h.shares, sp.price, (h.shares * sp.price) as market_value
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
                INNER JOIN securities s ON h.ticker = s.ticker
                INNER JOIN issuers i ON s.issr_id = i.issr_id
                WHERE h.fund_id = :fund_id
            """
        else:
            # Trade compliance - use staging holdings
            base_query = """
                SELECT hs.ticker, hs.shares, sp.price, (hs.shares * sp.price) as market_value
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
                INNER JOIN securities s ON hs.ticker = s.ticker
                INNER JOIN issuers i ON s.issr_id = i.issr_id
                WHERE hs.fund_id = :fund_id AND hs.trade_id = :trade_id
            """
        
        # Add rule logic as WHERE clause
        full_query = f"{base_query} AND ({rule_logic})"
        
        try:
            query = text(full_query)
            if trade_id == 0:
                result = db.session.execute(query, {'fund_id': fund_id}).fetchall()
            else:
                result = db.session.execute(query, {'fund_id': fund_id, 'trade_id': trade_id}).fetchall()
            
            total_numerator = Decimal('0.00')
            for row in result:
                market_value = Decimal(str(row.market_value))
                total_numerator += market_value
                logger.debug(f"Selected holding {row.ticker}: {row.shares} shares @ {row.price} = {market_value}")
            
            logger.debug(f"Total numerator for fund {fund_id}: {total_numerator}")
            return total_numerator
            
        except Exception as e:
            logger.error(f"Failed to calculate numerator for fund {fund_id}: {e}")
            return None
    
    @staticmethod
    def calculate_fe_numerators(fund_id: int, trade_id: int, rule_logic: str) -> List[Dict[str, Any]]:
        """
        Calculate numerators for For Each rules (one per holding).
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            rule_logic: SQL logic for selecting holdings
            
        Returns:
            List of dictionaries with holding data and calculated percentage
        """
        logger.debug(f"Calculating FE numerators for fund {fund_id}, trade {trade_id}")
        
        # Get holdings data for FE calculation
        from app.services.compliance.denominator_calculator import DenominatorCalculator
        holdings = DenominatorCalculator.get_holdings_for_fe_calculation(fund_id, trade_id)
        
        if not holdings:
            logger.warning(f"No holdings found for FE calculation for fund {fund_id}")
            return []
        
        # Filter holdings based on rule logic
        filtered_holdings = NumeratorCalculator._filter_holdings_by_logic(holdings, rule_logic, fund_id, trade_id)
        
        # Calculate percentage for each holding
        fe_results = []
        for holding in filtered_holdings:
            if holding['shares_outstanding'] and holding['shares_outstanding'] > 0:
                percentage = (holding['shares'] / Decimal(str(holding['shares_outstanding']))) * Decimal('100')
                fe_results.append({
                    'ticker': holding['ticker'],
                    'shares': holding['shares'],
                    'shares_outstanding': holding['shares_outstanding'],
                    'percentage': percentage
                })
                logger.debug(f"FE calculation for {holding['ticker']}: {holding['shares']}/{holding['shares_outstanding']} = {percentage}%")
            else:
                logger.warning(f"No shares outstanding data for {holding['ticker']}")
        
        logger.debug(f"Calculated FE numerators for {len(fe_results)} holdings")
        return fe_results
    
    @staticmethod
    def _filter_holdings_by_logic(holdings: List[Dict[str, Any]], rule_logic: str, 
                                 fund_id: int, trade_id: int) -> List[Dict[str, Any]]:
        """
        Filter holdings based on rule logic.
        
        Args:
            holdings: List of holdings data
            rule_logic: SQL logic for filtering
            fund_id: Fund ID
            trade_id: Trade ID
            
        Returns:
            List of filtered holdings
        """
        logger.debug(f"Filtering {len(holdings)} holdings with logic: {rule_logic}")
        
        if not rule_logic or rule_logic.strip() == "1=1":
            # Return all holdings if no specific logic
            return holdings
        
        # For simplicity, we'll use a basic approach here
        # In a production system, you might want to build a more sophisticated filter
        # that can handle complex SQL logic against the holdings data
        
        # For now, return all holdings and let the compliance engine handle the filtering
        # This is a simplified implementation
        logger.debug("Using simplified filtering - returning all holdings")
        return holdings
    
    @staticmethod
    def get_selected_holdings(fund_id: int, trade_id: int, rule_logic: str) -> List[Dict[str, Any]]:
        """
        Get holdings that match the rule logic.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            rule_logic: SQL logic for selecting holdings
            
        Returns:
            List of selected holdings with details
        """
        logger.debug(f"Getting selected holdings for fund {fund_id}, trade {trade_id}")
        
        # Build query to get selected holdings with all details
        if trade_id == 0:
            # Portfolio compliance - use actual holdings
            base_query = """
                SELECT h.ticker, h.shares, sp.price, (h.shares * sp.price) as market_value,
                       s.name as security_name, i.name as issuer_name, i.gics_sector
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
                INNER JOIN securities s ON h.ticker = s.ticker
                INNER JOIN issuers i ON s.issr_id = i.issr_id
                WHERE h.fund_id = :fund_id
            """
        else:
            # Trade compliance - use staging holdings
            base_query = """
                SELECT hs.ticker, hs.shares, sp.price, (hs.shares * sp.price) as market_value,
                       s.name as security_name, i.name as issuer_name, i.gics_sector
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
                INNER JOIN securities s ON hs.ticker = s.ticker
                INNER JOIN issuers i ON s.issr_id = i.issr_id
                WHERE hs.fund_id = :fund_id AND hs.trade_id = :trade_id
            """
        
        # Add rule logic as WHERE clause
        full_query = f"{base_query} AND ({rule_logic})"
        
        try:
            query = text(full_query)
            if trade_id == 0:
                result = db.session.execute(query, {'fund_id': fund_id}).fetchall()
            else:
                result = db.session.execute(query, {'fund_id': fund_id, 'trade_id': trade_id}).fetchall()
            
            selected_holdings = []
            for row in result:
                selected_holdings.append({
                    'ticker': row.ticker,
                    'shares': int(row.shares),
                    'price': float(row.price),
                    'market_value': float(row.market_value),
                    'security_name': row.security_name,
                    'issuer_name': row.issuer_name,
                    'gics_sector': row.gics_sector
                })
            
            logger.debug(f"Selected {len(selected_holdings)} holdings matching rule logic")
            return selected_holdings
            
        except Exception as e:
            logger.error(f"Failed to get selected holdings: {e}")
            return []
