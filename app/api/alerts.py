"""
Alerts API endpoints with Flask-RESTX for Swagger documentation.
"""

from flask import request
from flask_restx import Namespace, Resource
import logging

from app.services.alert_service import AlertService
from app.api.models import alerts_list_response, success_response, alert_response, alert_override_request

logger = logging.getLogger(__name__)

# Create namespace for alerts
alerts_ns = Namespace('alerts', description = 'Alert management operations')


@alerts_ns.route('/')
class AlertsList(Resource):
    @alerts_ns.doc('get_alerts')
    @alerts_ns.marshal_with(alerts_list_response)
    @alerts_ns.param('fund_id', 'Filter by fund ID')
    @alerts_ns.param('rule_id', 'Filter by rule ID')
    @alerts_ns.param('trade_id', 'Filter by trade ID')
    @alerts_ns.param('status', 'Filter by alert status')
    @alerts_ns.param('limit', 'Limit number of results')
    def get(self):
        """Get all alerts with optional filters."""
        logger.debug("API: Getting all alerts")
        
        try:
            fund_id = request.args.get('fund_id', type = int)
            rule_id = request.args.get('rule_id', type = int)
            trade_id = request.args.get('trade_id', type = int)
            status = request.args.get('status')
            limit = request.args.get('limit', type = int)
            
            alerts = AlertService.get_alerts(
                fund_id = fund_id,
                rule_id = rule_id,
                trade_id = trade_id,
                status = status,
                limit = limit
            )
            
            return {
                'success': True,
                'alerts': alerts,
                'count': len(alerts)
            }
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@alerts_ns.route('/<int:alert_id>')
class AlertDetail(Resource):
    @alerts_ns.doc('get_alert')
    @alerts_ns.marshal_with(alert_response)
    def get(self, alert_id):
        """Get alert details by ID."""
        logger.debug(f"API: Getting alert {alert_id}")
        
        try:
            alert = AlertService.get_alert_by_id(alert_id)
            
            if not alert:
                return {
                    'success': False,
                    'error': 'Alert not found'
                }, 404
            
            alert_data = alert.to_dict()
            
            return {
                'success': True,
                'alert': alert_data
            }
        except Exception as e:
            logger.error(f"Failed to get alert {alert_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@alerts_ns.route('/<int:alert_id>/override')
class AlertOverride(Resource):
    @alerts_ns.doc('override_alert')
    @alerts_ns.expect(alert_override_request)
    @alerts_ns.marshal_with(success_response)
    def put(self, alert_id):
        """Override alert with reason."""
        logger.debug(f"API: Overriding alert {alert_id}")
        
        try:
            data = request.get_json()
            if not data or 'reason' not in data:
                return {
                    'success': False,
                    'error': 'Override reason is required'
                }, 400
            
            reason = data['reason']
            success = AlertService.override_alert(alert_id, reason)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to override alert'
                }, 500
            
            return {
                'success': True,
                'message': 'Alert overridden successfully'
            }
        except Exception as e:
            logger.error(f"Failed to override alert {alert_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@alerts_ns.route('/<int:alert_id>/cancel')
class AlertCancel(Resource):
    @alerts_ns.doc('cancel_alert')
    @alerts_ns.marshal_with(success_response)
    def put(self, alert_id):
        """Cancel alert."""
        logger.debug(f"API: Cancelling alert {alert_id}")
        
        try:
            success = AlertService.cancel_alert(alert_id)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to cancel alert'
                }, 500
            
            return {
                'success': True,
                'message': 'Alert cancelled successfully'
            }
        except Exception as e:
            logger.error(f"Failed to cancel alert {alert_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@alerts_ns.route('/summary')
class AlertsSummary(Resource):
    @alerts_ns.doc('get_alerts_summary')
    @alerts_ns.marshal_with(success_response)
    @alerts_ns.param('fund_id', 'Filter by fund ID')
    def get(self):
        """Get alert summary statistics."""
        logger.debug("API: Getting alert summary")
        
        try:
            fund_id = request.args.get('fund_id', type = int)
            summary = AlertService.get_alert_summary(fund_id = fund_id)
            
            return {
                'success': True,
                'summary': summary
            }
        except Exception as e:
            logger.error(f"Failed to get alert summary: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@alerts_ns.route('/fund/<int:fund_id>')
class FundAlerts(Resource):
    @alerts_ns.doc('get_fund_alerts')
    @alerts_ns.marshal_with(alerts_list_response)
    def get(self, fund_id):
        """Get all alerts for a specific fund."""
        logger.debug(f"API: Getting alerts for fund {fund_id}")
        
        try:
            alerts = AlertService.get_alerts(fund_id = fund_id)
            
            return {
                'success': True,
                'alerts': alerts,
                'count': len(alerts)
            }
        except Exception as e:
            logger.error(f"Failed to get alerts for fund {fund_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@alerts_ns.route('/trade/<int:trade_id>')
class TradeAlerts(Resource):
    @alerts_ns.doc('get_trade_alerts')
    @alerts_ns.marshal_with(alerts_list_response)
    def get(self, trade_id):
        """Get all alerts for a specific trade."""
        logger.debug(f"API: Getting alerts for trade {trade_id}")
        
        try:
            alerts = AlertService.get_trade_alerts(trade_id)
            
            return {
                'success': True,
                'alerts': alerts,
                'count': len(alerts)
            }
        except Exception as e:
            logger.error(f"Failed to get alerts for trade {trade_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500