"""
Fund model representing investment funds.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import logging

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text
from sqlalchemy.orm import relationship

from app.models import db
from app.config import get_eastern_time

logger = logging.getLogger(__name__)


class Fund(db.Model):
    """
    Fund model representing an investment fund.
    
    Each fund has a portfolio of holdings and cash.
    """
    
    __tablename__ = 'funds'
    
    # Primary key
    fund_id = Column(Integer, primary_key = True, autoincrement = True)
    
    # Fund details
    fund_name = Column(String(255), nullable = False, unique = True)
    cash = Column(Numeric(15, 2), nullable = False, default = 0.00)
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    updated_at = Column(DateTime, nullable = False, default = get_eastern_time, 
                       onupdate = get_eastern_time)
    
    # Relationships
    holdings = relationship("Holding", back_populates = "fund", cascade = "all, delete-orphan")
    trades = relationship("Trade", back_populates = "fund", cascade = "all, delete-orphan")
    alerts = relationship("Alert", back_populates = "fund", cascade = "all, delete-orphan")
    rule_attachments = relationship("RuleAttachment", back_populates = "fund", cascade = "all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Fund(fund_id={self.fund_id}, fund_name='{self.fund_name}', cash={self.cash})>"
    
    def to_dict(self) -> dict:
        """Convert fund to dictionary representation."""
        return {
            'fund_id': self.fund_id,
            'fund_name': self.fund_name,
            'cash': float(self.cash),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_holdings_count(self) -> int:
        """Get the number of unique securities held by this fund."""
        return len(self.holdings)
    
    def calculate_total_assets(self) -> Decimal:
        """
        Calculate total assets (holdings market value + cash).
        
        Returns:
            Total assets as Decimal
        """
        logger.debug(f"Calculating total assets for fund {self.fund_id}")
        
        total_holdings_value = Decimal('0.00')
        for holding in self.holdings:
            # Get latest price for the security
            latest_price = holding.security.get_latest_price()
            if latest_price:
                market_value = latest_price * holding.shares
                total_holdings_value += market_value
                logger.debug(f"Holding {holding.ticker}: {holding.shares} shares @ {latest_price} = {market_value}")
        
        total_assets = total_holdings_value + self.cash
        logger.debug(f"Fund {self.fund_id} total assets: {total_assets} (holdings: {total_holdings_value}, cash: {self.cash})")
        
        return total_assets
    
    def calculate_net_assets(self) -> Decimal:
        """
        Calculate net assets (alias for total assets).
        
        Returns:
            Net assets as Decimal
        """
        return self.calculate_total_assets()
    
    def calculate_total_assets_ex_cash(self) -> Decimal:
        """
        Calculate total assets excluding cash.
        
        Returns:
            Total assets ex cash as Decimal
        """
        logger.debug(f"Calculating total assets ex cash for fund {self.fund_id}")
        
        total_holdings_value = Decimal('0.00')
        for holding in self.holdings:
            latest_price = holding.security.get_latest_price()
            if latest_price:
                market_value = latest_price * holding.shares
                total_holdings_value += market_value
        
        logger.debug(f"Fund {self.fund_id} total assets ex cash: {total_holdings_value}")
        return total_holdings_value
