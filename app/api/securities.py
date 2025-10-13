"""
Securities API endpoints.
"""

from flask import Blueprint, request, jsonify
import logging

from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)

securities_bp = Blueprint('securities', __name__)


@securities_bp.route('/', methods = ['GET'])
def get_all_securities():
    """Get all securities with current prices."""
    logger.debug("API: Getting all securities")
    
    try:
        securities = SecurityService.get_securities_with_prices()
        return jsonify({
            'success': True,
            'securities': securities,
            'count': len(securities)
        })
    except Exception as e:
        logger.error(f"Failed to get securities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@securities_bp.route('/<ticker>', methods = ['GET'])
def get_security(ticker):
    """Get security details with all attributes."""
    logger.debug(f"API: Getting security {ticker}")
    
    try:
        security = SecurityService.get_security_by_ticker(ticker)
        if not security:
            return jsonify({
                'success': False,
                'error': 'Security not found'
            }), 404
        
        security_data = security.to_dict()
        current_price = SecurityService.get_current_price(ticker)
        security_data['current_price'] = float(current_price) if current_price else None
        
        return jsonify({
            'success': True,
            'security': security_data
        })
    except Exception as e:
        logger.error(f"Failed to get security {ticker}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@securities_bp.route('/search', methods = ['GET'])
def search_securities():
    """Search securities by ticker or issuer name."""
    logger.debug("API: Searching securities")
    
    try:
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                'success': False,
                'error': 'Search query is required'
            }), 400
        
        securities = SecurityService.search_securities(query)
        result = []
        
        for security in securities:
            security_data = security.to_dict()
            current_price = SecurityService.get_current_price(security.ticker)
            security_data['current_price'] = float(current_price) if current_price else None
            result.append(security_data)
        
        return jsonify({
            'success': True,
            'query': query,
            'securities': result,
            'count': len(result)
        })
    except Exception as e:
        logger.error(f"Failed to search securities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
