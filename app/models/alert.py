"""
Alert model for compliance rule violations.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
import logging

from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.models import db
from app.config import get_eastern_time
from app.constants import AlertStatus

logger = logging.getLogger(__name__)


class Alert(db.Model):
    """
    Alert model representing compliance rule violations.
    
    Each alert is created when a compliance rule is triggered.
    """
    
    __tablename__ = 'alerts'
    
    # Primary key
    alert_id = Column(Integer, primary_key = True, autoincrement = True)
    
    # Foreign keys
    rule_id = Column(Integer, ForeignKey('rules.rule_id'), nullable = False)
    fund_id = Column(Integer, ForeignKey('funds.fund_id'), nullable = False)
    trade_id = Column(Integer, ForeignKey('trades.trade_id'), nullable = True)  # Null for portfolio compliance
    
    # Alert details
    calculated_percentage = Column(Numeric(10, 4), nullable = True)  # Null for prohibit rules
    holdings_triggered = Column(Text, nullable = True)  # JSON string of holdings that triggered
    
    # User response
    status = Column(Enum(AlertStatus), nullable = False, default = AlertStatus.PENDING)
    override_reason = Column(Text, nullable = True)
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    updated_at = Column(DateTime, nullable = False, default = get_eastern_time, 
                       onupdate = get_eastern_time)
    
    # Relationships
    rule = relationship("Rule", back_populates = "alerts")
    fund = relationship("Fund", back_populates = "alerts")
    trade = relationship("Trade", back_populates = "alerts")
    
    def __repr__(self) -> str:
        return f"<Alert(alert_id={self.alert_id}, rule_id={self.rule_id}, fund_id={self.fund_id}, status={self.status.value})>"
    
    def to_dict(self) -> dict:
        """Convert alert to dictionary representation."""
        return {
            'alert_id': self.alert_id,
            'rule_id': self.rule_id,
            'fund_id': self.fund_id,
            'trade_id': self.trade_id,
            'calculated_percentage': float(self.calculated_percentage) if self.calculated_percentage else None,
            'holdings_triggered': self.holdings_triggered,
            'status': self.status.value,
            'override_reason': self.override_reason,
            'rule_name': self.rule.rule_name if self.rule else None,
            'alert_message': self.rule.alert_message if self.rule else None,
            'fund_name': self.fund.fund_name if self.fund else None,
            'trade_ticker': self.trade.ticker if self.trade else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def is_overridden(self) -> bool:
        """Check if alert has been overridden."""
        return self.status == AlertStatus.OVERRIDDEN
    
    def is_cancelled(self) -> bool:
        """Check if alert has been cancelled."""
        return self.status == AlertStatus.CANCELLED
    
    def is_pending(self) -> bool:
        """Check if alert is still pending."""
        return self.status == AlertStatus.PENDING
    
    def override(self, reason: str) -> None:
        """
        Override this alert with a reason.
        
        Args:
            reason: Override reason text
        """
        self.status = AlertStatus.OVERRIDDEN
        self.override_reason = reason
        logger.info(f"Alert {self.alert_id} overridden with reason: {reason}")
    
    def cancel(self) -> None:
        """Cancel this alert."""
        self.status = AlertStatus.CANCELLED
        logger.info(f"Alert {self.alert_id} cancelled")
    
    def get_holdings_triggered_list(self) -> list:
        """
        Parse holdings_triggered JSON string into list.
        
        Returns:
            List of holdings that triggered the alert
        """
        if not self.holdings_triggered:
            return []
        
        try:
            import json
            return json.loads(self.holdings_triggered)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse holdings_triggered for alert {self.alert_id}: {e}")
            return []
    
    def set_holdings_triggered(self, holdings_list: list) -> None:
        """
        Set holdings_triggered from a list.
        
        Args:
            holdings_list: List of holdings that triggered the alert
        """
        try:
            import json
            self.holdings_triggered = json.dumps(holdings_list)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize holdings_triggered for alert {self.alert_id}: {e}")
            self.holdings_triggered = str(holdings_list)
