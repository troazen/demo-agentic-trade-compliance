"""
Holdings service for managing fund positions and staging.
"""

from decimal import Decimal
from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import db, Fund, Security, Holding, HoldingStaging, Trade
from app.constants import TradeDirection

logger = logging.getLogger(__name__)


class HoldingsService:
    """Service class for holdings-related operations."""
    
    @staticmethod
    def get_holdings_for_fund(fund_id: int) -> List[Holding]:
        """
        Get all holdings for a fund.
        
        Args:
            fund_id: Fund ID to get holdings for
            
        Returns:
            List of Holding objects
        """
        logger.debug(f"Retrieving holdings for fund {fund_id}")
        
        holdings = Holding.query.filter_by(fund_id = fund_id).all()
        logger.debug(f"Retrieved {len(holdings)} holdings for fund {fund_id}")
        return holdings
    
    @staticmethod
    def get_holdings_with_market_values(fund_id: int) -> List[Dict[str, Any]]:
        """
        Get holdings for a fund with current market values.
        
        Args:
            fund_id: Fund ID to get holdings for
            
        Returns:
            List of holding dictionaries with market values
        """
        logger.debug(f"Retrieving holdings with market values for fund {fund_id}")
        
        holdings = HoldingsService.get_holdings_for_fund(fund_id)
        result = []
        
        for holding in holdings:
            holding_data = holding.to_dict()
            result.append(holding_data)
        
        logger.debug(f"Retrieved {len(result)} holdings with market values for fund {fund_id}")
        return result
    
    @staticmethod
    def update_holding_shares(fund_id: int, ticker: str, shares_delta: Decimal) -> bool:
        """
        Update holding shares (add or subtract).
        
        Args:
            fund_id: Fund ID
            ticker: Security ticker
            shares_delta: Change in shares (positive to add, negative to subtract)
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Updating holding {ticker} for fund {fund_id} by {shares_delta} shares")
        
        holding = Holding.query.filter_by(fund_id = fund_id, ticker = ticker).first()
        
        if not holding:
            logger.error(f"Holding {ticker} not found for fund {fund_id}")
            return False
        
        new_shares = holding.shares + shares_delta
        
        if new_shares < 0:
            logger.error(f"Cannot reduce shares below zero. Current: {holding.shares}, Delta: {shares_delta}")
            return False
        
        if new_shares == 0:
            # Remove holding when shares reach zero
            return HoldingsService.delete_holding(fund_id, ticker)
        
        try:
            holding.shares = new_shares
            db.session.commit()
            logger.info(f"Updated holding {ticker} for fund {fund_id}: {holding.shares - shares_delta} -> {new_shares}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update holding {ticker} for fund {fund_id}: {e}")
            return False
    
    @staticmethod
    def create_holding(fund_id: int, ticker: str, shares: Decimal) -> bool:
        """
        Create a new holding or add to existing holding.
        
        Args:
            fund_id: Fund ID
            ticker: Security ticker
            shares: Number of shares to add
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Creating/updating holding {ticker} for fund {fund_id} with {shares} shares")
        
        # Check if holding already exists
        existing_holding = Holding.query.filter_by(fund_id = fund_id, ticker = ticker).first()
        if existing_holding:
            # Add to existing holding
            logger.debug(f"Holding {ticker} already exists for fund {fund_id}, adding {shares} shares")
            return HoldingsService.update_holding_shares(fund_id, ticker, shares)
        
        # Verify security exists
        security = Security.query.get(ticker)
        if not security:
            logger.error(f"Security {ticker} not found")
            return False
        
        try:
            holding = Holding(
                fund_id = fund_id,
                ticker = ticker,
                shares = shares
            )
            db.session.add(holding)
            db.session.commit()
            
            logger.info(f"Created new holding {ticker} for fund {fund_id} with {shares} shares")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create holding {ticker} for fund {fund_id}: {e}")
            return False
    
    @staticmethod
    def delete_holding(fund_id: int, ticker: str) -> bool:
        """
        Delete a holding (when shares reach 0).
        
        Args:
            fund_id: Fund ID
            ticker: Security ticker
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Deleting holding {ticker} for fund {fund_id}")
        
        holding = Holding.query.filter_by(fund_id = fund_id, ticker = ticker).first()
        if not holding:
            logger.error(f"Holding {ticker} not found for fund {fund_id}")
            return False
        
        try:
            db.session.delete(holding)
            db.session.commit()
            logger.info(f"Deleted holding {ticker} for fund {fund_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to delete holding {ticker} for fund {fund_id}: {e}")
            return False
    
    @staticmethod
    def copy_holdings_to_staging(fund_id: int, trade_id: int) -> bool:
        """
        Copy fund holdings to staging table with trade_id.
        
        Args:
            fund_id: Fund ID to copy holdings from
            trade_id: Trade ID to associate with staging holdings
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Copying holdings for fund {fund_id} to staging for trade {trade_id}")
        
        # Clear any existing staging holdings for this trade
        HoldingStaging.query.filter_by(fund_id = fund_id, trade_id = trade_id).delete()
        
        # Get all holdings for the fund
        holdings = Holding.query.filter_by(fund_id = fund_id).all()
        
        try:
            for holding in holdings:
                staging_holding = HoldingStaging(
                    fund_id = fund_id,
                    ticker = holding.ticker,
                    trade_id = trade_id,
                    shares = holding.shares
                )
                db.session.add(staging_holding)
            
            db.session.commit()
            logger.info(f"Copied {len(holdings)} holdings to staging for fund {fund_id}, trade {trade_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to copy holdings to staging for fund {fund_id}, trade {trade_id}: {e}")
            return False
    
    @staticmethod
    def apply_trade_to_staging(trade: Trade) -> bool:
        """
        Apply trade logic to staging holdings.
        
        Args:
            trade: Trade object to apply
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Applying trade {trade.trade_id} to staging holdings")
        
        fund_id = trade.fund_id
        ticker = trade.ticker
        shares = trade.shares
        direction = trade.direction
        
        # Get or create staging holding
        staging_holding = HoldingStaging.query.filter_by(
            fund_id = fund_id,
            ticker = ticker,
            trade_id = trade.trade_id
        ).first()
        
        try:
            if direction == TradeDirection.BUY:
                if staging_holding:
                    # Add to existing holding
                    staging_holding.shares += shares
                    logger.debug(f"Added {shares} shares to existing staging holding {ticker}")
                else:
                    # Create new holding
                    staging_holding = HoldingStaging(
                        fund_id = fund_id,
                        ticker = ticker,
                        trade_id = trade.trade_id,
                        shares = shares
                    )
                    db.session.add(staging_holding)
                    logger.debug(f"Created new staging holding {ticker} with {shares} shares")
            
            elif direction == TradeDirection.SELL:
                if staging_holding:
                    # Subtract from existing holding
                    new_shares = staging_holding.shares - shares
                    if new_shares <= 0:
                        # Remove holding if shares reach zero or below
                        db.session.delete(staging_holding)
                        logger.debug(f"Removed staging holding {ticker} (shares would be {new_shares})")
                    else:
                        staging_holding.shares = new_shares
                        logger.debug(f"Reduced staging holding {ticker} to {new_shares} shares")
                else:
                    logger.error(f"Cannot sell {shares} shares of {ticker} - no existing holding")
                    return False
            
            db.session.commit()
            logger.info(f"Successfully applied trade {trade.trade_id} to staging holdings")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to apply trade {trade.trade_id} to staging holdings: {e}")
            return False
    
    @staticmethod
    def apply_staging_to_holdings(trade: Trade) -> bool:
        """
        Apply staged holdings changes to actual holdings table.
        
        Args:
            trade: Trade object that was processed
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Applying staging holdings to actual holdings for trade {trade.trade_id}")
        
        fund_id = trade.fund_id
        trade_id = trade.trade_id
        
        # Get all staging holdings for this trade
        staging_holdings = HoldingStaging.query.filter_by(
            fund_id = fund_id,
            trade_id = trade_id
        ).all()
        
        try:
            for staging_holding in staging_holdings:
                ticker = staging_holding.ticker
                shares = staging_holding.shares
                
                # Find existing holding
                existing_holding = Holding.query.filter_by(
                    fund_id = fund_id,
                    ticker = ticker
                ).first()
                
                if existing_holding:
                    # Update existing holding
                    existing_holding.shares = shares
                    logger.debug(f"Updated holding {ticker} to {shares} shares")
                else:
                    # Create new holding
                    new_holding = Holding(
                        fund_id = fund_id,
                        ticker = ticker,
                        shares = shares
                    )
                    db.session.add(new_holding)
                    logger.debug(f"Created new holding {ticker} with {shares} shares")
            
            # Clean up staging holdings
            HoldingStaging.query.filter_by(
                fund_id = fund_id,
                trade_id = trade_id
            ).delete()
            
            db.session.commit()
            logger.info(f"Successfully applied {len(staging_holdings)} staging holdings to actual holdings")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to apply staging holdings to actual holdings for trade {trade.trade_id}: {e}")
            return False
    
    @staticmethod
    def get_staging_holdings_for_trade(fund_id: int, trade_id: int) -> List[HoldingStaging]:
        """
        Get staging holdings for a specific trade.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID
            
        Returns:
            List of staging holding objects
        """
        logger.debug(f"Retrieving staging holdings for fund {fund_id}, trade {trade_id}")
        
        staging_holdings = HoldingStaging.query.filter_by(
            fund_id = fund_id,
            trade_id = trade_id
        ).all()
        
        logger.debug(f"Retrieved {len(staging_holdings)} staging holdings")
        return staging_holdings
