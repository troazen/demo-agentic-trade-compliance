"""
Fund service for managing fund operations.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import db, Fund, Holding
from app.config import Config

logger = logging.getLogger(__name__)


class FundService:
    """Service class for fund-related operations."""
    
    @staticmethod
    def get_all_funds() -> List[Dict[str, Any]]:
        """
        Get all funds with summary information.
        
        Returns:
            List of fund dictionaries with summary data
        """
        logger.debug("Retrieving all funds")
        
        funds = Fund.query.all()
        result = []
        
        for fund in funds:
            fund_data = fund.to_dict()
            fund_data['holdings_count'] = fund.get_holdings_count()
            result.append(fund_data)
        
        logger.debug(f"Retrieved {len(result)} funds")
        return result
    
    @staticmethod
    def get_fund_by_id(fund_id: int) -> Optional[Fund]:
        """
        Get fund by ID with all details.
        
        Args:
            fund_id: Fund ID to retrieve
            
        Returns:
            Fund object or None if not found
        """
        logger.debug(f"Retrieving fund {fund_id}")
        
        fund = Fund.query.get(fund_id)
        if fund:
            logger.debug(f"Found fund: {fund.fund_name}")
        else:
            logger.warning(f"Fund {fund_id} not found")
        
        return fund
    
    @staticmethod
    def update_fund_cash(fund_id: int, new_cash: Decimal) -> bool:
        """
        Update fund cash amount.
        
        Args:
            fund_id: Fund ID to update
            new_cash: New cash amount
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Updating cash for fund {fund_id} to {new_cash}")
        
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return False
        
        old_cash = fund.cash
        fund.cash = new_cash
        
        try:
            db.session.commit()
            logger.info(f"Fund {fund_id} cash updated from {old_cash} to {new_cash}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update fund {fund_id} cash: {e}")
            return False
    
    @staticmethod
    def calculate_total_assets(fund_id: int) -> Optional[Decimal]:
        """
        Calculate total assets for a fund (holdings market value + cash).
        
        Args:
            fund_id: Fund ID to calculate for
            
        Returns:
            Total assets as Decimal, or None if fund not found
        """
        logger.debug(f"Calculating total assets for fund {fund_id}")
        
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return None
        
        total_assets = fund.calculate_total_assets()
        logger.info(f"Fund {fund_id} total assets: {total_assets}")
        return total_assets
    
    @staticmethod
    def calculate_net_assets(fund_id: int) -> Optional[Decimal]:
        """
        Calculate net assets for a fund (alias for total assets).
        
        Args:
            fund_id: Fund ID to calculate for
            
        Returns:
            Net assets as Decimal, or None if fund not found
        """
        logger.debug(f"Calculating net assets for fund {fund_id}")
        
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return None
        
        net_assets = fund.calculate_net_assets()
        logger.info(f"Fund {fund_id} net assets: {net_assets}")
        return net_assets
    
    @staticmethod
    def calculate_total_assets_ex_cash(fund_id: int) -> Optional[Decimal]:
        """
        Calculate total assets excluding cash for a fund.
        
        Args:
            fund_id: Fund ID to calculate for
            
        Returns:
            Total assets ex cash as Decimal, or None if fund not found
        """
        logger.debug(f"Calculating total assets ex cash for fund {fund_id}")
        
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return None
        
        total_assets_ex_cash = fund.calculate_total_assets_ex_cash()
        logger.info(f"Fund {fund_id} total assets ex cash: {total_assets_ex_cash}")
        return total_assets_ex_cash
    
    @staticmethod
    def get_fund_holdings_with_market_values(fund_id: int) -> List[Dict[str, Any]]:
        """
        Get fund holdings with current market values.
        
        Args:
            fund_id: Fund ID to get holdings for
            
        Returns:
            List of holding dictionaries with market values
        """
        logger.debug(f"Retrieving holdings with market values for fund {fund_id}")
        
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return []
        
        holdings = []
        for holding in fund.holdings:
            holding_data = holding.to_dict()
            holdings.append(holding_data)
        
        logger.debug(f"Retrieved {len(holdings)} holdings for fund {fund_id}")
        return holdings
    
    @staticmethod
    def create_fund(fund_name: str, initial_cash: Decimal = Decimal('0.00')) -> Optional[Fund]:
        """
        Create a new fund.
        
        Args:
            fund_name: Name of the fund
            initial_cash: Initial cash amount
            
        Returns:
            Created Fund object or None if creation failed
        """
        logger.debug(f"Creating new fund: {fund_name} with cash: {initial_cash}")
        
        # Check if fund name already exists
        existing_fund = Fund.query.filter_by(fund_name = fund_name).first()
        if existing_fund:
            logger.error(f"Fund with name '{fund_name}' already exists")
            return None
        
        try:
            fund = Fund(
                fund_name = fund_name,
                cash = initial_cash
            )
            db.session.add(fund)
            db.session.commit()
            
            logger.info(f"Created fund {fund.fund_id}: {fund_name}")
            return fund
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create fund '{fund_name}': {e}")
            return None
