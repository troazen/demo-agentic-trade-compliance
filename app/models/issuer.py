"""
Issuer model representing companies that issue securities.
"""

from datetime import datetime
from typing import List, Optional
import logging

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.models import db
from app.config import get_eastern_time

logger = logging.getLogger(__name__)


class Issuer(db.Model):
    """
    Issuer model representing companies that issue securities.
    
    Each issuer can have multiple securities (different share classes, subsidiaries, etc.).
    """
    
    __tablename__ = 'issuers'
    
    # Primary key
    issr_id = Column(Integer, primary_key = True, autoincrement = True)
    
    # Issuer details
    name = Column(String(255), nullable = False)
    
    # GICS classification
    gics_sector = Column(String(100), nullable = True)
    gics_industry_grp = Column(String(100), nullable = True)
    gics_industry = Column(String(100), nullable = True)
    gics_sub_industry = Column(String(100), nullable = True)
    
    # Country information
    country_domicile = Column(String(100), nullable = True)
    country_incorporation = Column(String(100), nullable = True)
    country_domicile_code = Column(String(3), nullable = True)  # Three letter country code
    country_incorporation_code = Column(String(3), nullable = True)  # Three letter country code
    
    # Metadata
    created_at = Column(DateTime, nullable = False, default = get_eastern_time)
    updated_at = Column(DateTime, nullable = False, default = get_eastern_time, 
                       onupdate = get_eastern_time)
    
    # Relationships
    securities = relationship("Security", back_populates = "issuer", cascade = "all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Issuer(issr_id={self.issr_id}, name='{self.name}')>"
    
    def to_dict(self) -> dict:
        """Convert issuer to dictionary representation."""
        return {
            'issr_id': self.issr_id,
            'name': self.name,
            'gics_sector': self.gics_sector,
            'gics_industry_grp': self.gics_industry_grp,
            'gics_industry': self.gics_industry,
            'gics_sub_industry': self.gics_sub_industry,
            'country_domicile': self.country_domicile,
            'country_incorporation': self.country_incorporation,
            'country_domicile_code': self.country_domicile_code,
            'country_incorporation_code': self.country_incorporation_code,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
