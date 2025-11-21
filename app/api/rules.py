"""
Rules API endpoints with Flask-RESTX for Swagger documentation.
"""

from flask import request
from flask_restx import Namespace, Resource
import logging

from app.services.rule_service import RuleService
from app.services.schema_service import SchemaService
from app.api.models import (
    rules_list_response, success_response, rule_response,
    rule_create_request, rule_update_request, rule_attach_request,
    rule_test_request, rule_validate_logic_request, rule_check_name_request
)

logger = logging.getLogger(__name__)

# Create namespace for rules
rules_ns = Namespace('rules', description = 'Compliance rules management operations')


@rules_ns.route('/')
class RulesList(Resource):
    @rules_ns.doc('get_rules')
    @rules_ns.marshal_with(rules_list_response)
    @rules_ns.param('fund_id', 'Filter by fund ID attachment')
    @rules_ns.param('q', 'Search query for rule name')
    def get(self):
        """Get all compliance rules with optional filters."""
        logger.debug("API: Getting all rules")
        
        try:
            fund_id = request.args.get('fund_id', type = int)
            search_query = request.args.get('q')
            
            rules = RuleService.get_all_rules(fund_id = fund_id, search_query = search_query)
            
            result = []
            for rule in rules:
                rule_data = rule.to_dict()
                
                # Add attached funds (only active attachments)
                from sqlalchemy.orm import joinedload
                from app.models import RuleAttachment
                attachments = RuleAttachment.query.options(joinedload(RuleAttachment.fund)).filter_by(rule_id = rule.rule_id).all()
                attached_funds = []
                for att in attachments:
                    if att.active and att.fund:
                        attached_funds.append({
                            'fund_id': att.fund_id,
                            'fund_name': att.fund.fund_name
                        })
                rule_data['attached_funds'] = attached_funds
                
                result.append(rule_data)
            
            return {
                'success': True,
                'rules': result,
                'count': len(result)
            }
        except Exception as e:
            logger.error(f"Failed to get rules: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @rules_ns.doc('create_rule')
    @rules_ns.expect(rule_create_request)
    @rules_ns.marshal_with(rule_response)
    def post(self):
        """Create a new compliance rule."""
        logger.debug("API: Creating new rule")
        
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'error': 'Request body is required'
                }, 400
            
            # Validate required fields
            required_fields = ['rule_name', 'alert_message', 'denominator']
            for field in required_fields:
                if field not in data:
                    return {
                        'success': False,
                        'error': f'{field} is required'
                    }, 400
            
            result = RuleService.create_rule(
                rule_name = data['rule_name'],
                alert_message = data['alert_message'],
                denominator = data['denominator'],
                logic = data.get('logic'),
                alert_if = data.get('alert_if'),
                alert_level = data.get('alert_level'),
                trade_compliance_mode = data.get('trade_compliance_mode', True),
                portfolio_compliance_mode = data.get('portfolio_compliance_mode', True)
            )
            
            if not result.get('success', False):
                error_msg = result.get('error', 'Failed to create rule')
                logger.error(f"Rule creation failed: {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }, 400
            
            rule = result.get('rule')
            if not rule:
                return {
                    'success': False,
                    'error': 'Failed to create rule - no rule object returned'
                }, 500
            
            rule_data = rule.to_dict()
            
            return {
                'success': True,
                'message': 'Rule created successfully',
                'rule': rule_data
            }, 201
        except Exception as e:
            logger.error(f"Failed to create rule: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@rules_ns.route('/<int:rule_id>')
class RuleDetail(Resource):
    @rules_ns.doc('get_rule')
    @rules_ns.marshal_with(rule_response)
    def get(self, rule_id):
        """Get rule details by ID including fund attachments."""
        logger.debug(f"API: Getting rule {rule_id}")
        
        try:
            rule_data = RuleService.get_rule_with_attachments(rule_id)
            
            if not rule_data:
                return {
                    'success': False,
                    'error': 'Rule not found'
                }, 404
            
            return {
                'success': True,
                'rule': rule_data
            }
        except Exception as e:
            logger.error(f"Failed to get rule {rule_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @rules_ns.doc('update_rule')
    @rules_ns.expect(rule_update_request)
    @rules_ns.marshal_with(success_response)
    def put(self, rule_id):
        """Update an existing rule."""
        logger.debug(f"API: Updating rule {rule_id}")
        
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'error': 'Request body is required'
                }, 400
            
            rule = RuleService.update_rule(
                rule_id = rule_id,
                rule_name = data.get('rule_name'),
                alert_message = data.get('alert_message'),
                logic = data.get('logic'),
                denominator = data.get('denominator'),
                alert_if = data.get('alert_if'),
                alert_level = data.get('alert_level'),
                trade_compliance_mode = data.get('trade_compliance_mode'),
                portfolio_compliance_mode = data.get('portfolio_compliance_mode')
            )
            
            if not rule:
                return {
                    'success': False,
                    'error': 'Failed to update rule'
                }, 500
            
            return {
                'success': True,
                'message': 'Rule updated successfully'
            }
        except Exception as e:
            logger.error(f"Failed to update rule {rule_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500
    
    @rules_ns.doc('delete_rule')
    @rules_ns.marshal_with(success_response)
    def delete(self, rule_id):
        """Deactivate a rule."""
        logger.debug(f"API: Deactivating rule {rule_id}")
        
        try:
            success = RuleService.deactivate_rule(rule_id)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to deactivate rule'
                }, 500
            
            return {
                'success': True,
                'message': 'Rule deactivated successfully'
            }
        except Exception as e:
            logger.error(f"Failed to deactivate rule {rule_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@rules_ns.route('/<int:rule_id>/activate')
class RuleActivate(Resource):
    @rules_ns.doc('activate_rule')
    @rules_ns.marshal_with(success_response)
    def post(self, rule_id):
        """Activate a rule."""
        logger.debug(f"API: Activating rule {rule_id}")
        
        try:
            success = RuleService.activate_rule(rule_id)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to activate rule'
                }, 500
            
            return {
                'success': True,
                'message': 'Rule activated successfully'
            }
        except Exception as e:
            logger.error(f"Failed to activate rule {rule_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@rules_ns.route('/<int:rule_id>/deactivate')
class RuleDeactivate(Resource):
    @rules_ns.doc('deactivate_rule')
    @rules_ns.marshal_with(success_response)
    def post(self, rule_id):
        """Deactivate a rule."""
        logger.debug(f"API: Deactivating rule {rule_id}")
        
        try:
            success = RuleService.deactivate_rule(rule_id)
            
            if not success:
                return {
                    'success': False,
                    'error': 'Failed to deactivate rule'
                }, 500
            
            return {
                'success': True,
                'message': 'Rule deactivated successfully'
            }
        except Exception as e:
            logger.error(f"Failed to deactivate rule {rule_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@rules_ns.route('/<int:rule_id>/attach')
class RuleAttach(Resource):
    @rules_ns.doc('attach_rule_to_fund')
    @rules_ns.expect(rule_attach_request)
    @rules_ns.marshal_with(success_response)
    def post(self, rule_id):
        """Attach a rule to one or more funds."""
        logger.debug(f"API: Attaching rule {rule_id} to funds")
        
        try:
            data = request.get_json()
            if not data or 'fund_ids' not in data:
                return {
                    'success': False,
                    'error': 'fund_ids array is required'
                }, 400
            
            fund_ids = data['fund_ids']
            if not isinstance(fund_ids, list) or len(fund_ids) == 0:
                return {
                    'success': False,
                    'error': 'fund_ids must be a non-empty array'
                }, 400
            
            attached = []
            for fund_id in fund_ids:
                success = RuleService.attach_rule_to_fund(rule_id, fund_id)
                if success:
                    attached.append(fund_id)
            
            if len(attached) == 0:
                return {
                    'success': False,
                    'error': 'Failed to attach rule to any funds'
                }, 500
            
            return {
                'success': True,
                'message': f'Rule attached to {len(attached)} fund(s)',
                'attached_funds': attached
            }
        except Exception as e:
            logger.error(f"Failed to attach rule {rule_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@rules_ns.route('/<int:rule_id>/detach')
class RuleDetach(Resource):
    @rules_ns.doc('detach_rule_from_fund')
    @rules_ns.expect(rule_attach_request)
    @rules_ns.marshal_with(success_response)
    def post(self, rule_id):
        """Detach a rule from one or more funds."""
        logger.debug(f"API: Detaching rule {rule_id} from funds")
        
        try:
            data = request.get_json()
            if not data or 'fund_ids' not in data:
                return {
                    'success': False,
                    'error': 'fund_ids array is required'
                }, 400
            
            fund_ids = data['fund_ids']
            if not isinstance(fund_ids, list) or len(fund_ids) == 0:
                return {
                    'success': False,
                    'error': 'fund_ids must be a non-empty array'
                }, 400
            
            detached = []
            for fund_id in fund_ids:
                success = RuleService.detach_rule_from_fund(rule_id, fund_id)
                if success:
                    detached.append(fund_id)
            
            if len(detached) == 0:
                return {
                    'success': False,
                    'error': 'Failed to detach rule from any funds'
                }, 500
            
            return {
                'success': True,
                'message': f'Rule detached from {len(detached)} fund(s)',
                'detached_funds': detached
            }
        except Exception as e:
            logger.error(f"Failed to detach rule {rule_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500


@rules_ns.route('/validate-logic')
class RuleValidateLogic(Resource):
    @rules_ns.doc('validate_rule_logic')
    @rules_ns.expect(rule_validate_logic_request)
    def post(self):
        """Validate rule SQL logic."""
        logger.debug("API: Validating rule logic")
        
        try:
            data = request.get_json()
            if not data or 'logic' not in data:
                return {
                    'success': False,
                    'valid': False,
                    'error': 'logic field is required'
                }, 400
            
            logic = data['logic']
            validation = RuleService.validate_rule_logic(logic)
            
            # Return full validation result without marshalling to preserve error field
            return {
                'success': validation.get('valid', False),
                'valid': validation.get('valid', False),
                'error': validation.get('error')
            }
        except Exception as e:
            logger.error(f"Failed to validate logic: {e}", exc_info = True)
            return {
                'success': False,
                'valid': False,
                'error': str(e)
            }, 500


@rules_ns.route('/check-name')
class RuleCheckName(Resource):
    @rules_ns.doc('check_rule_name')
    @rules_ns.expect(rule_check_name_request)
    def post(self):
        """Check if a rule name is available."""
        logger.debug("API: Checking rule name availability")
        
        try:
            data = request.get_json()
            if not data or 'rule_name' not in data:
                return {
                    'success': False,
                    'available': False,
                    'error': 'rule_name field is required'
                }, 400
            
            rule_name = data.get('rule_name', '').strip()
            exclude_rule_id = data.get('exclude_rule_id')  # For edit mode - exclude current rule
            
            if not rule_name:
                return {
                    'success': True,
                    'available': False,
                    'message': 'Rule name cannot be empty'
                }
            
            # Check if rule name exists
            existing_rule = RuleService.get_rule_by_name(rule_name)
            
            if existing_rule and (not exclude_rule_id or existing_rule.rule_id != exclude_rule_id):
                return {
                    'success': True,
                    'available': False,
                    'message': f"Rule name already exists as rule {existing_rule.rule_id}",
                    'existing_rule_id': existing_rule.rule_id
                }
            
            return {
                'success': True,
                'available': True,
                'message': 'Rule name is available'
            }
        except Exception as e:
            logger.error(f"Failed to check rule name: {e}")
            return {
                'success': False,
                'available': False,
                'error': str(e)
            }, 500


@rules_ns.route('/schema')
class RuleSchema(Resource):
    @rules_ns.doc('get_database_schema')
    def get(self):
        """Get database schema information for rule writing."""
        logger.debug("API: Getting database schema")
        
        try:
            schema = SchemaService.get_database_schema()
            schema_dataframe = SchemaService.get_schema_dataframe()
            
            return {
                'success': True,
                'schema': schema,
                'schema_dataframe': schema_dataframe
            }
        except Exception as e:
            logger.error(f"Failed to get database schema: {e}", exc_info = True)
            return {
                'success': False,
                'error': str(e)
            }, 500


@rules_ns.route('/<int:rule_id>/test')
class RuleTest(Resource):
    @rules_ns.doc('test_rule')
    @rules_ns.expect(rule_test_request)
    @rules_ns.marshal_with(success_response)
    def post(self, rule_id):
        """Test a rule against a fund with optional simulated trade."""
        logger.debug(f"API: Testing rule {rule_id}")
        
        try:
            data = request.get_json()
            if not data:
                return {
                    'success': False,
                    'error': 'Request body is required'
                }, 400
            
            if 'fund_id' not in data:
                return {
                    'success': False,
                    'error': 'fund_id is required'
                }, 400
            
            fund_id = data['fund_id']
            test_trade = data.get('test_trade')
            
            # Test the rule
            result = RuleService.test_rule(rule_id, fund_id, test_trade)
            
            if not result.get('success', False):
                return {
                    'success': False,
                    'error': result.get('error', 'Rule test failed')
                }, 500
            
            return result
        except Exception as e:
            logger.error(f"Failed to test rule {rule_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }, 500