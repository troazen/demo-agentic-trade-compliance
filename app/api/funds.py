"""
Fund API endpoints.
"""

from decimal import Decimal
from flask import Blueprint, request, jsonify
import logging

from app.services.fund_service import FundService

logger = logging.getLogger(__name__)

funds_bp = Blueprint('funds', __name__)


@funds_bp.route('/', methods = ['GET'])
def get_all_funds():
    """Get all funds with summary information."""
    logger.debug("API: Getting all funds")
    
    try:
        funds = FundService.get_all_funds()
        return jsonify({
            'success': True,
            'funds': funds,
            'count': len(funds)
        })
    except Exception as e:
        logger.error(f"Failed to get funds: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@funds_bp.route('/<int:fund_id>', methods = ['GET'])
def get_fund(fund_id):
    """Get fund details with holdings."""
    logger.debug(f"API: Getting fund {fund_id}")
    
    try:
        fund = FundService.get_fund_by_id(fund_id)
        if not fund:
            return jsonify({
                'success': False,
                'error': 'Fund not found'
            }), 404
        
        # Get holdings with market values
        holdings = FundService.get_fund_holdings_with_market_values(fund_id)
        
        fund_data = fund.to_dict()
        fund_data['holdings'] = holdings
        fund_data['holdings_count'] = len(holdings)
        
        return jsonify({
            'success': True,
            'fund': fund_data
        })
    except Exception as e:
        logger.error(f"Failed to get fund {fund_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@funds_bp.route('/<int:fund_id>/cash', methods = ['PUT'])
def update_fund_cash(fund_id):
    """Update fund cash amount."""
    logger.debug(f"API: Updating cash for fund {fund_id}")
    
    try:
        data = request.get_json()
        if not data or 'cash' not in data:
            return jsonify({
                'success': False,
                'error': 'Cash amount is required'
            }), 400
        
        try:
            new_cash = Decimal(str(data['cash']))
        except (ValueError, TypeError):
            return jsonify({
                'success': False,
                'error': 'Invalid cash amount'
            }), 400
        
        success = FundService.update_fund_cash(fund_id, new_cash)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to update fund cash'
            }), 500
        
        # Get updated fund data
        fund = FundService.get_fund_by_id(fund_id)
        return jsonify({
            'success': True,
            'fund': fund.to_dict(),
            'message': 'Fund cash updated successfully'
        })
    except Exception as e:
        logger.error(f"Failed to update fund {fund_id} cash: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@funds_bp.route('/<int:fund_id>/total-assets', methods = ['GET'])
def get_fund_total_assets(fund_id):
    """Get fund total assets."""
    logger.debug(f"API: Getting total assets for fund {fund_id}")
    
    try:
        total_assets = FundService.calculate_total_assets(fund_id)
        if total_assets is None:
            return jsonify({
                'success': False,
                'error': 'Fund not found'
            }), 404
        
        return jsonify({
            'success': True,
            'fund_id': fund_id,
            'total_assets': float(total_assets)
        })
    except Exception as e:
        logger.error(f"Failed to get total assets for fund {fund_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@funds_bp.route('/<int:fund_id>/net-assets', methods = ['GET'])
def get_fund_net_assets(fund_id):
    """Get fund net assets."""
    logger.debug(f"API: Getting net assets for fund {fund_id}")
    
    try:
        net_assets = FundService.calculate_net_assets(fund_id)
        if net_assets is None:
            return jsonify({
                'success': False,
                'error': 'Fund not found'
            }), 404
        
        return jsonify({
            'success': True,
            'fund_id': fund_id,
            'net_assets': float(net_assets)
        })
    except Exception as e:
        logger.error(f"Failed to get net assets for fund {fund_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@funds_bp.route('/<int:fund_id>/total-assets-ex-cash', methods = ['GET'])
def get_fund_total_assets_ex_cash(fund_id):
    """Get fund total assets excluding cash."""
    logger.debug(f"API: Getting total assets ex cash for fund {fund_id}")
    
    try:
        total_assets_ex_cash = FundService.calculate_total_assets_ex_cash(fund_id)
        if total_assets_ex_cash is None:
            return jsonify({
                'success': False,
                'error': 'Fund not found'
            }), 404
        
        return jsonify({
            'success': True,
            'fund_id': fund_id,
            'total_assets_ex_cash': float(total_assets_ex_cash)
        })
    except Exception as e:
        logger.error(f"Failed to get total assets ex cash for fund {fund_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@funds_bp.route('/', methods = ['POST'])
def create_fund():
    """Create a new fund."""
    logger.debug("API: Creating new fund")
    
    try:
        data = request.get_json()
        if not data or 'fund_name' not in data:
            return jsonify({
                'success': False,
                'error': 'Fund name is required'
            }), 400
        
        fund_name = data['fund_name']
        initial_cash = Decimal(str(data.get('initial_cash', 0)))
        
        fund = FundService.create_fund(fund_name, initial_cash)
        if not fund:
            return jsonify({
                'success': False,
                'error': 'Failed to create fund'
            }), 500
        
        return jsonify({
            'success': True,
            'fund': fund.to_dict(),
            'message': 'Fund created successfully'
        }), 201
    except Exception as e:
        logger.error(f"Failed to create fund: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
