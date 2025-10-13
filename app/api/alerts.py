"""
Alerts API endpoints.
"""

from flask import Blueprint, request, jsonify
import logging
from datetime import datetime, timedelta

from app.services.alert_service import AlertService

logger = logging.getLogger(__name__)

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.route('/', methods = ['GET'])
def get_alerts():
    """List alerts with optional filters."""
    logger.debug("API: Getting alerts")
    
    try:
        fund_id = request.args.get('fund_id', type = int)
        rule_id = request.args.get('rule_id', type = int)
        trade_id = request.args.get('trade_id', type = int)
        status = request.args.get('status')
        limit = request.args.get('limit', type = int)
        
        # Parse date filters
        date_from = None
        date_to = None
        
        if request.args.get('date_from'):
            try:
                date_from = datetime.fromisoformat(request.args.get('date_from'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date_from format (use ISO format)'
                }), 400
        
        if request.args.get('date_to'):
            try:
                date_to = datetime.fromisoformat(request.args.get('date_to'))
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid date_to format (use ISO format)'
                }), 400
        
        alerts = AlertService.get_alerts(
            fund_id = fund_id,
            rule_id = rule_id,
            trade_id = trade_id,
            status = status,
            date_from = date_from,
            date_to = date_to,
            limit = limit
        )
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        logger.error(f"Failed to get alerts: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/<int:alert_id>', methods = ['GET'])
def get_alert(alert_id):
    """Get alert details."""
    logger.debug(f"API: Getting alert {alert_id}")
    
    try:
        alert = AlertService.get_alert_by_id(alert_id)
        if not alert:
            return jsonify({
                'success': False,
                'error': 'Alert not found'
            }), 404
        
        return jsonify({
            'success': True,
            'alert': alert.to_dict()
        })
    except Exception as e:
        logger.error(f"Failed to get alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/<int:alert_id>/override', methods = ['POST'])
def override_alert(alert_id):
    """Override an alert with a reason."""
    logger.debug(f"API: Overriding alert {alert_id}")
    
    try:
        data = request.get_json()
        if not data or 'reason' not in data:
            return jsonify({
                'success': False,
                'error': 'Override reason is required'
            }), 400
        
        reason = data['reason'].strip()
        if not reason:
            return jsonify({
                'success': False,
                'error': 'Override reason cannot be empty'
            }), 400
        
        success = AlertService.override_alert(alert_id, reason)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to override alert'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Alert overridden successfully'
        })
    except Exception as e:
        logger.error(f"Failed to override alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/<int:alert_id>/cancel', methods = ['POST'])
def cancel_alert(alert_id):
    """Cancel an alert."""
    logger.debug(f"API: Cancelling alert {alert_id}")
    
    try:
        success = AlertService.cancel_alert(alert_id)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to cancel alert'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Alert cancelled successfully'
        })
    except Exception as e:
        logger.error(f"Failed to cancel alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/summary', methods = ['GET'])
def get_alert_summary():
    """Get alert summary statistics."""
    logger.debug("API: Getting alert summary")
    
    try:
        fund_id = request.args.get('fund_id', type = int)
        summary = AlertService.get_alert_summary(fund_id = fund_id)
        
        return jsonify({
            'success': True,
            'summary': summary
        })
    except Exception as e:
        logger.error(f"Failed to get alert summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/rule/<int:rule_id>', methods = ['GET'])
def get_rule_alerts(rule_id):
    """Get all alerts for a specific rule."""
    logger.debug(f"API: Getting alerts for rule {rule_id}")
    
    try:
        limit = request.args.get('limit', type = int)
        alerts = AlertService.get_alerts_by_rule(rule_id, limit = limit)
        
        return jsonify({
            'success': True,
            'rule_id': rule_id,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        logger.error(f"Failed to get alerts for rule {rule_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@alerts_bp.route('/trade/<int:trade_id>', methods = ['GET'])
def get_trade_alerts(trade_id):
    """Get all alerts for a specific trade."""
    logger.debug(f"API: Getting alerts for trade {trade_id}")
    
    try:
        alerts = AlertService.get_trade_alerts(trade_id)
        
        return jsonify({
            'success': True,
            'trade_id': trade_id,
            'alerts': alerts,
            'count': len(alerts)
        })
    except Exception as e:
        logger.error(f"Failed to get alerts for trade {trade_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
