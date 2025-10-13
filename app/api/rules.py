"""
Rules API endpoints.
"""

from flask import Blueprint, request, jsonify
import logging

from app.models import db, Rule, RuleAttachment, Fund
from app.services.compliance.rule_validator import RuleValidator
from app.services.compliance.compliance_engine import ComplianceEngine
from app.services.compliance.portfolio_compliance import PortfolioComplianceService

logger = logging.getLogger(__name__)

rules_bp = Blueprint('rules', __name__)


@rules_bp.route('/', methods = ['GET'])
def get_all_rules():
    """List all compliance rules with optional filters."""
    logger.debug("API: Getting all rules")
    
    try:
        fund_id = request.args.get('fund_id', type = int)
        rule_name = request.args.get('rule_name', '').strip()
        
        query = Rule.query
        
        if fund_id:
            query = query.join(RuleAttachment).filter(RuleAttachment.fund_id == fund_id)
        
        if rule_name:
            query = query.filter(Rule.rule_name.ilike(f'%{rule_name}%'))
        
        rules = query.order_by(Rule.created_at.desc()).all()
        
        result = []
        for rule in rules:
            rule_data = rule.to_dict()
            # Add attached fund names
            attached_funds = [att.fund.fund_name for att in rule.attachments if att.active and att.fund]
            rule_data['attached_funds'] = attached_funds
            result.append(rule_data)
        
        return jsonify({
            'success': True,
            'rules': result,
            'count': len(result)
        })
    except Exception as e:
        logger.error(f"Failed to get rules: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rules_bp.route('/<int:rule_id>', methods = ['GET'])
def get_rule(rule_id):
    """Get rule details."""
    logger.debug(f"API: Getting rule {rule_id}")
    
    try:
        rule = Rule.query.get(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': 'Rule not found'
            }), 404
        
        rule_data = rule.to_dict()
        # Add attached fund names
        attached_funds = [att.fund.fund_name for att in rule.attachments if att.active and att.fund]
        rule_data['attached_funds'] = attached_funds
        
        return jsonify({
            'success': True,
            'rule': rule_data
        })
    except Exception as e:
        logger.error(f"Failed to get rule {rule_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rules_bp.route('/', methods = ['POST'])
def create_rule():
    """Create a new compliance rule."""
    logger.debug("API: Creating new rule")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Validate rule data
        validation_result = RuleValidator.validate_rule_data(data)
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'validation_errors': validation_result['errors']
            }), 400
        
        # Create rule
        rule = Rule(
            rule_name = data['rule_name'],
            alert_message = data['alert_message'],
            trade_compliance_mode = data.get('trade_compliance_mode', True),
            portfolio_compliance_mode = data.get('portfolio_compliance_mode', True),
            logic = data.get('logic', ''),
            denominator = data['denominator'],
            alert_if = data.get('alert_if'),
            alert_level = data.get('alert_level'),
            active = data.get('active', True)
        )
        
        db.session.add(rule)
        db.session.commit()
        
        logger.info(f"Created rule {rule.rule_id}: {rule.rule_name}")
        return jsonify({
            'success': True,
            'rule': rule.to_dict(),
            'message': 'Rule created successfully'
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create rule: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rules_bp.route('/<int:rule_id>', methods = ['PUT'])
def update_rule(rule_id):
    """Update an existing rule."""
    logger.debug(f"API: Updating rule {rule_id}")
    
    try:
        rule = Rule.query.get(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': 'Rule not found'
            }), 404
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        # Update fields
        if 'rule_name' in data:
            rule.rule_name = data['rule_name']
        if 'alert_message' in data:
            rule.alert_message = data['alert_message']
        if 'trade_compliance_mode' in data:
            rule.trade_compliance_mode = data['trade_compliance_mode']
        if 'portfolio_compliance_mode' in data:
            rule.portfolio_compliance_mode = data['portfolio_compliance_mode']
        if 'logic' in data:
            rule.logic = data['logic']
        if 'denominator' in data:
            rule.denominator = data['denominator']
        if 'alert_if' in data:
            rule.alert_if = data['alert_if']
        if 'alert_level' in data:
            rule.alert_level = data['alert_level']
        if 'active' in data:
            rule.active = data['active']
        
        # Validate updated rule
        rule_data = rule.to_dict()
        validation_result = RuleValidator.validate_rule_data(rule_data)
        if not validation_result['valid']:
            return jsonify({
                'success': False,
                'error': 'Validation failed',
                'validation_errors': validation_result['errors']
            }), 400
        
        db.session.commit()
        
        logger.info(f"Updated rule {rule_id}")
        return jsonify({
            'success': True,
            'rule': rule.to_dict(),
            'message': 'Rule updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to update rule {rule_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rules_bp.route('/<int:rule_id>', methods = ['DELETE'])
def deactivate_rule(rule_id):
    """Deactivate a rule."""
    logger.debug(f"API: Deactivating rule {rule_id}")
    
    try:
        rule = Rule.query.get(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': 'Rule not found'
            }), 404
        
        rule.active = False
        db.session.commit()
        
        logger.info(f"Deactivated rule {rule_id}")
        return jsonify({
            'success': True,
            'message': 'Rule deactivated successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to deactivate rule {rule_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rules_bp.route('/<int:rule_id>/test', methods = ['POST'])
def test_rule(rule_id):
    """Test a rule against a fund (with optional test trade)."""
    logger.debug(f"API: Testing rule {rule_id}")
    
    try:
        rule = Rule.query.get(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': 'Rule not found'
            }), 404
        
        data = request.get_json() or {}
        fund_id = data.get('fund_id')
        test_trade = data.get('test_trade')
        
        if not fund_id:
            return jsonify({
                'success': False,
                'error': 'Fund ID is required for testing'
            }), 400
        
        # Verify fund exists
        fund = Fund.query.get(fund_id)
        if not fund:
            return jsonify({
                'success': False,
                'error': 'Fund not found'
            }), 404
        
        # Test rule
        if test_trade:
            # Test with a hypothetical trade
            trade_id = 0  # Use 0 for test trades
            result = ComplianceEngine.execute_rule(fund_id, trade_id, rule)
        else:
            # Test against current holdings
            result = ComplianceEngine.execute_rule(fund_id, 0, rule)
        
        return jsonify({
            'success': True,
            'rule_id': rule_id,
            'fund_id': fund_id,
            'test_result': result
        })
    except Exception as e:
        logger.error(f"Failed to test rule {rule_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rules_bp.route('/<int:rule_id>/attach', methods = ['POST'])
def attach_rule_to_fund(rule_id):
    """Attach a rule to a fund."""
    logger.debug(f"API: Attaching rule {rule_id} to fund")
    
    try:
        rule = Rule.query.get(rule_id)
        if not rule:
            return jsonify({
                'success': False,
                'error': 'Rule not found'
            }), 404
        
        data = request.get_json()
        if not data or 'fund_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Fund ID is required'
            }), 400
        
        fund_id = data['fund_id']
        fund = Fund.query.get(fund_id)
        if not fund:
            return jsonify({
                'success': False,
                'error': 'Fund not found'
            }), 404
        
        # Check if already attached
        existing_attachment = RuleAttachment.query.filter_by(
            rule_id = rule_id,
            fund_id = fund_id
        ).first()
        
        if existing_attachment:
            if existing_attachment.active:
                return jsonify({
                    'success': False,
                    'error': 'Rule is already attached to this fund'
                }), 400
            else:
                # Reactivate existing attachment
                existing_attachment.active = True
        else:
            # Create new attachment
            attachment = RuleAttachment(
                rule_id = rule_id,
                fund_id = fund_id,
                active = True
            )
            db.session.add(attachment)
        
        db.session.commit()
        
        logger.info(f"Attached rule {rule_id} to fund {fund_id}")
        return jsonify({
            'success': True,
            'message': 'Rule attached to fund successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to attach rule {rule_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rules_bp.route('/<int:rule_id>/attach/<int:fund_id>', methods = ['DELETE'])
def detach_rule_from_fund(rule_id, fund_id):
    """Detach a rule from a fund."""
    logger.debug(f"API: Detaching rule {rule_id} from fund {fund_id}")
    
    try:
        attachment = RuleAttachment.query.filter_by(
            rule_id = rule_id,
            fund_id = fund_id
        ).first()
        
        if not attachment:
            return jsonify({
                'success': False,
                'error': 'Rule is not attached to this fund'
            }), 404
        
        attachment.active = False
        db.session.commit()
        
        logger.info(f"Detached rule {rule_id} from fund {fund_id}")
        return jsonify({
            'success': True,
            'message': 'Rule detached from fund successfully'
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to detach rule {rule_id} from fund {fund_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rules_bp.route('/<int:fund_id>/compliance-check', methods = ['POST'])
def run_portfolio_compliance(fund_id):
    """Run portfolio compliance check for a fund."""
    logger.debug(f"API: Running portfolio compliance for fund {fund_id}")
    
    try:
        result = PortfolioComplianceService.run_portfolio_compliance(fund_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to run portfolio compliance for fund {fund_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
