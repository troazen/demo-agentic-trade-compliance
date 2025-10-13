"""
API blueprint registration and error handling.
"""

from flask import Blueprint, jsonify
import logging

from app.services.fund_service import FundService
from app.services.holdings_service import HoldingsService
from app.services.security_service import SecurityService
from app.services.trade_service import TradeService
from app.services.alert_service import AlertService

# Create API blueprint
api_bp = Blueprint('api', __name__)

# Import all API modules to register routes
from app.api.funds import funds_bp
from app.api.holdings import holdings_bp
from app.api.securities import securities_bp
from app.api.trades import trades_bp
from app.api.rules import rules_bp
from app.api.alerts import alerts_bp

# Register blueprints
api_bp.register_blueprint(funds_bp, url_prefix = '/funds')
api_bp.register_blueprint(holdings_bp, url_prefix = '/funds')
api_bp.register_blueprint(securities_bp, url_prefix = '/securities')
api_bp.register_blueprint(trades_bp, url_prefix = '/trades')
api_bp.register_blueprint(rules_bp, url_prefix = '/rules')
api_bp.register_blueprint(alerts_bp, url_prefix = '/alerts')

logger = logging.getLogger(__name__)


@api_bp.route('/health', methods = ['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Investment Operations Compliance System API is running'
    })


@api_bp.errorhandler(400)
def bad_request(error):
    """Handle 400 Bad Request errors."""
    return jsonify({
        'error': 'Bad Request',
        'message': str(error.description) if error.description else 'Invalid request'
    }), 400


@api_bp.errorhandler(404)
def not_found(error):
    """Handle 404 Not Found errors."""
    return jsonify({
        'error': 'Not Found',
        'message': str(error.description) if error.description else 'Resource not found'
    }), 404


@api_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500
