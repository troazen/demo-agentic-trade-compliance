"""
Trade API endpoints.
"""

from flask import Blueprint, request, jsonify
import logging

from app.services.trade_service import TradeService
from app.services.trade_executor import TradeExecutor
from app.services.compliance.trade_compliance import TradeComplianceService

logger = logging.getLogger(__name__)

trades_bp = Blueprint('trades', __name__)


@trades_bp.route('/', methods = ['POST'])
def create_trade():
    """Submit a new trade."""
    logger.debug("API: Creating new trade")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        required_fields = ['fund_id', 'ticker', 'direction', 'shares']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        # Validate inputs first to provide better error messages
        from app.services.trade_validator import TradeValidator
        validation_result = TradeValidator.validate_trade_inputs(
            data['fund_id'], data['ticker'], data['direction'], data['shares']
        )
        
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': validation_result['error']
            }), 400
        
        # Create trade
        trade = TradeService.create_trade(
            fund_id = data['fund_id'],
            ticker = data['ticker'],
            direction = data['direction'],
            shares = data['shares']
        )
        
        if not trade:
            return jsonify({
                'success': False,
                'error': 'Failed to create trade - internal error'
            }), 500
        
        # Process trade through flow
        flow_result = TradeService.process_trade_flow(trade.trade_id)
        if not flow_result['success']:
            return jsonify({
                'success': False,
                'error': flow_result['error']
            }), 400
        
        # Check compliance if trade is ready
        if flow_result['status'] == 'compliance':
            compliance_result = TradeComplianceService.check_trade_compliance(trade)
            
            if compliance_result['success'] and compliance_result['alerted']:
                # Trade has compliance alerts
                return jsonify({
                    'success': False,
                    'error': 'Compliance alerts triggered',
                    'trade_id': trade.trade_id,
                    'status': 'alert',
                    'alerts': compliance_result['alerts']
                }), 403
            elif compliance_result['success'] and not compliance_result['alerted']:
                # No alerts - execute trade
                execution_result = TradeExecutor.execute_trade(trade)
                if execution_result['success']:
                    return jsonify({
                        'success': True,
                        'trade_id': trade.trade_id,
                        'status': 'processed',
                        'message': 'Trade executed successfully'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': execution_result['error']
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': compliance_result['error']
                }), 500
        else:
            # Trade is in invalid status
            return jsonify({
                'success': False,
                'error': 'Trade validation failed',
                'trade_id': trade.trade_id,
                'status': flow_result['status']
            }), 400
            
    except Exception as e:
        logger.error(f"Failed to create trade: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@trades_bp.route('/<int:trade_id>', methods = ['GET'])
def get_trade(trade_id):
    """Get trade details and status."""
    logger.debug(f"API: Getting trade {trade_id}")
    
    try:
        trade = TradeService.get_trade_by_id(trade_id)
        if not trade:
            return jsonify({
                'success': False,
                'error': 'Trade not found'
            }), 404
        
        trade_data = trade.to_dict()
        
        # Add alerts if trade is in alert status
        if trade.status.value == 'alert':
            alerts = TradeComplianceService.get_trade_alerts(trade_id)
            trade_data['alerts'] = alerts
        
        return jsonify({
            'success': True,
            'trade': trade_data
        })
    except Exception as e:
        logger.error(f"Failed to get trade {trade_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@trades_bp.route('/', methods = ['GET'])
def get_trades():
    """List trades with optional filters."""
    logger.debug("API: Getting trades")
    
    try:
        fund_id = request.args.get('fund_id', type = int)
        status = request.args.get('status')
        
        if fund_id:
            trades = TradeService.get_trades_for_fund(fund_id)
        elif status:
            trades = TradeService.get_trades_by_status(status)
        else:
            # Get all trades (you might want to add pagination here)
            from app.models import Trade
            trades = Trade.query.order_by(Trade.created_at.desc()).limit(100).all()
        
        result = []
        for trade in trades:
            trade_data = trade.to_dict()
            result.append(trade_data)
        
        return jsonify({
            'success': True,
            'trades': result,
            'count': len(result)
        })
    except Exception as e:
        logger.error(f"Failed to get trades: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@trades_bp.route('/<int:trade_id>/override', methods = ['POST'])
def override_trade(trade_id):
    """Override trade alerts with reasons."""
    logger.debug(f"API: Overriding trade {trade_id}")
    
    try:
        data = request.get_json()
        if not data or 'override_reasons' not in data:
            return jsonify({
                'success': False,
                'error': 'Override reasons are required'
            }), 400
        
        override_reasons = data['override_reasons']
        if not isinstance(override_reasons, dict):
            return jsonify({
                'success': False,
                'error': 'Override reasons must be a dictionary mapping alert_id to reason'
            }), 400
        
        result = TradeComplianceService.override_trade_alerts(trade_id, override_reasons)
        
        if result['success']:
            # Execute trade if all alerts overridden
            if result['status'] == 'compliance':
                trade = TradeService.get_trade_by_id(trade_id)
                if trade:
                    execution_result = TradeExecutor.execute_trade(trade)
                    if execution_result['success']:
                        result['status'] = 'processed'
                        result['message'] = 'Trade executed successfully after override'
                    else:
                        result['success'] = False
                        result['error'] = execution_result['error']
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to override trade {trade_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@trades_bp.route('/<int:trade_id>/cancel', methods = ['POST'])
def cancel_trade(trade_id):
    """Cancel a trade."""
    logger.debug(f"API: Cancelling trade {trade_id}")
    
    try:
        result = TradeComplianceService.cancel_trade_alerts(trade_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to cancel trade {trade_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
