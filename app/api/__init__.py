"""
API blueprint registration and error handling with Flask-RESTX for Swagger documentation.
"""

from flask import Flask
from flask_restx import Api, Resource
import logging

from app.services.fund_service import FundService
from app.services.holdings_service import HoldingsService
from app.services.security_service import SecurityService
from app.services.trade_service import TradeService
from app.services.alert_service import AlertService

# Create Flask-RESTX API instance
api = Api(
    version = '1.0',
    title = 'Trade Compliance System API',
    description = 'REST API for the Investment Operations Compliance System',
    doc = '/swagger/',  # Swagger UI will be available at /swagger/
    prefix = '/api'
)

# Import all API modules to register routes
from app.api.funds import funds_ns
from app.api.holdings import holdings_ns
from app.api.securities import securities_ns
from app.api.trades import trades_ns
from app.api.rules import rules_ns
from app.api.alerts import alerts_ns

# Register namespaces
api.add_namespace(funds_ns)
api.add_namespace(holdings_ns)
api.add_namespace(securities_ns)
api.add_namespace(trades_ns)
api.add_namespace(rules_ns)
api.add_namespace(alerts_ns)

# Import models for Swagger documentation
from app.api.models import *

logger = logging.getLogger(__name__)

# Health check namespace
health_ns = api.namespace('health', description = 'Health check operations')

@health_ns.route('/')
class HealthCheck(Resource):
    @health_ns.doc('health_check')
    @health_ns.marshal_with(health_response)
    def get(self):
        """Health check endpoint."""
        return {
            'status': 'healthy',
            'message': 'Investment Operations Compliance System API is running'
        }
