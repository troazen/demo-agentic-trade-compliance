"""
SecuritiesPrice model for storing historical security prices.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy import Column, String, Date, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.models import db
from app.config import get_eastern_time
from app.constants import PRICE_DECIMAL_PLACES

logger = logging.getLogger(__name__)


class SecuritiesPrice(db.Model):
    """
    SecuritiesPrice model for storing historical security prices.
    
    Each row represents a price for a security on a specific date.
    Only one price per day per security is stored.
    """
    
    __tablename__ = 'securities_price'
    
    # Primary key (composite)
    ticker = Column(String(10), ForeignKey('securities.ticker'), primary_key = True)
    price_date = Column(Date, primary_key = True)
    
    # Price information
    price = Column(Numeric(10, PRICE_DECIMAL_PLACES), nullable = False)
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    updated_at = Column(DateTime, nullable = False, default = get_eastern_time, 
                       onupdate = get_eastern_time)
    
    # Relationships
    security = relationship("Security", back_populates = "prices")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_ticker_date', 'ticker', 'price_date'),
        Index('idx_price_date', 'price_date'),
    )
    
    def __repr__(self) -> str:
        return f"<SecuritiesPrice(ticker='{self.ticker}', date={self.price_date}, price={self.price})>"
    
    def to_dict(self) -> dict:
        """Convert price record to dictionary representation."""
        return {
            'ticker': self.ticker,
            'price_date': self.price_date.isoformat(),
            'price': float(self.price),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def get_latest_price_for_ticker(cls, ticker: str) -> Optional[Decimal]:
        """
        Get the latest price for a specific ticker.
        
        Args:
            ticker: Security ticker symbol
            
        Returns:
            Latest price as Decimal, or None if no price found
        """
        logger.debug(f"Getting latest price for ticker {ticker}")
        
        latest_price_record = cls.query.filter_by(
            ticker = ticker
        ).order_by(cls.price_date.desc()).first()
        
        if latest_price_record:
            logger.debug(f"Latest price for {ticker}: {latest_price_record.price}")
            return latest_price_record.price
        else:
            logger.warning(f"No price found for ticker {ticker}")
            return None
    
    @classmethod
    def get_price_for_date(cls, ticker: str, target_date: date) -> Optional[Decimal]:
        """
        Get the price for a specific ticker on a specific date.
        
        Args:
            ticker: Security ticker symbol
            target_date: Date to get price for
            
        Returns:
            Price as Decimal, or None if no price found for that date
        """
        logger.debug(f"Getting price for ticker {ticker} on {target_date}")
        
        price_record = cls.query.filter_by(
            ticker = ticker,
            price_date = target_date
        ).first()
        
        if price_record:
            logger.debug(f"Price for {ticker} on {target_date}: {price_record.price}")
            return price_record.price
        else:
            logger.warning(f"No price found for ticker {ticker} on {target_date}")
            return None
    
    @classmethod
    def get_all_latest_prices(cls) -> dict:
        """
        Get the latest price for all securities.
        
        Returns:
            Dictionary mapping ticker to latest price
        """
        logger.debug("Getting latest prices for all securities")
        
        # Subquery to get the latest date for each ticker
        from sqlalchemy import func
        latest_dates = db.session.query(
            cls.ticker,
            func.max(cls.price_date).label('latest_date')
        ).group_by(cls.ticker).subquery()
        
        # Join with main table to get latest prices
        latest_prices = cls.query.join(
            latest_dates,
            (cls.ticker == latest_dates.c.ticker) & 
            (cls.price_date == latest_dates.c.latest_date)
        ).all()
        
        result = {price.ticker: price.price for price in latest_prices}
        logger.debug(f"Retrieved latest prices for {len(result)} securities")
        
        return result
