"""
Portfolio compliance service for batch compliance checking.
"""

from typing import Dict, Any, List, Optional
import logging

from app.models import db, Rule, RuleAttachment, Fund
from app.services.holdings_service import HoldingsService
from app.services.compliance.compliance_engine import ComplianceEngine

logger = logging.getLogger(__name__)


class PortfolioComplianceService:
    """Service class for portfolio compliance checking."""
    
    @staticmethod
    def run_portfolio_compliance(fund_id: int) -> Dict[str, Any]:
        """
        Run portfolio compliance check for a fund.
        
        Args:
            fund_id: Fund ID to check
            
        Returns:
            Dictionary with compliance check results
        """
        logger.debug(f"Running portfolio compliance for fund {fund_id}")
        
        # Verify fund exists
        fund = Fund.query.get(fund_id)
        if not fund:
            logger.error(f"Fund {fund_id} not found")
            return {
                'success': False,
                'error': 'Fund not found'
            }
        
        try:
            # Copy holdings to staging with trade_id = 0 (no trade)
            if not HoldingsService.copy_holdings_to_staging(fund_id, 0):
                logger.error(f"Failed to copy holdings to staging for fund {fund_id}")
                return {
                    'success': False,
                    'error': 'Failed to copy holdings to staging'
                }
            
            # Get active rules for this fund where portfolio_compliance_mode = True
            rules = PortfolioComplianceService._get_portfolio_compliance_rules(fund_id)
            logger.debug(f"Found {len(rules)} portfolio compliance rules for fund {fund_id}")
            
            if not rules:
                logger.info(f"No portfolio compliance rules found for fund {fund_id}")
                return {
                    'success': True,
                    'fund_id': fund_id,
                    'alerts': [],
                    'alerted': False,
                    'message': 'No portfolio compliance rules configured'
                }
            
            # Execute all rules
            alerts = []
            for rule in rules:
                result = ComplianceEngine.execute_rule(fund_id, 0, rule)  # trade_id = 0 for portfolio
                
                if result.get('alerted', False):
                    # Create alert record
                    alert = ComplianceEngine.create_alert_from_result(
                        fund_id, None, result  # trade_id = None for portfolio compliance
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
                        logger.warning(f"Portfolio compliance alert created: {result['rule_name']}")
                else:
                    logger.debug(f"Portfolio compliance rule passed: {result['rule_name']}")
            
            # Clean up staging holdings
            HoldingsService.get_staging_holdings_for_trade(fund_id, 0)
            # Note: We don't need to clean up staging for portfolio compliance as it's just a copy
            
            logger.info(f"Portfolio compliance check completed for fund {fund_id}: {len(alerts)} alerts")
            return {
                'success': True,
                'fund_id': fund_id,
                'alerts': alerts,
                'alerted': len(alerts) > 0,
                'message': f'Portfolio compliance check completed with {len(alerts)} alerts'
            }
            
        except Exception as e:
            logger.error(f"Failed to run portfolio compliance for fund {fund_id}: {e}")
            return {
                'success': False,
                'error': f'Portfolio compliance check failed: {str(e)}'
            }
    
    @staticmethod
    def _get_portfolio_compliance_rules(fund_id: int) -> List[Rule]:
        """
        Get active rules for fund where portfolio_compliance_mode = True.
        
        Args:
            fund_id: Fund ID
            
        Returns:
            List of Rule objects
        """
        logger.debug(f"Getting portfolio compliance rules for fund {fund_id}")
        
        rules = db.session.query(Rule).join(RuleAttachment).filter(
            RuleAttachment.fund_id == fund_id,
            RuleAttachment.active == True,
            Rule.portfolio_compliance_mode == True,
            Rule.active == True
        ).all()
        
        logger.debug(f"Found {len(rules)} portfolio compliance rules for fund {fund_id}")
        return rules
    
    @staticmethod
    def get_fund_alerts(fund_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all alerts for a specific fund.
        
        Args:
            fund_id: Fund ID
            limit: Optional limit on number of alerts to return
            
        Returns:
            List of alert dictionaries
        """
        logger.debug(f"Getting alerts for fund {fund_id}")
        
        from app.models import Alert
        query = Alert.query.filter_by(fund_id = fund_id).order_by(Alert.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        alerts = query.all()
        
        result = []
        for alert in alerts:
            alert_data = alert.to_dict()
            result.append(alert_data)
        
        logger.debug(f"Retrieved {len(result)} alerts for fund {fund_id}")
        return result
    
    @staticmethod
    def get_recent_portfolio_alerts(fund_id: int, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get recent portfolio compliance alerts for a fund.
        
        Args:
            fund_id: Fund ID
            hours: Number of hours to look back
            
        Returns:
            List of recent alert dictionaries
        """
        logger.debug(f"Getting recent portfolio alerts for fund {fund_id} (last {hours} hours)")
        
        from app.models import Alert
        from datetime import datetime, timedelta
        from app.config import get_eastern_time
        
        cutoff_time = get_eastern_time() - timedelta(hours = hours)
        
        alerts = Alert.query.filter(
            Alert.fund_id == fund_id,
            Alert.trade_id.is_(None),  # Portfolio compliance alerts have no trade_id
            Alert.created_at >= cutoff_time
        ).order_by(Alert.created_at.desc()).all()
        
        result = []
        for alert in alerts:
            alert_data = alert.to_dict()
            result.append(alert_data)
        
        logger.debug(f"Retrieved {len(result)} recent portfolio alerts for fund {fund_id}")
        return result
    
    @staticmethod
    def run_all_funds_compliance() -> Dict[str, Any]:
        """
        Run portfolio compliance for all funds.
        
        Returns:
            Dictionary with overall compliance results
        """
        logger.debug("Running portfolio compliance for all funds")
        
        funds = Fund.query.all()
        results = {
            'success': True,
            'total_funds': len(funds),
            'fund_results': [],
            'total_alerts': 0
        }
        
        for fund in funds:
            fund_result = PortfolioComplianceService.run_portfolio_compliance(fund.fund_id)
            results['fund_results'].append({
                'fund_id': fund.fund_id,
                'fund_name': fund.fund_name,
                'success': fund_result['success'],
                'alerts_count': len(fund_result.get('alerts', [])),
                'alerted': fund_result.get('alerted', False)
            })
            results['total_alerts'] += len(fund_result.get('alerts', []))
        
        logger.info(f"Portfolio compliance completed for {len(funds)} funds with {results['total_alerts']} total alerts")
        return results
