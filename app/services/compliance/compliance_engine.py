"""
Main compliance engine for rule execution and alert generation.
"""

from decimal import Decimal
from typing import Dict, Any, List, Optional
import logging

from app.models import db, Rule, Alert, Fund, Trade
from app.constants import DenominatorType, AlertIf, AlertStatus
from app.services.compliance.denominator_calculator import DenominatorCalculator
from app.services.compliance.numerator_calculator import NumeratorCalculator

logger = logging.getLogger(__name__)


class ComplianceEngine:
    """Main service class for compliance rule execution."""
    
    @staticmethod
    def execute_rule(fund_id: int, trade_id: int, rule: Rule) -> Dict[str, Any]:
        """
        Execute a single compliance rule.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (0 for portfolio compliance)
            rule: Rule object to execute
            
        Returns:
            Dictionary with rule execution result
        """
        logger.debug(f"Executing rule {rule.rule_id} ({rule.rule_name}) for fund {fund_id}, trade {trade_id}")
        
        try:
            # Get processed rule logic
            processed_logic = rule.get_processed_logic()
            
            # Handle prohibit rules
            if rule.is_prohibit_rule():
                return ComplianceEngine._execute_prohibit_rule(fund_id, trade_id, rule, processed_logic)
            
            # Handle For Each rules
            if rule.denominator == DenominatorType.SHARES_OUTSTANDING_FE:
                return ComplianceEngine._execute_fe_rule(fund_id, trade_id, rule, processed_logic)
            
            # Handle standard percentage rules
            return ComplianceEngine._execute_standard_rule(fund_id, trade_id, rule, processed_logic)
            
        except Exception as e:
            logger.error(f"Failed to execute rule {rule.rule_id}: {e}")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': False,
                'error': str(e)
            }
    
    @staticmethod
    def _execute_prohibit_rule(fund_id: int, trade_id: int, rule: Rule, logic: str) -> Dict[str, Any]:
        """
        Execute a prohibit rule.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID
            rule: Rule object
            logic: Processed rule logic
            
        Returns:
            Dictionary with rule execution result
        """
        logger.debug(f"Executing prohibit rule {rule.rule_id}")
        
        # Get holdings that match the logic
        selected_holdings = NumeratorCalculator.get_selected_holdings(fund_id, trade_id, logic)
        
        if selected_holdings:
            # Prohibit rule triggered - any matching holding causes alert
            logger.warning(f"Prohibit rule {rule.rule_id} triggered: {len(selected_holdings)} holdings found")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': True,
                'calculated_percentage': None,
                'selected_holdings': selected_holdings,
                'alert_message': rule.alert_message
            }
        else:
            logger.debug(f"Prohibit rule {rule.rule_id} not triggered")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': False,
                'calculated_percentage': None,
                'selected_holdings': [],
                'alert_message': rule.alert_message
            }
    
    @staticmethod
    def _execute_fe_rule(fund_id: int, trade_id: int, rule: Rule, logic: str) -> Dict[str, Any]:
        """
        Execute a For Each rule.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID
            rule: Rule object
            logic: Processed rule logic
            
        Returns:
            Dictionary with rule execution result
        """
        logger.debug(f"Executing FE rule {rule.rule_id}")
        
        # Calculate FE numerators
        fe_results = NumeratorCalculator.calculate_fe_numerators(fund_id, trade_id, logic)
        
        if not fe_results:
            logger.debug(f"FE rule {rule.rule_id} not triggered - no holdings match logic")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': False,
                'calculated_percentage': None,
                'selected_holdings': [],
                'alert_message': rule.alert_message
            }
        
        # Check each holding against alert level
        alerted_holdings = []
        for result in fe_results:
            percentage = result['percentage']
            alert_level = Decimal(str(rule.alert_level))
            
            should_alert = False
            if rule.alert_if == AlertIf.ABOVE and percentage >= alert_level:
                should_alert = True
            elif rule.alert_if == AlertIf.BELOW and percentage <= alert_level:
                should_alert = True
            
            if should_alert:
                alerted_holdings.append({
                    'ticker': result['ticker'],
                    'shares': int(result['shares']),
                    'shares_outstanding': result['shares_outstanding'],
                    'percentage': float(percentage)
                })
                logger.warning(f"FE rule {rule.rule_id} triggered for {result['ticker']}: {percentage}% {rule.alert_if.value} {alert_level}%")
        
        if alerted_holdings:
            logger.warning(f"FE rule {rule.rule_id} triggered: {len(alerted_holdings)} holdings exceed threshold")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': True,
                'calculated_percentage': None,  # FE rules don't have single percentage
                'selected_holdings': alerted_holdings,
                'alert_message': rule.alert_message
            }
        else:
            logger.debug(f"FE rule {rule.rule_id} not triggered")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': False,
                'calculated_percentage': None,
                'selected_holdings': [],
                'alert_message': rule.alert_message
            }
    
    @staticmethod
    def _execute_standard_rule(fund_id: int, trade_id: int, rule: Rule, logic: str) -> Dict[str, Any]:
        """
        Execute a standard percentage rule.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID
            rule: Rule object
            logic: Processed rule logic
            
        Returns:
            Dictionary with rule execution result
        """
        logger.debug(f"Executing standard rule {rule.rule_id}")
        
        # Calculate denominator
        denominator = DenominatorCalculator.calculate_denominator(fund_id, trade_id, rule.denominator)
        if denominator is None or denominator == 0:
            logger.error(f"Failed to calculate denominator for rule {rule.rule_id}")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': False,
                'error': 'Failed to calculate denominator'
            }
        
        # Calculate numerator
        numerator = NumeratorCalculator.calculate_numerator(fund_id, trade_id, logic, rule.denominator)
        if numerator is None:
            logger.error(f"Failed to calculate numerator for rule {rule.rule_id}")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': False,
                'error': 'Failed to calculate numerator'
            }
        
        # Calculate percentage
        percentage = (numerator / denominator) * Decimal('100')
        logger.debug(f"Rule {rule.rule_id} calculation: {numerator} / {denominator} = {percentage}%")
        
        # Check against alert level
        alert_level = Decimal(str(rule.alert_level))
        should_alert = False
        
        if rule.alert_if == AlertIf.ABOVE and percentage >= alert_level:
            should_alert = True
        elif rule.alert_if == AlertIf.BELOW and percentage <= alert_level:
            should_alert = True
        
        # Get selected holdings for alert details
        selected_holdings = NumeratorCalculator.get_selected_holdings(fund_id, trade_id, logic)
        
        if should_alert:
            logger.warning(f"Rule {rule.rule_id} triggered: {percentage}% {rule.alert_if.value} {alert_level}%")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': True,
                'calculated_percentage': float(percentage),
                'selected_holdings': selected_holdings,
                'alert_message': rule.alert_message
            }
        else:
            logger.debug(f"Rule {rule.rule_id} not triggered: {percentage}% not {rule.alert_if.value} {alert_level}%")
            return {
                'rule_id': rule.rule_id,
                'rule_name': rule.rule_name,
                'alerted': False,
                'calculated_percentage': float(percentage),
                'selected_holdings': selected_holdings,
                'alert_message': rule.alert_message
            }
    
    @staticmethod
    def create_alert_from_result(fund_id: int, trade_id: Optional[int], result: Dict[str, Any]) -> Optional[Alert]:
        """
        Create an alert record from rule execution result.
        
        Args:
            fund_id: Fund ID
            trade_id: Trade ID (None for portfolio compliance)
            result: Rule execution result
            
        Returns:
            Created Alert object or None if creation failed
        """
        if not result.get('alerted', False):
            return None
        
        logger.debug(f"Creating alert for rule {result['rule_id']}")
        
        try:
            # Serialize selected holdings
            import json
            holdings_json = json.dumps(result.get('selected_holdings', []))
            
            alert = Alert(
                rule_id = result['rule_id'],
                fund_id = fund_id,
                trade_id = trade_id,
                calculated_percentage = result.get('calculated_percentage'),
                holdings_triggered = holdings_json,
                status = AlertStatus.PENDING
            )
            
            db.session.add(alert)
            db.session.commit()
            
            logger.info(f"Created alert {alert.alert_id} for rule {result['rule_id']}")
            return alert
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create alert for rule {result['rule_id']}: {e}")
            return None
