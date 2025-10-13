"""
Trade model representing fund transactions.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.models import db
from app.config import get_eastern_time
from app.constants import TradeStatus, TradeDirection

logger = logging.getLogger(__name__)


class Trade(db.Model):
    """
    Trade model representing a fund transaction (BUY or SELL).
    
    Each trade involves one fund, one security, and a number of shares.
    """
    
    __tablename__ = 'trades'
    
    # Primary key
    trade_id = Column(Integer, primary_key = True, autoincrement = True)
    
    # Foreign keys
    fund_id = Column(Integer, ForeignKey('funds.fund_id'), nullable = False)
    ticker = Column(String(10), ForeignKey('securities.ticker'), nullable = False)
    
    # Trade details
    direction = Column(Enum(TradeDirection), nullable = False)
    shares = Column(Numeric(15, 0), nullable = False)  # No fractional shares
    price = Column(Numeric(10, 3), nullable = True)  # Price at time of trade
    total_value = Column(Numeric(15, 2), nullable = True)  # Total trade value
    
    # Status tracking
    status = Column(Enum(TradeStatus), nullable = False, default = TradeStatus.SUBMITTED)
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    updated_at = Column(DateTime, nullable = False, default = get_eastern_time, 
                       onupdate = get_eastern_time)
    
    # Relationships
    fund = relationship("Fund", back_populates = "trades")
    security = relationship("Security", back_populates = "trades")
    alerts = relationship("Alert", back_populates = "trade", cascade = "all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Trade(trade_id={self.trade_id}, fund_id={self.fund_id}, ticker='{self.ticker}', direction={self.direction.value}, shares={self.shares}, status={self.status.value})>"
    
    def to_dict(self) -> dict:
        """Convert trade to dictionary representation."""
        return {
            'trade_id': self.trade_id,
            'fund_id': self.fund_id,
            'ticker': self.ticker,
            'direction': self.direction.value,
            'shares': int(self.shares),
            'price': float(self.price) if self.price else None,
            'total_value': float(self.total_value) if self.total_value else None,
            'status': self.status.value,
            'fund_name': self.fund.fund_name if self.fund else None,
            'security_name': self.security.name if self.security else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def calculate_total_value(self) -> Optional[Decimal]:
        """
        Calculate total value of this trade.
        
        Returns:
            Total value as Decimal, or None if price not available
        """
        if self.price is None:
            logger.warning(f"No price available for trade {self.trade_id}")
            return None
        
        total_value = self.price * self.shares
        logger.debug(f"Trade {self.trade_id}: {self.shares} shares @ {self.price} = {total_value}")
        return total_value
    
    def is_buy(self) -> bool:
        """Check if this is a BUY trade."""
        return self.direction == TradeDirection.BUY
    
    def is_sell(self) -> bool:
        """Check if this is a SELL trade."""
        return self.direction == TradeDirection.SELL
    
    def update_status(self, new_status: TradeStatus) -> None:
        """
        Update trade status with logging.
        
        Args:
            new_status: New status to set
        """
        old_status = self.status
        self.status = new_status
        logger.info(f"Trade {self.trade_id} status changed from {old_status.value} to {new_status.value}")
    
    def is_completed(self) -> bool:
        """Check if trade is in a completed state."""
        return self.status in [TradeStatus.PROCESSED, TradeStatus.INVALID, TradeStatus.CANCELLED]
    
    def is_pending(self) -> bool:
        """Check if trade is in a pending state."""
        return self.status in [TradeStatus.SUBMITTED, TradeStatus.VALIDATING, TradeStatus.COMPLIANCE, TradeStatus.ALERT]
