"""
Holdings API endpoints with Flask-RESTX for Swagger documentation.
"""

from flask import request
from flask_restx import Namespace, Resource
import logging

from app.services.holdings_service import HoldingsService
from app.services.fund_service import FundService
from app.api.models import success_response

logger = logging.getLogger(__name__)

# Create namespace for holdings
holdings_ns = Namespace('holdings', description = 'Holdings management operations')


@holdings_ns.route('/')
class HoldingsList(Resource):
    @holdings_ns.doc('get_all_holdings')
    @holdings_ns.marshal_with(success_response)
    @holdings_ns.param('fund_id', 'Filter by fund ID')
    def get(self):
        """Get all holdings with optional filter by fund."""
        logger.debug("API: Getting all holdings")
        
        try:
            fund_id = request.args.get('fund_id', type = int)
            
            if fund_id:
                # Get holdings for specific fund
                holdings = HoldingsService.get_holdings_with_market_values(fund_id)
            else:
                # Get all holdings
                from app.models import Holding
                holdings_query = Holding.query
                holdings_list = holdings_query.all()
                
                holdings = []
                for holding in holdings_list:
                    holding_data = holding.to_dict()
                    holdings.append(holding_data)
            
            return {
                'success': True,
                'holdings': holdings,
                'count': len(holdings)
            }
        except Exception as e:
            logger.error(f"Failed to get holdings: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@holdings_ns.route('/fund/<int:fund_id>')
class FundHoldings(Resource):
    @holdings_ns.doc('get_fund_holdings')
    @holdings_ns.marshal_with(success_response)
    def get(self, fund_id):
        """Get holdings for a specific fund with market values."""
        logger.debug(f"API: Getting holdings for fund {fund_id}")
        
        try:
            holdings = HoldingsService.get_holdings_with_market_values(fund_id)
            
            # Also get fund information
            from app.services.fund_service import FundService
            fund = FundService.get_fund_by_id(fund_id)
            if not fund:
                return {
                    'success': False,
                    'error': 'Fund not found'
                }, 404
            
            return {
                'success': True,
                'fund': fund.to_dict(),
                'holdings': holdings,
                'holdings_count': len(holdings)
            }
        except Exception as e:
            logger.error(f"Failed to get holdings for fund {fund_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@holdings_ns.route('/fund/<int:fund_id>/compliance-check')
class FundComplianceCheck(Resource):
    @holdings_ns.doc('run_portfolio_compliance_check')
    @holdings_ns.marshal_with(success_response)
    def post(self, fund_id):
        """Run batch portfolio compliance check for a fund."""
        logger.debug(f"API: Running portfolio compliance check for fund {fund_id}")
        
        try:
            from app.services.compliance.portfolio_compliance import PortfolioCompliance
            
            # Run portfolio compliance check
            result = PortfolioCompliance.check_fund_compliance(fund_id)
            
            return {
                'success': True,
                'alerts': result.get('alerts', []),
                'alerts_count': result.get('alerts_count', 0),
                'rules_checked': result.get('rules_checked', 0),
                'fund_id': fund_id
            }
        except Exception as e:
            logger.error(f"Failed to run compliance check for fund {fund_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500