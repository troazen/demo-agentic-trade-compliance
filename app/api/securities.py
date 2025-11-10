"""
Securities API endpoints with Flask-RESTX for Swagger documentation.
"""

from flask import request
from flask_restx import Namespace, Resource, fields
import logging

from app.services.security_service import SecurityService
from app.api.models import (
    securities_list_response, security_model, security_with_issuer,
    success_response, error_response
)

logger = logging.getLogger(__name__)

# Create namespace for securities
securities_ns = Namespace('securities', description = 'Securities management operations')


@securities_ns.route('/')
class SecuritiesList(Resource):
    @securities_ns.doc('get_securities')
    @securities_ns.marshal_with(securities_list_response)
    @securities_ns.param('q', 'Search query (ticker or issuer name)')
    def get(self):
        """Get all securities with current prices."""
        logger.debug("API: Getting all securities")
        
        try:
            search_query = request.args.get('q')
            
            if search_query:
                # Search securities
                securities = SecurityService.search_securities(search_query)
            else:
                # Get all securities
                securities = SecurityService.get_securities_with_prices()
            
            result = []
            for security in securities:
                if isinstance(security, dict):
                    result.append(security)
                else:
                    security_data = security.to_dict()
                    current_price = SecurityService.get_current_price(security.ticker)
                    security_data['current_price'] = float(current_price) if current_price else None
                    result.append(security_data)
            
            return {
                'success': True,
                'securities': result,
                'count': len(result)
            }
        except Exception as e:
            logger.error(f"Failed to get securities: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@securities_ns.route('/search')
class SecuritySearch(Resource):
    @securities_ns.doc('search_securities')
    @securities_ns.marshal_with(securities_list_response)
    @securities_ns.param('q', 'Search query (ticker or issuer name)', required = True)
    def get(self):
        """Search securities by ticker or issuer name."""
        logger.debug("API: Searching securities")
        
        try:
            search_query = request.args.get('q')
            
            if not search_query or not search_query.strip():
                return {
                    'success': False,
                    'error': 'Search query is required'
                }, 400
            
            securities = SecurityService.search_securities(search_query)
            
            result = []
            for security in securities:
                security_data = security.to_dict()
                current_price = SecurityService.get_current_price(security.ticker)
                security_data['current_price'] = float(current_price) if current_price else None
                result.append(security_data)
            
            return {
                'success': True,
                'securities': result,
                'count': len(result)
            }
        except Exception as e:
            logger.error(f"Failed to search securities: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@securities_ns.route('/<string:ticker>')
class SecurityDetail(Resource):
    @securities_ns.doc('get_security')
    @securities_ns.marshal_with(security_with_issuer)
    def get(self, ticker):
        """Get security details by ticker."""
        logger.debug(f"API: Getting security {ticker}")
        
        try:
            security = SecurityService.get_security_by_ticker(ticker)
            
            if not security:
                return {
                    'success': False,
                    'error': 'Security not found'
                }, 404
            
            security_data = security.to_dict()
            current_price = SecurityService.get_current_price(ticker)
            security_data['current_price'] = float(current_price) if current_price else None
            
            # Get issuer details if available
            if security.issuer:
                security_data['issuer'] = security.issuer.to_dict()
            
            return {
                'success': True,
                'security': security_data
            }
        except Exception as e:
            logger.error(f"Failed to get security {ticker}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@securities_ns.route('/<string:ticker>/price')
class SecurityPrice(Resource):
    @securities_ns.doc('get_security_price')
    @securities_ns.marshal_with(success_response)
    def get(self, ticker):
        """Get current price for a security."""
        logger.debug(f"API: Getting price for security {ticker}")
        
        try:
            current_price = SecurityService.get_current_price(ticker)
            
            if current_price is None:
                return {
                    'success': False,
                    'error': 'Price not available for this security'
                }, 404
            
            return {
                'success': True,
                'ticker': ticker,
                'price': float(current_price)
            }
        except Exception as e:
            logger.error(f"Failed to get price for {ticker}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500