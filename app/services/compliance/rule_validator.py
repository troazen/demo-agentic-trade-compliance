"""
Rule validator for SQL logic validation and testing.
"""

import sqlparse
import logging
from typing import Dict, Any, Optional
from sqlalchemy import text

from app.models import db
from app.constants import BLOCKED_SQL_KEYWORDS, DEFAULT_RULE_LOGIC

logger = logging.getLogger(__name__)


class RuleValidator:
    """Service class for rule SQL logic validation."""
    
    @staticmethod
    def validate_rule_logic(logic: str) -> Dict[str, Any]:
        """
        Validate rule SQL logic.
        
        Args:
            logic: SQL logic string to validate
            
        Returns:
            Dictionary with validation result
        """
        logger.debug(f"Validating rule logic: {logic}")
        
        # Handle empty or null logic
        if not logic or not logic.strip():
            logger.debug("Empty logic provided, using default")
            return {
                'valid': True,
                'processed_logic': DEFAULT_RULE_LOGIC,
                'message': 'Empty logic converted to default (1=1)'
            }
        
        processed_logic = logic.strip()
        
        # Remove WHERE prefix if present
        if processed_logic.upper().startswith('WHERE'):
            processed_logic = processed_logic[5:].strip()
            logger.debug("Removed WHERE prefix from logic")
        
        # Check for semicolons
        if ';' in processed_logic:
            logger.error("Semicolon found in rule logic")
            return {
                'valid': False,
                'error': 'Semicolons are not allowed in rule logic'
            }
        
        # Check for blocked SQL keywords
        logic_upper = processed_logic.upper()
        for keyword in BLOCKED_SQL_KEYWORDS:
            # Check for keyword with word boundaries
            if f' {keyword} ' in logic_upper or logic_upper.startswith(f'{keyword} ') or logic_upper.endswith(f' {keyword}'):
                logger.error(f"Blocked SQL keyword found: {keyword}")
                return {
                    'valid': False,
                    'error': f'SQL keyword "{keyword}" is not allowed in rule logic'
                }
        
        # Parse SQL to check for syntax errors
        try:
            parsed = sqlparse.parse(processed_logic)
            if not parsed:
                logger.error("Empty SQL after parsing")
                return {
                    'valid': False,
                    'error': 'Invalid SQL syntax: empty statement'
                }
        except Exception as e:
            logger.error(f"SQL parsing error: {e}")
            return {
                'valid': False,
                'error': f'Invalid SQL syntax: {str(e)}'
            }
        
        # Test execution with a simple query
        test_result = RuleValidator._test_sql_execution(processed_logic)
        if not test_result['valid']:
            return test_result
        
        logger.debug(f"Rule logic validation passed: {processed_logic}")
        return {
            'valid': True,
            'processed_logic': processed_logic,
            'message': 'Rule logic is valid'
        }
    
    @staticmethod
    def _test_sql_execution(logic: str) -> Dict[str, Any]:
        """
        Test SQL execution with a simple query.
        
        Args:
            logic: SQL logic to test
            
        Returns:
            Dictionary with test result
        """
        logger.debug(f"Testing SQL execution for logic: {logic}")
        
        # Create a test query that would be used in compliance checking
        test_query = f"""
        SELECT 1 as test_result
        FROM (
            SELECT 'TEST' as ticker, 1 as fund_id, 0 as trade_id, 100 as shares
        ) holdings
        INNER JOIN (
            SELECT 'TEST' as ticker, 'Test Security' as name, 1 as issr_id
        ) securities ON securities.ticker = holdings.ticker
        INNER JOIN (
            SELECT 'TEST' as ticker, 100.00 as price
        ) sp ON securities.ticker = sp.ticker
        INNER JOIN (
            SELECT 1 as issr_id, 'Test Issuer' as name, 'Technology' as gics_sector
        ) issuers ON issuers.issr_id = securities.issr_id
        WHERE {logic}
        """
        
        try:
            # Execute the test query
            result = db.session.execute(text(test_query)).fetchone()
            if result is None:
                logger.warning("Test query returned no results")
                return {
                    'valid': True,
                    'message': 'Test query executed successfully (no results)'
                }
            else:
                logger.debug("Test query executed successfully")
                return {
                    'valid': True,
                    'message': 'Test query executed successfully'
                }
        except Exception as e:
            logger.error(f"Test query execution failed: {e}")
            return {
                'valid': False,
                'error': f'SQL execution test failed: {str(e)}'
            }
    
    @staticmethod
    def validate_rule_data(rule_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate complete rule data.
        
        Args:
            rule_data: Dictionary containing rule data
            
        Returns:
            Dictionary with validation result
        """
        logger.debug("Validating complete rule data")
        
        errors = []
        
        # Validate required fields
        required_fields = ['rule_name', 'alert_message', 'denominator']
        for field in required_fields:
            if field not in rule_data or not rule_data[field]:
                errors.append(f"Required field '{field}' is missing or empty")
        
        # Validate rule name uniqueness (if not updating existing rule)
        if 'rule_id' not in rule_data or not rule_data['rule_id']:
            from app.models import Rule
            existing_rule = Rule.query.filter_by(rule_name = rule_data.get('rule_name', '')).first()
            if existing_rule:
                errors.append(f"Rule name '{rule_data['rule_name']}' already exists")
        
        # Validate denominator
        if 'denominator' in rule_data:
            from app.constants import DenominatorType
            try:
                DenominatorType(rule_data['denominator'])
            except ValueError:
                errors.append(f"Invalid denominator: {rule_data['denominator']}")
        
        # Validate alert_if and alert_level for non-prohibit rules
        if rule_data.get('denominator') != 'prohibit':
            if 'alert_if' in rule_data and rule_data['alert_if']:
                from app.constants import AlertIf
                try:
                    AlertIf(rule_data['alert_if'])
                except ValueError:
                    errors.append(f"Invalid alert_if: {rule_data['alert_if']}")
            
            if 'alert_level' in rule_data and rule_data['alert_level'] is not None:
                try:
                    alert_level = float(rule_data['alert_level'])
                    if alert_level < 0:
                        errors.append("Alert level must be non-negative")
                except (ValueError, TypeError):
                    errors.append(f"Invalid alert_level: {rule_data['alert_level']}")
        
        # Validate logic if provided
        if 'logic' in rule_data:
            logic_result = RuleValidator.validate_rule_logic(rule_data['logic'])
            if not logic_result['valid']:
                errors.append(f"Logic validation failed: {logic_result['error']}")
        
        if errors:
            logger.error(f"Rule validation failed: {errors}")
            return {
                'valid': False,
                'errors': errors
            }
        
        logger.debug("Rule data validation passed")
        return {
            'valid': True,
            'message': 'Rule data is valid'
        }
