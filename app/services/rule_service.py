"""
Rule service for managing compliance rules and fund attachments.
"""

from typing import List, Optional, Dict, Any
import logging

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func

from app.models import db, Rule, RuleAttachment, Fund
from app.constants import AlertIf, DenominatorType, BLOCKED_SQL_KEYWORDS
from app.config import get_eastern_time

logger = logging.getLogger(__name__)


class RuleService:
    """Service class for rule-related operations."""
    
    @staticmethod
    def get_all_rules(fund_id: Optional[int] = None, search_query: Optional[str] = None) -> List[Rule]:
        """
        Get all rules with optional filters.
        
        Args:
            fund_id: Optional fund ID to filter by attachment
            search_query: Optional search query for rule name
            
        Returns:
            List of Rule objects
        """
        logger.debug(f"Getting all rules with filters: fund_id={fund_id}, search_query={search_query}")
        
        query = Rule.query
        
        # Filter by fund attachment if provided
        if fund_id:
            query = query.join(RuleAttachment).filter(
                RuleAttachment.fund_id == fund_id,
                RuleAttachment.active == True
            )
        
        # Search by rule name if provided
        if search_query and search_query.strip():
            search_term = f"%{search_query.strip()}%"
            query = query.filter(Rule.rule_name.ilike(search_term))
        
        rules = query.order_by(Rule.created_at.desc()).all()
        
        logger.debug(f"Retrieved {len(rules)} rules")
        return rules
    
    @staticmethod
    def get_rule_by_id(rule_id: int) -> Optional[Rule]:
        """
        Get rule by ID.
        
        Args:
            rule_id: Rule ID to retrieve
            
        Returns:
            Rule object or None if not found
        """
        logger.debug(f"Retrieving rule {rule_id}")
        
        rule = Rule.query.get(rule_id)
        if rule:
            logger.debug(f"Found rule: {rule.rule_name}")
        else:
            logger.warning(f"Rule {rule_id} not found")
        
        return rule
    
    @staticmethod
    def get_rule_by_name(rule_name: str) -> Optional[Rule]:
        """
        Get rule by name.
        
        Args:
            rule_name: Rule name to retrieve
            
        Returns:
            Rule object or None if not found
        """
        logger.debug(f"Retrieving rule by name: {rule_name}")
        
        rule = Rule.query.filter_by(rule_name = rule_name).first()
        if rule:
            logger.debug(f"Found rule: {rule.rule_id} - {rule.rule_name}")
        else:
            logger.debug(f"Rule name '{rule_name}' not found")
        
        return rule
    
    @staticmethod
    def validate_rule_logic(logic: Optional[str]) -> Dict[str, Any]:
        """
        Validate rule SQL logic for safety and test against database.
        
        Args:
            logic: SQL logic string to validate
            
        Returns:
            Dictionary with 'valid' boolean and optional 'error' message
        """
        logger.debug("Validating rule logic")
        
        if not logic or not logic.strip():
            logger.debug("Logic is empty, will use default")
            return {'valid': True}
        
        logic_str = logic.strip()
        logic_upper = logic_str.upper()
        
        # Check for semicolons
        if ';' in logic_str:
            logger.error("Logic contains semicolon")
            return {'valid': False, 'error': 'SQL logic cannot contain semicolons'}
        
        # Check for blocked keywords
        for keyword in BLOCKED_SQL_KEYWORDS:
            if f' {keyword} ' in f' {logic_upper} ':
                logger.error(f"Logic contains blocked keyword: {keyword}")
                return {'valid': False, 'error': f'SQL logic cannot contain "{keyword}" keyword'}
        
        # Remove WHERE prefix if present
        if logic_upper.startswith('WHERE'):
            logic_str = logic_str[5:].strip()
            logger.debug("Removed WHERE prefix from logic")
        
        # Test the SQL against the database using a sample query structure
        # This matches the structure used in the compliance engine
        try:
            from sqlalchemy import text
            
            # Process logic to replace table names with aliases (as done in compliance engine)
            processed_logic = logic_str.replace('holdings.', 'h.').replace('issuers.', 'i.').replace('issuer.', 'i.').replace('securities.', 's.')
            
            # Create a test query that matches the compliance engine structure
            # Use a fund_id that might not exist (999999) to avoid affecting real data
            test_query = text(f"""
                SELECT COUNT(*) as test_count
                FROM holdings h
                INNER JOIN securities s ON h.ticker = s.ticker
                INNER JOIN issuers i ON s.issr_id = i.issr_id
                WHERE h.fund_id = 999999 AND ({processed_logic})
                LIMIT 1
            """)
            
            # Execute the test query
            result = db.session.execute(test_query)
            result.fetchone()  # Execute the query to check for SQL errors
            
            logger.debug("Rule logic validation passed - SQL syntax is valid")
            return {'valid': True}
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Rule logic validation failed: {error_msg}", exc_info = True)
            
            # Extract meaningful error message from SQLAlchemy exceptions
            if hasattr(e, 'orig'):
                # SQLAlchemy wraps the original exception
                original_error = str(e.orig) if e.orig else error_msg
                error_msg = original_error
            
            # Extract meaningful error message
            if "no such column" in error_msg.lower() or "no such table" in error_msg.lower():
                # SQLite error format
                return {'valid': False, 'error': f'SQL error: {error_msg}'}
            elif "column" in error_msg.lower() and "does not exist" in error_msg.lower():
                # PostgreSQL error format
                return {'valid': False, 'error': f'SQL error: {error_msg}'}
            elif "operationalerror" in error_msg.lower() or "programmingerror" in error_msg.lower():
                # SQLAlchemy operational/programming errors
                return {'valid': False, 'error': f'SQL error: {error_msg}'}
            else:
                # Generic error - include full error message
                return {'valid': False, 'error': f'SQL validation failed: {error_msg}'}
    
    @staticmethod
    def create_rule(rule_name: str, alert_message: str, denominator: str, 
                   logic: Optional[str] = None, alert_if: Optional[str] = None,
                   alert_level: Optional[float] = None, 
                   trade_compliance_mode: bool = True, 
                   portfolio_compliance_mode: bool = True) -> Dict[str, Any]:
        """
        Create a new compliance rule.
        
        Args:
            rule_name: Name of the rule
            alert_message: Alert message for violations
            denominator: Denominator type (enum value)
            logic: Optional SQL logic string
            alert_if: Optional alert condition ('above' or 'below')
            alert_level: Optional alert threshold level
            trade_compliance_mode: Whether rule runs on trades
            portfolio_compliance_mode: Whether rule runs on portfolio
            
        Returns:
            Dictionary with 'success' boolean, 'rule' object if successful, and 'error' message if failed
        """
        logger.debug(f"Creating new rule: {rule_name}")
        
        # Validate rule name is unique
        existing_rule = Rule.query.filter_by(rule_name = rule_name).first()
        if existing_rule:
            error_msg = f"Rule name '{rule_name}' already exists as rule {existing_rule.rule_id}"
            logger.error(error_msg)
            return {'success': False, 'rule': None, 'error': error_msg}
        
        # Validate logic
        logic_validation = RuleService.validate_rule_logic(logic)
        if not logic_validation['valid']:
            error_msg = f"Rule logic validation failed: {logic_validation.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return {'success': False, 'rule': None, 'error': error_msg}
        
        # Validate denominator
        try:
            denominator_enum = DenominatorType(denominator)
        except ValueError:
            error_msg = f"Invalid denominator type: {denominator}"
            logger.error(error_msg)
            return {'success': False, 'rule': None, 'error': error_msg}
        
        # Validate alert_if
        alert_if_enum = None
        if alert_if:
            try:
                alert_if_enum = AlertIf(alert_if)
            except ValueError:
                error_msg = f"Invalid alert_if value: {alert_if}"
                logger.error(error_msg)
                return {'success': False, 'rule': None, 'error': error_msg}
        
        # Validate alert_level (should not be None for non-prohibit rules)
        if denominator_enum != DenominatorType.PROHIBIT and alert_level is None:
            error_msg = "Alert level is required for non-prohibit rules"
            logger.error(error_msg)
            return {'success': False, 'rule': None, 'error': error_msg}
        
        try:
            rule = Rule(
                rule_name = rule_name,
                alert_message = alert_message,
                logic = logic,
                denominator = denominator_enum,
                alert_if = alert_if_enum,
                alert_level = alert_level,
                trade_compliance_mode = trade_compliance_mode,
                portfolio_compliance_mode = portfolio_compliance_mode,
                active = True
            )
            
            db.session.add(rule)
            db.session.commit()
            
            logger.info(f"Created rule {rule.rule_id}: {rule_name}")
            return {'success': True, 'rule': rule, 'error': None}
            
        except Exception as e:
            db.session.rollback()
            error_msg = f"Database error: {str(e)}"
            logger.error(f"Failed to create rule: {error_msg}", exc_info = True)
            return {'success': False, 'rule': None, 'error': error_msg}
    
    @staticmethod
    def update_rule(rule_id: int, rule_name: Optional[str] = None,
                   alert_message: Optional[str] = None, logic: Optional[str] = None,
                   denominator: Optional[str] = None, alert_if: Optional[str] = None,
                   alert_level: Optional[float] = None,
                   trade_compliance_mode: Optional[bool] = None,
                   portfolio_compliance_mode: Optional[bool] = None) -> Optional[Rule]:
        """
        Update an existing rule.
        
        Args:
            rule_id: Rule ID to update
            rule_name: Optional new rule name
            alert_message: Optional new alert message
            logic: Optional new logic
            denominator: Optional new denominator
            alert_if: Optional new alert_if
            alert_level: Optional new alert_level
            trade_compliance_mode: Optional new trade compliance mode
            portfolio_compliance_mode: Optional new portfolio compliance mode
            
        Returns:
            Updated Rule object or None if update failed
        """
        logger.debug(f"Updating rule {rule_id}")
        
        rule = Rule.query.get(rule_id)
        if not rule:
            logger.error(f"Rule {rule_id} not found")
            return None
        
        # Validate new rule name if provided
        if rule_name and rule_name != rule.rule_name:
            existing_rule = Rule.query.filter_by(rule_name = rule_name).first()
            if existing_rule:
                logger.error(f"Rule name '{rule_name}' already exists")
                return None
        
        # Validate logic if provided
        if logic is not None:
            logic_validation = RuleService.validate_rule_logic(logic)
            if not logic_validation['valid']:
                logger.error(f"Rule logic validation failed: {logic_validation['error']}")
                return None
        
        try:
            # Update fields if provided
            if rule_name:
                rule.rule_name = rule_name
            if alert_message:
                rule.alert_message = alert_message
            if logic is not None:
                rule.logic = logic
            if denominator:
                try:
                    rule.denominator = DenominatorType(denominator)
                except ValueError:
                    logger.error(f"Invalid denominator type: {denominator}")
                    return None
            if alert_if is not None:
                try:
                    rule.alert_if = AlertIf(alert_if) if alert_if else None
                except ValueError:
                    logger.error(f"Invalid alert_if value: {alert_if}")
                    return None
            if alert_level is not None:
                rule.alert_level = alert_level
            if trade_compliance_mode is not None:
                rule.trade_compliance_mode = trade_compliance_mode
            if portfolio_compliance_mode is not None:
                rule.portfolio_compliance_mode = portfolio_compliance_mode
            
            rule.updated_at = get_eastern_time()
            
            db.session.commit()
            
            logger.info(f"Updated rule {rule_id}")
            return rule
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update rule {rule_id}: {e}")
            return None
    
    @staticmethod
    def activate_rule(rule_id: int) -> bool:
        """
        Activate a rule.
        
        Args:
            rule_id: Rule ID to activate
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Activating rule {rule_id}")
        
        rule = Rule.query.get(rule_id)
        if not rule:
            logger.error(f"Rule {rule_id} not found")
            return False
        
        try:
            rule.active = True
            rule.updated_at = get_eastern_time()
            db.session.commit()
            
            logger.info(f"Activated rule {rule_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to activate rule {rule_id}: {e}")
            return False
    
    @staticmethod
    def deactivate_rule(rule_id: int) -> bool:
        """
        Deactivate a rule.
        
        Args:
            rule_id: Rule ID to deactivate
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Deactivating rule {rule_id}")
        
        rule = Rule.query.get(rule_id)
        if not rule:
            logger.error(f"Rule {rule_id} not found")
            return False
        
        try:
            rule.active = False
            rule.updated_at = get_eastern_time()
            db.session.commit()
            
            logger.info(f"Deactivated rule {rule_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to deactivate rule {rule_id}: {e}")
            return False
    
    @staticmethod
    def attach_rule_to_fund(rule_id: int, fund_id: int) -> bool:
        """
        Attach a rule to a fund.
        
        Args:
            rule_id: Rule ID
            fund_id: Fund ID
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Attaching rule {rule_id} to fund {fund_id}")
        
        # Verify rule exists
        rule = Rule.query.get(rule_id)
        if not rule:
            logger.error(f"Rule {rule_id} not found")
            return False
        
        # Verify fund exists
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return False
        
        # Check if attachment already exists
        existing_attachment = RuleAttachment.query.filter_by(
            rule_id = rule_id,
            fund_id = fund_id
        ).first()
        
        if existing_attachment:
            # Reactivate if inactive
            if not existing_attachment.active:
                existing_attachment.active = True
                existing_attachment.updated_at = get_eastern_time()
                try:
                    db.session.commit()
                    logger.info(f"Reactivated attachment for rule {rule_id} and fund {fund_id}")
                    return True
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Failed to reactivate attachment: {e}")
                    return False
            else:
                logger.debug(f"Rule {rule_id} is already attached to fund {fund_id}")
                return True
        
        try:
            attachment = RuleAttachment(
                rule_id = rule_id,
                fund_id = fund_id,
                active = True
            )
            db.session.add(attachment)
            db.session.commit()
            
            logger.info(f"Attached rule {rule_id} to fund {fund_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to attach rule {rule_id} to fund {fund_id}: {e}")
            return False
    
    @staticmethod
    def detach_rule_from_fund(rule_id: int, fund_id: int) -> bool:
        """
        Detach a rule from a fund.
        
        Args:
            rule_id: Rule ID
            fund_id: Fund ID
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Detaching rule {rule_id} from fund {fund_id}")
        
        attachment = RuleAttachment.query.filter_by(
            rule_id = rule_id,
            fund_id = fund_id
        ).first()
        
        if not attachment:
            logger.warning(f"No attachment found for rule {rule_id} and fund {fund_id}")
            return False
        
        try:
            # Deactivate rather than delete
            attachment.active = False
            attachment.updated_at = get_eastern_time()
            db.session.commit()
            
            logger.info(f"Detached rule {rule_id} from fund {fund_id}")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to detach rule {rule_id} from fund {fund_id}: {e}")
            return False
    
    @staticmethod
    def get_rule_attachments(rule_id: int) -> List[RuleAttachment]:
        """
        Get all fund attachments for a rule.
        
        Args:
            rule_id: Rule ID
            
        Returns:
            List of RuleAttachment objects
        """
        logger.debug(f"Getting attachments for rule {rule_id}")
        
        attachments = RuleAttachment.query.options(joinedload(RuleAttachment.fund)).filter_by(rule_id = rule_id).all()
        logger.debug(f"Found {len(attachments)} attachments for rule {rule_id}")
        return attachments
    
    @staticmethod
    def get_rule_with_attachments(rule_id: int) -> Optional[Dict[str, Any]]:
        """
        Get rule with its fund attachments.
        
        Args:
            rule_id: Rule ID
            
        Returns:
            Dictionary with rule details and attachments, or None if not found
        """
        logger.debug(f"Getting rule {rule_id} with attachments")
        
        rule = Rule.query.get(rule_id)
        if not rule:
            return None
        
        rule_data = rule.to_dict()
        
        # Add attached funds (only active attachments)
        attachments = RuleService.get_rule_attachments(rule_id)
        attached_funds = []
        for att in attachments:
            if att.active and att.fund:
                attached_funds.append({
                    'fund_id': att.fund_id,
                    'fund_name': att.fund.fund_name
                })
        rule_data['attached_funds'] = attached_funds
        
        logger.debug(f"Retrieved rule {rule_id} with {len(attached_funds)} attached funds")
        return rule_data
    
    @staticmethod
    def test_rule(rule_id: int, fund_id: int, test_trade: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Test a rule against a fund without persisting any data.
        
        Args:
            rule_id: Rule ID to test
            fund_id: Fund ID to test against
            test_trade: Optional test trade details (ticker, direction, shares)
            
        Returns:
            Dictionary with test results
        """
        logger.debug(f"Testing rule {rule_id} against fund {fund_id}")
        
        # Verify rule exists
        rule = Rule.query.get(rule_id)
        if not rule:
            logger.error(f"Rule {rule_id} not found")
            return {
                'success': False,
                'error': 'Rule not found'
            }
        
        # Verify fund exists
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return {
                'success': False,
                'error': 'Fund not found'
            }
        
        try:
            from app.services.compliance.compliance_engine import ComplianceEngine
            from app.services.holdings_service import HoldingsService
            from decimal import Decimal
            
            # Determine test type
            test_type = 'portfolio'
            test_trade_details = None
            
            # If test_trade provided, simulate it
            if test_trade:
                test_type = 'trade'
                ticker = test_trade.get('ticker')
                direction = test_trade.get('direction')
                shares = test_trade.get('shares')
                
                # Validate test trade
                if not all([ticker, direction, shares]):
                    return {
                        'success': False,
                        'error': 'test_trade requires ticker, direction, and shares'
                    }
                
                # Copy holdings to staging
                test_trade_id = 999999
                HoldingsService.copy_holdings_to_staging(fund_id, test_trade_id)
                
                # Create a simple dict to represent the trade (don't create actual Trade object)
                from app.constants import TradeDirection
                from app.models import HoldingStaging
                
                # Manually apply the test trade to staging without creating a Trade object
                direction_enum = TradeDirection(direction.upper())
                
                if direction_enum == TradeDirection.BUY:
                    # Add shares to existing holding or create new
                    staging_holding = HoldingStaging.query.filter_by(
                        fund_id = fund_id,
                        ticker = ticker,
                        trade_id = test_trade_id
                    ).first()
                    
                    if staging_holding:
                        staging_holding.shares += Decimal(str(shares))
                    else:
                        staging_holding = HoldingStaging(
                            fund_id = fund_id,
                            ticker = ticker,
                            trade_id = test_trade_id,
                            shares = Decimal(str(shares))
                        )
                        db.session.add(staging_holding)
                    db.session.commit()
                elif direction_enum == TradeDirection.SELL:
                    # Remove shares from existing holding
                    staging_holding = HoldingStaging.query.filter_by(
                        fund_id = fund_id,
                        ticker = ticker,
                        trade_id = test_trade_id
                    ).first()
                    
                    if staging_holding:
                        new_shares = staging_holding.shares - Decimal(str(shares))
                        if new_shares <= 0:
                            db.session.delete(staging_holding)
                        else:
                            staging_holding.shares = new_shares
                        db.session.commit()
                
                test_trade_details = {
                    'ticker': ticker,
                    'direction': direction,
                    'shares': int(shares)
                }
                trade_id = test_trade_id
            else:
                # Test against current holdings (portfolio mode)
                HoldingsService.copy_holdings_to_staging(fund_id, 0)
                trade_id = 0
            
            # Execute the rule
            result = ComplianceEngine.execute_rule(fund_id, trade_id, rule)
            
            # Clean up staging
            if test_type == 'trade':
                # Clean up the test trade staging data
                from app.models import HoldingStaging
                HoldingStaging.query.filter_by(
                    fund_id = fund_id,
                    trade_id = 999999
                ).delete()
                try:
                    db.session.commit()
                except Exception as e:
                    logger.warning(f"Failed to cleanup test staging data: {e}")
                    db.session.rollback()
            
            # Format response
            response = {
                'success': True,
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'fund_id': fund_id,
                'test_type': test_type,
                'would_alert': result.get('alerted', False),
                'calculated_percentage': float(result.get('calculated_percentage')) if result.get('calculated_percentage') else None,
                'alert_level': float(rule.alert_level) if rule.alert_level else None,
                'alert_if': rule.alert_if.value if rule.alert_if else None,
                'alert_message': rule.alert_message,
                'holdings_triggered': result.get('selected_holdings', [])
            }
            
            if test_trade_details:
                response['test_trade_details'] = test_trade_details
            
            logger.info(f"Rule {rule_id} test completed: would_alert={response['would_alert']}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to test rule {rule_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
