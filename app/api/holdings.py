"""
Holdings API endpoints.
"""

from flask import Blueprint, request, jsonify
import logging

from app.services.holdings_service import HoldingsService

logger = logging.getLogger(__name__)

holdings_bp = Blueprint('holdings', __name__)


@holdings_bp.route('/<int:fund_id>/holdings', methods = ['GET'])
def get_fund_holdings(fund_id):
    """Get holdings for a fund with market values."""
    logger.debug(f"API: Getting holdings for fund {fund_id}")
    
    try:
        holdings = HoldingsService.get_holdings_with_market_values(fund_id)
        return jsonify({
            'success': True,
            'fund_id': fund_id,
            'holdings': holdings,
            'count': len(holdings)
        })
    except Exception as e:
        logger.error(f"Failed to get holdings for fund {fund_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
