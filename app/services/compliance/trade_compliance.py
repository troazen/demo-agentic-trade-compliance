"""
Trade compliance service for checking trades against compliance rules.
"""

from typing import Dict, Any, List, Optional
import logging

from app.models import db, Trade, Rule, RuleAttachment
from app.constants import TradeStatus
from app.services.holdings_service import HoldingsService
from app.services.compliance.compliance_engine import ComplianceEngine

logger = logging.getLogger(__name__)


class TradeComplianceService:
    """Service class for trade compliance checking."""
    
    @staticmethod
    def check_trade_compliance(trade: Trade) -> Dict[str, Any]:
        """
        Check trade against all applicable compliance rules.
        
        Args:
            trade: Trade object to check
            
        Returns:
            Dictionary with compliance check results
        """
        logger.debug(f"Checking trade compliance for trade {trade.trade_id}")
        
        try:
            # Copy holdings to staging
            if not HoldingsService.copy_holdings_to_staging(trade.fund_id, trade.trade_id):
                logger.error(f"Failed to copy holdings to staging for trade {trade.trade_id}")
                return {
                    'success': False,
                    'error': 'Failed to copy holdings to staging'
                }
            
            # Apply trade to staging holdings
            if not HoldingsService.apply_trade_to_staging(trade):
                logger.error(f"Failed to apply trade to staging holdings for trade {trade.trade_id}")
                return {
                    'success': False,
                    'error': 'Failed to apply trade to staging holdings'
                }
            
            # Get active rules for this fund where trade_compliance_mode = True
            rules = TradeComplianceService._get_trade_compliance_rules(trade.fund_id)
            logger.debug(f"Found {len(rules)} trade compliance rules for fund {trade.fund_id}")
            
            # Execute all rules
            alerts = []
            for rule in rules:
                result = ComplianceEngine.execute_rule(trade.fund_id, trade.trade_id, rule)
                
                if result.get('alerted', False):
                    # Create alert record
                    alert = ComplianceEngine.create_alert_from_result(
                        trade.fund_id, trade.trade_id, result
                    )
                    if alert:
                        alerts.append({
                            'alert_id': alert.alert_id,
                            'rule_id': result['rule_id'],
                            'rule_name': result['rule_name'],
                            'alert_message': result['alert_message'],
                            'calculated_percentage': result.get('calculated_percentage'),
                            'selected_holdings': result.get('selected_holdings', [])
                        })
                        logger.warning(f"Trade compliance alert created: {result['rule_name']}")
                else:
                    logger.debug(f"Trade compliance rule passed: {result['rule_name']}")
            
            # Update trade status based on results
            if alerts:
                trade.update_status(TradeStatus.ALERT)
                db.session.commit()
                logger.info(f"Trade {trade.trade_id} has {len(alerts)} compliance alerts")
                return {
                    'success': True,
                    'trade_id': trade.trade_id,
                    'status': TradeStatus.ALERT.value,
                    'alerts': alerts,
                    'alerted': True
                }
            else:
                # No alerts - trade can proceed
                logger.info(f"Trade {trade.trade_id} passed all compliance checks")
                return {
                    'success': True,
                    'trade_id': trade.trade_id,
                    'status': TradeStatus.COMPLIANCE.value,
                    'alerts': [],
                    'alerted': False
                }
                
        except Exception as e:
            logger.error(f"Failed to check trade compliance for trade {trade.trade_id}: {e}")
            return {
                'success': False,
                'error': f'Compliance check failed: {str(e)}'
            }
    
    @staticmethod
    def _get_trade_compliance_rules(fund_id: int) -> List[Rule]:
        """
        Get active rules for fund where trade_compliance_mode = True.
        
        Args:
            fund_id: Fund ID
            
        Returns:
            List of Rule objects
        """
        logger.debug(f"Getting trade compliance rules for fund {fund_id}")
        
        rules = db.session.query(Rule).join(RuleAttachment).filter(
            RuleAttachment.fund_id == fund_id,
            RuleAttachment.active == True,
            Rule.trade_compliance_mode == True,
            Rule.active == True
        ).all()
        
        logger.debug(f"Found {len(rules)} trade compliance rules for fund {fund_id}")
        return rules
    
    @staticmethod
    def get_trade_alerts(trade_id: int) -> List[Dict[str, Any]]:
        """
        Get all alerts for a specific trade.
        
        Args:
            trade_id: Trade ID
            
        Returns:
            List of alert dictionaries
        """
        logger.debug(f"Getting alerts for trade {trade_id}")
        
        from app.models import Alert
        alerts = Alert.query.filter_by(trade_id = trade_id).all()
        
        result = []
        for alert in alerts:
            alert_data = alert.to_dict()
            result.append(alert_data)
        
        logger.debug(f"Retrieved {len(result)} alerts for trade {trade_id}")
        return result
    
    @staticmethod
    def override_trade_alerts(trade_id: int, override_reasons: Dict[int, str]) -> Dict[str, Any]:
        """
        Override trade alerts with reasons.
        
        Args:
            trade_id: Trade ID
            override_reasons: Dictionary mapping alert_id to override reason
            
        Returns:
            Dictionary with override result
        """
        logger.debug(f"Overriding alerts for trade {trade_id}")
        
        from app.models import Alert, Trade
        from app.constants import AlertStatus, TradeStatus
        
        trade = Trade.query.get(trade_id)
        if not trade:
            logger.error(f"Trade {trade_id} not found")
            return {'success': False, 'error': 'Trade not found'}
        
        if trade.status != TradeStatus.ALERT:
            logger.error(f"Trade {trade_id} is not in alert status")
            return {'success': False, 'error': 'Trade is not in alert status'}
        
        try:
            # Get all pending alerts for this trade
            alerts = Alert.query.filter_by(
                trade_id = trade_id,
                status = AlertStatus.PENDING
            ).all()
            
            if not alerts:
                logger.warning(f"No pending alerts found for trade {trade_id}")
                return {'success': False, 'error': 'No pending alerts found'}
            
            # Override alerts with provided reasons
            overridden_count = 0
            for alert in alerts:
                if alert.alert_id in override_reasons:
                    alert.override(override_reasons[alert.alert_id])
                    overridden_count += 1
                    logger.info(f"Overridden alert {alert.alert_id} for trade {trade_id}")
                else:
                    logger.warning(f"No override reason provided for alert {alert.alert_id}")
            
            if overridden_count == len(alerts):
                # All alerts overridden - update trade status
                trade.update_status(TradeStatus.COMPLIANCE)
                db.session.commit()
                logger.info(f"All alerts overridden for trade {trade_id}, status updated to compliance")
                return {
                    'success': True,
                    'trade_id': trade_id,
                    'status': TradeStatus.COMPLIANCE.value,
                    'overridden_count': overridden_count,
                    'message': 'All alerts overridden successfully'
                }
            else:
                # Some alerts not overridden
                db.session.commit()
                logger.warning(f"Only {overridden_count} of {len(alerts)} alerts overridden for trade {trade_id}")
                return {
                    'success': False,
                    'error': f'Only {overridden_count} of {len(alerts)} alerts overridden. All alerts must be overridden to proceed.',
                    'overridden_count': overridden_count,
                    'total_alerts': len(alerts)
                }
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to override alerts for trade {trade_id}: {e}")
            return {'success': False, 'error': f'Override failed: {str(e)}'}
    
    @staticmethod
    def cancel_trade_alerts(trade_id: int) -> Dict[str, Any]:
        """
        Cancel trade by cancelling all alerts.
        
        Args:
            trade_id: Trade ID
            
        Returns:
            Dictionary with cancellation result
        """
        logger.debug(f"Cancelling trade {trade_id}")
        
        from app.models import Alert, Trade
        from app.constants import AlertStatus, TradeStatus
        
        trade = Trade.query.get(trade_id)
        if not trade:
            logger.error(f"Trade {trade_id} not found")
            return {'success': False, 'error': 'Trade not found'}
        
        try:
            # Cancel all pending alerts
            alerts = Alert.query.filter_by(
                trade_id = trade_id,
                status = AlertStatus.PENDING
            ).all()
            
            for alert in alerts:
                alert.cancel()
                logger.info(f"Cancelled alert {alert.alert_id} for trade {trade_id}")
            
            # Update trade status to cancelled
            trade.update_status(TradeStatus.CANCELLED)
            db.session.commit()
            
            logger.info(f"Successfully cancelled trade {trade_id}")
            return {
                'success': True,
                'trade_id': trade_id,
                'status': TradeStatus.CANCELLED.value,
                'cancelled_alerts': len(alerts),
                'message': 'Trade cancelled successfully'
            }
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to cancel trade {trade_id}: {e}")
            return {'success': False, 'error': f'Cancellation failed: {str(e)}'}
