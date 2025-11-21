"""
Trades API endpoints with Flask-RESTX for Swagger documentation.
"""

from flask import request
from flask_restx import Namespace, Resource
import logging

from app.services.trade_service import TradeService
from app.api.models import (
    trade_response, trade_create_request,
    success_response, error_response, trade_override_request
)

logger = logging.getLogger(__name__)

# Create namespace for trades
trades_ns = Namespace('trades', description = 'Trade management operations')


@trades_ns.route('/')
class TradesList(Resource):
    @trades_ns.doc('get_trades')
    @trades_ns.marshal_with(success_response)
    @trades_ns.param('fund_id', 'Filter by fund ID')
    @trades_ns.param('status', 'Filter by trade status')
    def get(self):
        """Get all trades with optional filters."""
        logger.debug("API: Getting all trades")
        
        try:
            fund_id = request.args.get('fund_id', type = int)
            status = request.args.get('status')
            
            if fund_id:
                trades = TradeService.get_trades_for_fund(fund_id)
            elif status:
                trades = TradeService.get_trades_by_status(status)
            else:
                from app.models import Trade
                trades = Trade.query.order_by(Trade.created_at.desc()).limit(100).all()
            
            result = []
            for trade in trades:
                trade_data = trade.to_dict()
                result.append(trade_data)
            
            return {
                'success': True,
                'trades': result,
                'count': len(result)
            }
        except Exception as e:
            logger.error(f"Failed to get trades: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @trades_ns.doc('create_trade')
    @trades_ns.expect(trade_create_request)
    @trades_ns.marshal_with(trade_response)
    def post(self):
        """Create and submit a new trade."""
        logger.debug("API: Creating new trade")
        
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'error': 'Request body is required'
                }, 400
            
            # Validate required fields
            required_fields = ['fund_id', 'ticker', 'direction', 'shares']
            for field in required_fields:
                if field not in data:
                    return {
                        'success': False,
                        'error': f'{field} is required'
                    }, 400
            
            # Create trade
            trade = TradeService.create_trade(
                fund_id = data['fund_id'],
                ticker = data['ticker'],
                direction = data['direction'],
                shares = data['shares']
            )
            
            if not trade:
                return {
                    'success': False,
                    'error': 'Failed to create trade'
                }, 500
            
            # Process trade through flow
            result = TradeService.process_trade_flow(trade.trade_id)
            
            if not result['success']:
                return result, 400
            
            # Run compliance checks automatically
            from app.services.compliance.trade_compliance import TradeComplianceService
            compliance_result = TradeComplianceService.check_trade_compliance(trade)
            
            if not compliance_result.get('success'):
                logger.error(f"Compliance check failed for trade {trade.trade_id}: {compliance_result.get('error')}")
                # Still return trade details, but with error message
                trade_data = trade.to_dict()
                return {
                    'success': False,
                    'trade': trade_data,
                    'error': compliance_result.get('error', 'Compliance check failed')
                }, 500
            
            # Refresh trade to get updated status
            from app.models import Trade, db
            db.session.refresh(trade)
            
            # If alerts were found, return 403 status per PRD
            if compliance_result.get('alerted', False):
                trade_data = trade.to_dict()
                return {
                    'success': True,
                    'trade': trade_data,
                    'alerts': compliance_result.get('alerts', []),
                    'message': 'Trade submitted but compliance alerts found'
                }, 403
            
            # No alerts - automatically execute the trade per PRD Step 12
            from app.services.trade_executor import TradeExecutor
            execution_result = TradeExecutor.execute_trade(trade)
            
            if not execution_result.get('success'):
                logger.error(f"Failed to execute trade {trade.trade_id}: {execution_result.get('error')}")
                trade_data = trade.to_dict()
                return {
                    'success': False,
                    'trade': trade_data,
                    'error': execution_result.get('error', 'Failed to execute trade')
                }, 500
            
            # Refresh trade to get final status
            db.session.refresh(trade)
            trade_data = trade.to_dict()
            
            # Trade processed successfully
            return {
                'success': True,
                'trade': trade_data,
                'message': 'Trade submitted and executed successfully'
            }, 201
        except Exception as e:
            logger.error(f"Failed to create trade: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@trades_ns.route('/<int:trade_id>')
class TradeDetail(Resource):
    @trades_ns.doc('get_trade')
    @trades_ns.marshal_with(trade_response)
    def get(self, trade_id):
        """Get trade details by ID."""
        logger.debug(f"API: Getting trade {trade_id}")
        
        try:
            trade = TradeService.get_trade_by_id(trade_id)
            
            if not trade:
                return {
                    'success': False,
                    'error': 'Trade not found'
                }, 404
            
            trade_data = trade.to_dict()
            
            return {
                'success': True,
                'trade': trade_data
            }
        except Exception as e:
            logger.error(f"Failed to get trade {trade_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@trades_ns.route('/<int:trade_id>/override')
class TradeOverride(Resource):
    @trades_ns.doc('override_trade')
    @trades_ns.expect(trade_override_request)
    @trades_ns.marshal_with(success_response)
    def post(self, trade_id):
        """Override trade alerts and proceed with trade."""
        logger.debug(f"API: Overriding alerts for trade {trade_id}")
        
        try:
            data = request.get_json()
            if not data or 'alerts' not in data:
                return {
                    'success': False,
                    'error': 'Alerts override data is required'
                }, 400
            
            # Import AlertService
            from app.services.alert_service import AlertService
            
            # Get all alerts for this trade
            alerts = AlertService.get_trade_alerts(trade_id)
            
            # Apply overrides
            override_data = data.get('alerts', {})
            for alert in alerts:
                alert_id = alert['alert_id']
                if alert_id in override_data:
                    override_reason = override_data[alert_id].get('reason', 'User override')
                    AlertService.override_alert(alert_id, override_reason)
            
            # Get the trade object
            trade = TradeService.get_trade_by_id(trade_id)
            if not trade:
                return {
                    'success': False,
                    'error': 'Trade not found'
                }, 404
            
            # Execute the trade after overriding alerts (per PRD Step 12)
            from app.services.trade_executor import TradeExecutor
            execution_result = TradeExecutor.execute_trade(trade)
            
            if not execution_result.get('success'):
                logger.error(f"Failed to execute trade {trade_id} after override: {execution_result.get('error')}")
                return {
                    'success': False,
                    'error': execution_result.get('error', 'Failed to execute trade')
                }, 500
            
            # Trade executed successfully
            return {
                'success': True,
                'message': 'Trade alerts overridden and trade processed'
            }
        except Exception as e:
            logger.error(f"Failed to override trade {trade_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@trades_ns.route('/<int:trade_id>/cancel')
class TradeCancel(Resource):
    @trades_ns.doc('cancel_trade')
    @trades_ns.marshal_with(success_response)
    def post(self, trade_id):
        """Cancel a trade."""
        logger.debug(f"API: Cancelling trade {trade_id}")
        
        try:
            # Import AlertService
            from app.services.alert_service import AlertService
            
            # Get all alerts for this trade
            alerts = AlertService.get_trade_alerts(trade_id)
            
            # Cancel all alerts
            for alert in alerts:
                AlertService.cancel_alert(alert['alert_id'])
            
            # Update trade status
            TradeService.update_trade_status(trade_id, 'cancelled')
            
            return {
                'success': True,
                'message': 'Trade cancelled'
            }
        except Exception as e:
            logger.error(f"Failed to cancel trade {trade_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@trades_ns.route('/fund/<int:fund_id>')
class FundTrades(Resource):
    @trades_ns.doc('get_fund_trades')
    @trades_ns.marshal_with(success_response)
    def get(self, fund_id):
        """Get all trades for a specific fund."""
        logger.debug(f"API: Getting trades for fund {fund_id}")
        
        try:
            trades = TradeService.get_trades_for_fund(fund_id)
            
            result = []
            for trade in trades:
                trade_data = trade.to_dict()
                result.append(trade_data)
            
            return {
                'success': True,
                'trades': result,
                'count': len(result)
            }
        except Exception as e:
            logger.error(f"Failed to get trades for fund {fund_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500