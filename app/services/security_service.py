"""
Security service for managing securities and prices.
"""

from decimal import Decimal
from datetime import date
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.models import db, Security, SecuritiesPrice, Issuer

logger = logging.getLogger(__name__)


class SecurityService:
    """Service class for security-related operations."""
    
    @staticmethod
    def get_security_by_ticker(ticker: str) -> Optional[Security]:
        """
        Get security by ticker.
        
        Args:
            ticker: Security ticker symbol
            
        Returns:
            Security object or None if not found
        """
        logger.debug(f"Retrieving security {ticker}")
        
        security = Security.query.get(ticker)
        if security:
            logger.debug(f"Found security: {security.name}")
        else:
            logger.warning(f"Security {ticker} not found")
        
        return security
    
    @staticmethod
    def get_all_securities() -> List[Security]:
        """
        Get all securities.
        
        Returns:
            List of Security objects
        """
        logger.debug("Retrieving all securities")
        
        securities = Security.query.all()
        logger.debug(f"Retrieved {len(securities)} securities")
        return securities
    
    @staticmethod
    def get_securities_with_prices() -> List[Dict[str, Any]]:
        """
        Get all securities with current prices.
        
        Returns:
            List of security dictionaries with current prices
        """
        logger.debug("Retrieving all securities with current prices")
        
        securities = Security.query.all()
        result = []
        
        for security in securities:
            security_data = security.to_dict()
            current_price = security.get_latest_price()
            security_data['current_price'] = float(current_price) if current_price else None
            result.append(security_data)
        
        logger.debug(f"Retrieved {len(result)} securities with prices")
        return result
    
    @staticmethod
    def search_securities(query: str) -> List[Security]:
        """
        Search securities by ticker or issuer name (case insensitive contains).
        
        Args:
            query: Search query string
            
        Returns:
            List of matching Security objects
        """
        logger.debug(f"Searching securities with query: {query}")
        
        if not query or not query.strip():
            logger.warning("Empty search query provided")
            return []
        
        search_term = f"%{query.strip()}%"
        
        securities = Security.query.join(Issuer).filter(
            or_(
                Security.ticker.ilike(search_term),
                Security.name.ilike(search_term),
                Issuer.name.ilike(search_term)
            )
        ).all()
        
        logger.debug(f"Found {len(securities)} securities matching '{query}'")
        return securities
    
    @staticmethod
    def get_current_price(ticker: str) -> Optional[Decimal]:
        """
        Get current price for a security (latest date in securities_price).
        
        Args:
            ticker: Security ticker symbol
            
        Returns:
            Current price as Decimal, or None if not found
        """
        logger.debug(f"Getting current price for {ticker}")
        
        security = Security.query.get(ticker)
        if not security:
            logger.error(f"Security {ticker} not found")
            return None
        
        current_price = security.get_latest_price()
        if current_price:
            logger.debug(f"Current price for {ticker}: {current_price}")
        else:
            logger.warning(f"No current price found for {ticker}")
        
        return current_price
    
    @staticmethod
    def get_price_for_date(ticker: str, target_date: date) -> Optional[Decimal]:
        """
        Get price for a security on a specific date.
        
        Args:
            ticker: Security ticker symbol
            target_date: Date to get price for
            
        Returns:
            Price as Decimal, or None if not found
        """
        logger.debug(f"Getting price for {ticker} on {target_date}")
        
        security = Security.query.get(ticker)
        if not security:
            logger.error(f"Security {ticker} not found")
            return None
        
        price = security.get_price_for_date(target_date)
        if price:
            logger.debug(f"Price for {ticker} on {target_date}: {price}")
        else:
            logger.warning(f"No price found for {ticker} on {target_date}")
        
        return price
    
    @staticmethod
    def validate_security_exists(ticker: str) -> bool:
        """
        Validate that a security exists.
        
        Args:
            ticker: Security ticker symbol to validate
            
        Returns:
            True if security exists, False otherwise
        """
        logger.debug(f"Validating security exists: {ticker}")
        
        security = Security.query.get(ticker)
        exists = security is not None
        
        if exists:
            logger.debug(f"Security {ticker} exists")
        else:
            logger.warning(f"Security {ticker} does not exist")
        
        return exists
    
    @staticmethod
    def create_security(ticker: str, name: str, issr_id: int, 
                       security_type: str = 'Equity Stock',
                       shares_outstanding: Optional[int] = None,
                       market_cap: Optional[int] = None) -> Optional[Security]:
        """
        Create a new security.
        
        Args:
            ticker: Security ticker symbol
            name: Security name
            issr_id: Issuer ID
            security_type: Type of security
            shares_outstanding: Number of shares outstanding
            market_cap: Market capitalization
            
        Returns:
            Created Security object or None if creation failed
        """
        logger.debug(f"Creating security {ticker}: {name}")
        
        # Check if security already exists
        existing_security = Security.query.get(ticker)
        if existing_security:
            logger.error(f"Security {ticker} already exists")
            return None
        
        # Verify issuer exists
        issuer = Issuer.query.get(issr_id)
        if not issuer:
            logger.error(f"Issuer {issr_id} not found")
            return None
        
        try:
            security = Security(
                ticker = ticker,
                name = name,
                issr_id = issr_id,
                type = security_type,
                shares_outstanding = shares_outstanding,
                market_cap = market_cap
            )
            db.session.add(security)
            db.session.commit()
            
            logger.info(f"Created security {ticker}: {name}")
            return security
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create security {ticker}: {e}")
            return None
    
    @staticmethod
    def add_price(ticker: str, price_date: date, price: Decimal) -> bool:
        """
        Add a price record for a security.
        
        Args:
            ticker: Security ticker symbol
            price_date: Date for the price
            price: Price value
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Adding price for {ticker} on {price_date}: {price}")
        
        # Verify security exists
        security = Security.query.get(ticker)
        if not security:
            logger.error(f"Security {ticker} not found")
            return False
        
        # Check if price already exists for this date
        existing_price = SecuritiesPrice.query.filter_by(
            ticker = ticker,
            price_date = price_date
        ).first()
        
        if existing_price:
            logger.warning(f"Price for {ticker} on {price_date} already exists, updating")
            existing_price.price = price
        else:
            price_record = SecuritiesPrice(
                ticker = ticker,
                price_date = price_date,
                price = price
            )
            db.session.add(price_record)
        
        try:
            db.session.commit()
            logger.info(f"Added/updated price for {ticker} on {price_date}: {price}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to add price for {ticker}: {e}")
            return False
    
    @staticmethod
    def get_latest_prices_for_all() -> Dict[str, Decimal]:
        """
        Get latest prices for all securities.
        
        Returns:
            Dictionary mapping ticker to latest price
        """
        logger.debug("Getting latest prices for all securities")
        
        latest_prices = SecuritiesPrice.get_all_latest_prices()
        logger.debug(f"Retrieved latest prices for {len(latest_prices)} securities")
        return latest_prices
