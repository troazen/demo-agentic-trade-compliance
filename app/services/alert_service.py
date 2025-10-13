"""
Alert service for managing compliance alerts.
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

from app.models import db, Alert, Fund, Rule, Trade
from app.constants import AlertStatus
from app.config import get_eastern_time

logger = logging.getLogger(__name__)


class AlertService:
    """Service class for alert management operations."""
    
    @staticmethod
    def create_alert(rule_id: int, fund_id: int, trade_id: Optional[int] = None,
                    calculated_percentage: Optional[float] = None,
                    holdings_triggered: Optional[List[Dict[str, Any]]] = None) -> Optional[Alert]:
        """
        Create a new alert record.
        
        Args:
            rule_id: Rule ID that triggered the alert
            fund_id: Fund ID
            trade_id: Trade ID (None for portfolio compliance)
            calculated_percentage: Calculated percentage that triggered alert
            holdings_triggered: List of holdings that triggered the alert
            
        Returns:
            Created Alert object or None if creation failed
        """
        logger.debug(f"Creating alert for rule {rule_id}, fund {fund_id}, trade {trade_id}")
        
        try:
            # Serialize holdings if provided
            holdings_json = None
            if holdings_triggered:
                import json
                holdings_json = json.dumps(holdings_triggered)
            
            alert = Alert(
                rule_id = rule_id,
                fund_id = fund_id,
                trade_id = trade_id,
                calculated_percentage = calculated_percentage,
                holdings_triggered = holdings_json,
                status = AlertStatus.PENDING
            )
            
            db.session.add(alert)
            db.session.commit()
            
            logger.info(f"Created alert {alert.alert_id} for rule {rule_id}")
            return alert
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to create alert for rule {rule_id}: {e}")
            return None
    
    @staticmethod
    def get_alert_by_id(alert_id: int) -> Optional[Alert]:
        """
        Get alert by ID.
        
        Args:
            alert_id: Alert ID to retrieve
            
        Returns:
            Alert object or None if not found
        """
        logger.debug(f"Retrieving alert {alert_id}")
        
        alert = Alert.query.get(alert_id)
        if alert:
            logger.debug(f"Found alert: {alert.rule.rule_name if alert.rule else 'Unknown rule'}")
        else:
            logger.warning(f"Alert {alert_id} not found")
        
        return alert
    
    @staticmethod
    def get_alerts(fund_id: Optional[int] = None, rule_id: Optional[int] = None,
                   trade_id: Optional[int] = None, status: Optional[str] = None,
                   date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get alerts with optional filters.
        
        Args:
            fund_id: Filter by fund ID
            rule_id: Filter by rule ID
            trade_id: Filter by trade ID
            status: Filter by alert status
            date_from: Filter alerts from this date
            date_to: Filter alerts to this date
            limit: Limit number of results
            
        Returns:
            List of alert dictionaries
        """
        logger.debug(f"Getting alerts with filters: fund_id={fund_id}, rule_id={rule_id}, trade_id={trade_id}, status={status}")
        
        query = Alert.query
        
        if fund_id:
            query = query.filter(Alert.fund_id == fund_id)
        if rule_id:
            query = query.filter(Alert.rule_id == rule_id)
        if trade_id:
            query = query.filter(Alert.trade_id == trade_id)
        if status:
            try:
                status_enum = AlertStatus(status)
                query = query.filter(Alert.status == status_enum)
            except ValueError:
                logger.error(f"Invalid alert status: {status}")
                return []
        
        if date_from:
            query = query.filter(Alert.created_at >= date_from)
        if date_to:
            query = query.filter(Alert.created_at <= date_to)
        
        query = query.order_by(Alert.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        alerts = query.all()
        
        result = []
        for alert in alerts:
            alert_data = alert.to_dict()
            result.append(alert_data)
        
        logger.debug(f"Retrieved {len(result)} alerts")
        return result
    
    @staticmethod
    def override_alert(alert_id: int, reason: str) -> bool:
        """
        Override an alert with a reason.
        
        Args:
            alert_id: Alert ID to override
            reason: Override reason
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Overriding alert {alert_id} with reason: {reason}")
        
        alert = Alert.query.get(alert_id)
        if not alert:
            logger.error(f"Alert {alert_id} not found")
            return False
        
        try:
            alert.override(reason)
            db.session.commit()
            
            logger.info(f"Successfully overridden alert {alert_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to override alert {alert_id}: {e}")
            return False
    
    @staticmethod
    def cancel_alert(alert_id: int) -> bool:
        """
        Cancel an alert.
        
        Args:
            alert_id: Alert ID to cancel
            
        Returns:
            True if successful, False otherwise
        """
        logger.debug(f"Cancelling alert {alert_id}")
        
        alert = Alert.query.get(alert_id)
        if not alert:
            logger.error(f"Alert {alert_id} not found")
            return False
        
        try:
            alert.cancel()
            db.session.commit()
            
            logger.info(f"Successfully cancelled alert {alert_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to cancel alert {alert_id}: {e}")
            return False
    
    @staticmethod
    def get_alert_summary(fund_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get alert summary statistics.
        
        Args:
            fund_id: Optional fund ID to filter by
            
        Returns:
            Dictionary with alert summary
        """
        logger.debug(f"Getting alert summary for fund_id={fund_id}")
        
        query = Alert.query
        if fund_id:
            query = query.filter(Alert.fund_id == fund_id)
        
        total_alerts = query.count()
        pending_alerts = query.filter(Alert.status == AlertStatus.PENDING).count()
        overridden_alerts = query.filter(Alert.status == AlertStatus.OVERRIDDEN).count()
        cancelled_alerts = query.filter(Alert.status == AlertStatus.CANCELLED).count()
        
        # Get recent alerts (last 24 hours)
        cutoff_time = get_eastern_time() - timedelta(hours = 24)
        recent_alerts = query.filter(Alert.created_at >= cutoff_time).count()
        
        summary = {
            'total_alerts': total_alerts,
            'pending_alerts': pending_alerts,
            'overridden_alerts': overridden_alerts,
            'cancelled_alerts': cancelled_alerts,
            'recent_alerts_24h': recent_alerts
        }
        
        logger.debug(f"Alert summary: {summary}")
        return summary
    
    @staticmethod
    def get_alerts_by_rule(rule_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all alerts for a specific rule.
        
        Args:
            rule_id: Rule ID
            limit: Optional limit on number of alerts
            
        Returns:
            List of alert dictionaries
        """
        logger.debug(f"Getting alerts for rule {rule_id}")
        
        query = Alert.query.filter_by(rule_id = rule_id).order_by(Alert.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        alerts = query.all()
        
        result = []
        for alert in alerts:
            alert_data = alert.to_dict()
            result.append(alert_data)
        
        logger.debug(f"Retrieved {len(result)} alerts for rule {rule_id}")
        return result
    
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
        
        alerts = Alert.query.filter_by(trade_id = trade_id).order_by(Alert.created_at.desc()).all()
        
        result = []
        for alert in alerts:
            alert_data = alert.to_dict()
            result.append(alert_data)
        
        logger.debug(f"Retrieved {len(result)} alerts for trade {trade_id}")
        return result
    
    @staticmethod
    def cleanup_old_alerts(days: int = 90) -> int:
        """
        Clean up old alerts (for maintenance).
        
        Args:
            days: Number of days to keep alerts
            
        Returns:
            Number of alerts deleted
        """
        logger.debug(f"Cleaning up alerts older than {days} days")
        
        cutoff_time = get_eastern_time() - timedelta(days = days)
        
        try:
            old_alerts = Alert.query.filter(Alert.created_at < cutoff_time).all()
            count = len(old_alerts)
            
            for alert in old_alerts:
                db.session.delete(alert)
            
            db.session.commit()
            
            logger.info(f"Cleaned up {count} old alerts")
            return count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to cleanup old alerts: {e}")
            return 0
