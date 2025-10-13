"""
Security model representing financial instruments.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models import db
from app.config import get_eastern_time

logger = logging.getLogger(__name__)


class Security(db.Model):
    """
    Security model representing financial instruments (equity stocks).
    
    Uses ticker as primary key for simplicity as specified in PRD.
    """
    
    __tablename__ = 'securities'
    
    # Primary key (ticker as string)
    ticker = Column(String(10), primary_key = True)
    
    # Security details
    name = Column(String(255), nullable = False)
    type = Column(String(50), nullable = False, default = 'Equity Stock')
    
    # Market information
    shares_outstanding = Column(Integer, nullable = True)
    market_cap = Column(Integer, nullable = True)  # Big integer, no decimals
    
    # Foreign key to issuer
    issr_id = Column(Integer, ForeignKey('issuers.issr_id'), nullable = False)
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    updated_at = Column(DateTime, nullable = False, default = get_eastern_time, 
                       onupdate = get_eastern_time)
    
    # Relationships
    issuer = relationship("Issuer", back_populates = "securities")
    holdings = relationship("Holding", back_populates = "security", cascade = "all, delete-orphan")
    holdings_staging = relationship("HoldingStaging", back_populates = "security", cascade = "all, delete-orphan")
    trades = relationship("Trade", back_populates = "security", cascade = "all, delete-orphan")
    prices = relationship("SecuritiesPrice", back_populates = "security", cascade = "all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Security(ticker='{self.ticker}', name='{self.name}')>"
    
    def to_dict(self) -> dict:
        """Convert security to dictionary representation."""
        return {
            'ticker': self.ticker,
            'name': self.name,
            'type': self.type,
            'shares_outstanding': self.shares_outstanding,
            'market_cap': self.market_cap,
            'issr_id': self.issr_id,
            'issuer_name': self.issuer.name if self.issuer else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_latest_price(self) -> Optional[Decimal]:
        """
        Get the latest price for this security.
        
        Returns:
            Latest price as Decimal, or None if no price found
        """
        logger.debug(f"Getting latest price for security {self.ticker}")
        
        latest_price_record = SecuritiesPrice.query.filter_by(
            ticker = self.ticker
        ).order_by(SecuritiesPrice.price_date.desc()).first()
        
        if latest_price_record:
            logger.debug(f"Latest price for {self.ticker}: {latest_price_record.price}")
            return latest_price_record.price
        else:
            logger.warning(f"No price found for security {self.ticker}")
            return None
    
    def get_price_for_date(self, target_date: datetime) -> Optional[Decimal]:
        """
        Get the price for this security on a specific date.
        
        Args:
            target_date: Date to get price for
            
        Returns:
            Price as Decimal, or None if no price found for that date
        """
        logger.debug(f"Getting price for security {self.ticker} on {target_date}")
        
        price_record = SecuritiesPrice.query.filter_by(
            ticker = self.ticker,
            price_date = target_date.date()
        ).first()
        
        if price_record:
            logger.debug(f"Price for {self.ticker} on {target_date}: {price_record.price}")
            return price_record.price
        else:
            logger.warning(f"No price found for security {self.ticker} on {target_date}")
            return None
