"""
Holding models for fund positions and staging.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models import db
from app.config import get_eastern_time

logger = logging.getLogger(__name__)


class Holding(db.Model):
    """
    Holding model representing a security position held by a fund.
    
    Each holding links a fund to a security with the number of shares held.
    """
    
    __tablename__ = 'holdings'
    
    # Primary key
    holding_id = Column(Integer, primary_key = True, autoincrement = True)
    
    # Foreign keys
    fund_id = Column(Integer, ForeignKey('funds.fund_id'), nullable = False)
    ticker = Column(String(10), ForeignKey('securities.ticker'), nullable = False)
    
    # Position details
    shares = Column(Numeric(15, 0), nullable = False)  # No fractional shares
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    updated_at = Column(DateTime, nullable = False, default = get_eastern_time, 
                       onupdate = get_eastern_time)
    
    # Relationships
    fund = relationship("Fund", back_populates = "holdings")
    security = relationship("Security", back_populates = "holdings")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('fund_id', 'ticker', name = 'uq_fund_ticker'),
    )
    
    def __repr__(self) -> str:
        return f"<Holding(holding_id={self.holding_id}, fund_id={self.fund_id}, ticker='{self.ticker}', shares={self.shares})>"
    
    def to_dict(self) -> dict:
        """Convert holding to dictionary representation."""
        current_price = self.security.get_latest_price() if self.security else None
        market_value = current_price * self.shares if current_price else None
        
        return {
            'holding_id': self.holding_id,
            'fund_id': self.fund_id,
            'ticker': self.ticker,
            'shares': int(self.shares),
            'current_price': float(current_price) if current_price else None,
            'market_value': float(market_value) if market_value else None,
            'security_name': self.security.name if self.security else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_market_value(self) -> Optional[Decimal]:
        """
        Calculate current market value of this holding.
        
        Returns:
            Market value as Decimal, or None if no current price available
        """
        if not self.security:
            return None
            
        current_price = self.security.get_latest_price()
        if current_price is None:
            logger.warning(f"No current price available for security {self.ticker}")
            return None
        
        market_value = current_price * self.shares
        logger.debug(f"Holding {self.ticker}: {self.shares} shares @ {current_price} = {market_value}")
        return market_value


class HoldingStaging(db.Model):
    """
    HoldingStaging model for temporary holdings during trade processing.
    
    Used to stage holdings changes during compliance checking before applying to actual holdings.
    """
    
    __tablename__ = 'holdings_staging'
    
    # Primary key
    staging_id = Column(Integer, primary_key = True, autoincrement = True)
    
    # Foreign keys
    fund_id = Column(Integer, ForeignKey('funds.fund_id'), nullable = False)
    ticker = Column(String(10), ForeignKey('securities.ticker'), nullable = False)
    trade_id = Column(Integer, ForeignKey('trades.trade_id'), nullable = False)
    
    # Position details
    shares = Column(Numeric(15, 0), nullable = False)  # No fractional shares
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    
    # Relationships
    fund = relationship("Fund")
    security = relationship("Security", back_populates = "holdings_staging")
    trade = relationship("Trade")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('fund_id', 'ticker', 'trade_id', name = 'uq_fund_ticker_trade'),
    )
    
    def __repr__(self) -> str:
        return f"<HoldingStaging(staging_id={self.staging_id}, fund_id={self.fund_id}, ticker='{self.ticker}', trade_id={self.trade_id}, shares={self.shares})>"
    
    def to_dict(self) -> dict:
        """Convert staging holding to dictionary representation."""
        current_price = self.security.get_latest_price() if self.security else None
        market_value = current_price * self.shares if current_price else None
        
        return {
            'staging_id': self.staging_id,
            'fund_id': self.fund_id,
            'ticker': self.ticker,
            'trade_id': self.trade_id,
            'shares': int(self.shares),
            'current_price': float(current_price) if current_price else None,
            'market_value': float(market_value) if market_value else None,
            'security_name': self.security.name if self.security else None,
            'created_at': self.created_at.isoformat()
        }
    
    def get_market_value(self) -> Optional[Decimal]:
        """
        Calculate current market value of this staging holding.
        
        Returns:
            Market value as Decimal, or None if no current price available
        """
        if not self.security:
            return None
            
        current_price = self.security.get_latest_price()
        if current_price is None:
            logger.warning(f"No current price available for security {self.ticker}")
            return None
        
        market_value = current_price * self.shares
        logger.debug(f"Staging holding {self.ticker}: {self.shares} shares @ {current_price} = {market_value}")
        return market_value
