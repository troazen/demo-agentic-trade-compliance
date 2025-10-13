"""
Rule models for compliance rules and fund attachments.
"""

from datetime import datetime
from typing import List, Optional
import logging

from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from app.models import db
from app.config import get_eastern_time
from app.constants import AlertIf, DenominatorType

logger = logging.getLogger(__name__)


class Rule(db.Model):
    """
    Rule model representing compliance rules.
    
    Each rule contains logic and thresholds for compliance checking.
    """
    
    __tablename__ = 'rules'
    
    # Primary key
    rule_id = Column(Integer, primary_key = True, autoincrement = True)
    
    # Rule details
    rule_name = Column(String(255), nullable = False, unique = True)
    alert_message = Column(Text, nullable = False)
    
    # Mode flags
    trade_compliance_mode = Column(Boolean, nullable = False, default = True)
    portfolio_compliance_mode = Column(Boolean, nullable = False, default = True)
    
    # Rule logic (SQL WHERE clause)
    logic = Column(Text, nullable = True)
    
    # Alert configuration
    denominator = Column(Enum(DenominatorType), nullable = False)
    alert_if = Column(Enum(AlertIf), nullable = True)  # Null for prohibit rules
    alert_level = Column(Numeric(10, 2), nullable = True)  # Null for prohibit rules
    
    # Status
    active = Column(Boolean, nullable = False, default = True)
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    updated_at = Column(DateTime, nullable = False, default = get_eastern_time, 
                       onupdate = get_eastern_time)
    
    # Relationships
    attachments = relationship("RuleAttachment", back_populates = "rule", cascade = "all, delete-orphan")
    alerts = relationship("Alert", back_populates = "rule", cascade = "all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Rule(rule_id={self.rule_id}, rule_name='{self.rule_name}', active={self.active})>"
    
    def to_dict(self) -> dict:
        """Convert rule to dictionary representation."""
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'alert_message': self.alert_message,
            'trade_compliance_mode': self.trade_compliance_mode,
            'portfolio_compliance_mode': self.portfolio_compliance_mode,
            'logic': self.logic,
            'denominator': self.denominator.value if self.denominator else None,
            'alert_if': self.alert_if.value if self.alert_if else None,
            'alert_level': float(self.alert_level) if self.alert_level else None,
            'active': self.active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def get_processed_logic(self) -> str:
        """
        Get processed rule logic for SQL execution.
        
        Returns:
            Processed logic string ready for WHERE clause
        """
        if not self.logic or not self.logic.strip():
            logger.debug(f"Rule {self.rule_id} has empty logic, using default")
            return "1=1"
        
        logic = self.logic.strip()
        
        # Remove WHERE prefix if present
        if logic.upper().startswith('WHERE'):
            logic = logic[5:].strip()
            logger.debug(f"Rule {self.rule_id} logic had WHERE prefix, removed")
        
        logger.debug(f"Rule {self.rule_id} processed logic: {logic}")
        return logic
    
    def is_prohibit_rule(self) -> bool:
        """Check if this is a prohibit rule."""
        return self.denominator == DenominatorType.PROHIBIT
    
    def get_attached_fund_ids(self) -> List[int]:
        """Get list of fund IDs this rule is attached to."""
        return [attachment.fund_id for attachment in self.attachments if attachment.active]
    
    def is_attached_to_fund(self, fund_id: int) -> bool:
        """
        Check if rule is attached to a specific fund.
        
        Args:
            fund_id: Fund ID to check
            
        Returns:
            True if attached, False otherwise
        """
        return any(attachment.fund_id == fund_id and attachment.active 
                  for attachment in self.attachments)


class RuleAttachment(db.Model):
    """
    RuleAttachment model for many-to-many relationship between rules and funds.
    
    Links compliance rules to specific funds.
    """
    
    __tablename__ = 'rules_attachments'
    
    # Primary key
    attachment_id = Column(Integer, primary_key = True, autoincrement = True)
    
    # Foreign keys
    rule_id = Column(Integer, ForeignKey('rules.rule_id'), nullable = False)
    fund_id = Column(Integer, ForeignKey('funds.fund_id'), nullable = False)
    
    # Status
    active = Column(Boolean, nullable = False, default = True)
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    updated_at = Column(DateTime, nullable = False, default = get_eastern_time, 
                       onupdate = get_eastern_time)
    
    # Relationships
    rule = relationship("Rule", back_populates = "attachments")
    fund = relationship("Fund", back_populates = "rule_attachments")
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('rule_id', 'fund_id', name = 'uq_rule_fund'),
    )
    
    def __repr__(self) -> str:
        return f"<RuleAttachment(attachment_id={self.attachment_id}, rule_id={self.rule_id}, fund_id={self.fund_id}, active={self.active})>"
    
    def to_dict(self) -> dict:
        """Convert attachment to dictionary representation."""
        return {
            'attachment_id': self.attachment_id,
            'rule_id': self.rule_id,
            'fund_id': self.fund_id,
            'active': self.active,
            'rule_name': self.rule.rule_name if self.rule else None,
            'fund_name': self.fund.fund_name if self.fund else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
