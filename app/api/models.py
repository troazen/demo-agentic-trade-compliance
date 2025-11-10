"""
API models and schemas for Swagger documentation.
"""

from flask_restx import fields, Model
from app.api import api

# Common response models
success_response = Model('SuccessResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'message': fields.String(description = 'Success message')
})

error_response = Model('ErrorResponse', {
    'success': fields.Boolean(required = True, description = 'Always false for error responses'),
    'error': fields.String(required = True, description = 'Error message')
})

# Health check models
health_response = Model('HealthResponse', {
    'status': fields.String(required = True, description = 'Service status'),
    'message': fields.String(required = True, description = 'Service message')
})

# Fund models
fund_model = Model('Fund', {
    'fund_id': fields.Integer(required = True, description = 'Unique fund identifier'),
    'fund_name': fields.String(required = True, description = 'Name of the fund'),
    'cash': fields.Float(required = True, description = 'Cash amount in the fund'),
    'holdings_count': fields.Integer(description = 'Number of holdings'),
    'created_at': fields.DateTime(description = 'Fund creation timestamp'),
    'updated_at': fields.DateTime(description = 'Last update timestamp')
})

fund_with_holdings = Model('FundWithHoldings', {
    'fund_id': fields.Integer(required = True, description = 'Unique fund identifier'),
    'fund_name': fields.String(required = True, description = 'Name of the fund'),
    'cash': fields.Float(required = True, description = 'Cash amount in the fund'),
    'holdings': fields.List(fields.Raw, description = 'Fund holdings with market values'),
    'holdings_count': fields.Integer(description = 'Number of holdings'),
    'created_at': fields.DateTime(description = 'Fund creation timestamp'),
    'updated_at': fields.DateTime(description = 'Last update timestamp')
})

funds_list_response = Model('FundsListResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'funds': fields.List(fields.Nested(fund_model), description = 'List of funds'),
    'count': fields.Integer(description = 'Number of funds returned')
})

fund_response = Model('FundResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'fund': fields.Nested(fund_with_holdings, description = 'Fund details')
})

# Fund creation/update models
fund_create_request = Model('FundCreateRequest', {
    'fund_name': fields.String(required = True, description = 'Name of the fund to create'),
    'initial_cash': fields.Float(description = 'Initial cash amount (default: 0)')
})

fund_cash_update_request = Model('FundCashUpdateRequest', {
    'cash': fields.Float(required = True, description = 'New cash amount for the fund')
})

# Asset calculation models
total_assets_response = Model('TotalAssetsResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'fund_id': fields.Integer(required = True, description = 'Fund identifier'),
    'total_assets': fields.Float(description = 'Total assets value')
})

net_assets_response = Model('NetAssetsResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'fund_id': fields.Integer(required = True, description = 'Fund identifier'),
    'net_assets': fields.Float(description = 'Net assets value')
})

total_assets_ex_cash_response = Model('TotalAssetsExCashResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'fund_id': fields.Integer(required = True, description = 'Fund identifier'),
    'total_assets_ex_cash': fields.Float(description = 'Total assets excluding cash value')
})

# Security models
security_model = Model('Security', {
    'ticker': fields.String(required = True, description = 'Security ticker symbol'),
    'name': fields.String(description = 'Security name'),
    'type': fields.String(description = 'Security type'),
    'shares_outstanding': fields.Integer(description = 'Number of shares outstanding'),
    'market_cap': fields.Integer(description = 'Market capitalization'),
    'current_price': fields.Float(description = 'Current price'),
    'issuer': fields.Raw(description = 'Issuer information')
})

security_with_issuer = Model('SecurityWithIssuer', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'security': fields.Nested(security_model, description = 'Security details')
})

securities_list_response = Model('SecuritiesListResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'securities': fields.List(fields.Raw, description = 'List of securities'),
    'count': fields.Integer(description = 'Number of securities returned')
})

# Trade models
trade_model = Model('Trade', {
    'trade_id': fields.Integer(required = True, description = 'Unique trade identifier'),
    'fund_id': fields.Integer(required = True, description = 'Fund identifier'),
    'ticker': fields.String(required = True, description = 'Security ticker symbol'),
    'direction': fields.String(required = True, description = 'Trade direction (BUY or SELL)'),
    'shares': fields.Integer(required = True, description = 'Number of shares'),
    'price': fields.Float(description = 'Price per share'),
    'total_value': fields.Float(description = 'Total trade value'),
    'status': fields.String(description = 'Trade status'),
    'created_at': fields.DateTime(description = 'Trade creation timestamp')
})

trade_create_request = Model('TradeCreateRequest', {
    'fund_id': fields.Integer(required = True, description = 'Fund identifier'),
    'ticker': fields.String(required = True, description = 'Security ticker symbol'),
    'direction': fields.String(required = True, description = 'Trade direction (BUY or SELL)'),
    'shares': fields.Integer(required = True, description = 'Number of shares to trade')
})

trade_response = Model('TradeResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'trade': fields.Nested(trade_model, description = 'Trade details')
})

# Rule models
rule_model = Model('Rule', {
    'rule_id': fields.Integer(required = True, description = 'Unique rule identifier'),
    'rule_name': fields.String(required = True, description = 'Name of the compliance rule'),
    'alert_message': fields.String(description = 'Alert message for rule violations'),
    'logic': fields.String(description = 'SQL logic for the rule'),
    'denominator': fields.String(description = 'Rule denominator type'),
    'alert_if': fields.String(description = 'Alert condition (above/below)'),
    'alert_level': fields.Float(description = 'Alert threshold level'),
    'trade_compliance_mode': fields.Boolean(description = 'Whether rule runs on trades'),
    'portfolio_compliance_mode': fields.Boolean(description = 'Whether rule runs on portfolio'),
    'active': fields.Boolean(description = 'Whether rule is active'),
    'created_at': fields.DateTime(description = 'Rule creation timestamp'),
    'updated_at': fields.DateTime(description = 'Last update timestamp'),
    'attachments': fields.Raw(description = 'Fund attachments')
})

rule_create_request = Model('RuleCreateRequest', {
    'rule_name': fields.String(required = True, description = 'Name of the rule'),
    'alert_message': fields.String(required = True, description = 'Alert message'),
    'denominator': fields.String(required = True, description = 'Denominator type'),
    'logic': fields.String(description = 'SQL logic (optional)'),
    'alert_if': fields.String(description = 'Alert condition (above/below)'),
    'alert_level': fields.Float(description = 'Alert threshold level'),
    'trade_compliance_mode': fields.Boolean(description = 'Run on trades', default = True),
    'portfolio_compliance_mode': fields.Boolean(description = 'Run on portfolio', default = True)
})

rule_update_request = Model('RuleUpdateRequest', {
    'rule_name': fields.String(description = 'Name of the rule'),
    'alert_message': fields.String(description = 'Alert message'),
    'logic': fields.String(description = 'SQL logic'),
    'denominator': fields.String(description = 'Denominator type'),
    'alert_if': fields.String(description = 'Alert condition'),
    'alert_level': fields.Float(description = 'Alert threshold level'),
    'trade_compliance_mode': fields.Boolean(description = 'Run on trades'),
    'portfolio_compliance_mode': fields.Boolean(description = 'Run on portfolio')
})

rule_attach_request = Model('RuleAttachRequest', {
    'fund_ids': fields.List(fields.Integer, required = True, description = 'List of fund IDs to attach to')
})

rule_response = Model('RuleResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'rule': fields.Raw(description = 'Rule details')
})

rules_list_response = Model('RulesListResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'rules': fields.List(fields.Raw, description = 'List of compliance rules'),
    'count': fields.Integer(description = 'Number of rules returned')
})

# Alert models
alert_model = Model('Alert', {
    'alert_id': fields.Integer(required = True, description = 'Unique alert identifier'),
    'rule_id': fields.Integer(required = True, description = 'Rule that triggered the alert'),
    'fund_id': fields.Integer(required = True, description = 'Fund identifier'),
    'trade_id': fields.Integer(description = 'Trade identifier (if trade-related)'),
    'alert_message': fields.String(description = 'Alert message'),
    'calculated_percentage': fields.Float(description = 'Calculated percentage that triggered alert'),
    'status': fields.String(description = 'Alert status (pending/overridden/cancelled)'),
    'override_reason': fields.String(description = 'Override reason if applicable'),
    'created_at': fields.DateTime(description = 'Alert creation timestamp')
})

alert_override_request = Model('AlertOverrideRequest', {
    'reason': fields.String(required = True, description = 'Reason for overriding the alert')
})

alert_response = Model('AlertResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'alert': fields.Raw(description = 'Alert details')
})

alerts_list_response = Model('AlertsListResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'alerts': fields.List(fields.Raw, description = 'List of alerts'),
    'count': fields.Integer(description = 'Number of alerts returned')
})

# Register all models with the API
api.models[success_response.name] = success_response
api.models[error_response.name] = error_response
api.models[health_response.name] = health_response
api.models[fund_model.name] = fund_model
api.models[fund_with_holdings.name] = fund_with_holdings
api.models[funds_list_response.name] = funds_list_response
api.models[fund_response.name] = fund_response
api.models[fund_create_request.name] = fund_create_request
api.models[fund_cash_update_request.name] = fund_cash_update_request
api.models[total_assets_response.name] = total_assets_response
api.models[net_assets_response.name] = net_assets_response
api.models[total_assets_ex_cash_response.name] = total_assets_ex_cash_response
api.models[security_model.name] = security_model
api.models[security_with_issuer.name] = security_with_issuer
securities_list_response = api.models[securities_list_response.name] = securities_list_response
api.models[trade_model.name] = trade_model
api.models[trade_create_request.name] = trade_create_request
api.models[trade_response.name] = trade_response
trades_list_response = Model('TradesListResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'trades': fields.List(fields.Raw, description = 'List of trades'),
    'count': fields.Integer(description = 'Number of trades returned')
})
api.models[rule_model.name] = rule_model
api.models[rule_create_request.name] = rule_create_request
api.models[rule_update_request.name] = rule_update_request
api.models[rule_attach_request.name] = rule_attach_request
api.models[rule_response.name] = rule_response
api.models[rules_list_response.name] = rules_list_response
api.models[alert_model.name] = alert_model
api.models[alert_override_request.name] = alert_override_request
api.models[alert_response.name] = alert_response
api.models[alerts_list_response.name] = alerts_list_response

# Holdings models
holdings_list_response = Model('HoldingsListResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'holdings': fields.List(fields.Raw, description = 'List of holdings'),
    'count': fields.Integer(description = 'Number of holdings returned')
})

fund_holdings_response = Model('FundHoldingsResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'fund': fields.Raw(description = 'Fund details'),
    'holdings': fields.List(fields.Raw, description = 'List of holdings'),
    'holdings_count': fields.Integer(description = 'Number of holdings')
})

# Compliance check response model (first definition - will be replaced)

# Rule test models
rule_test_request = Model('RuleTestRequest', {
    'fund_id': fields.Integer(required = True, description = 'Fund ID to test against'),
    'test_trade': fields.Raw(description = 'Optional test trade details {ticker, direction, shares}')
})

rule_test_response = Model('RuleTestResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'rule_id': fields.Integer(description = 'Rule ID'),
    'rule_name': fields.String(description = 'Rule name'),
    'fund_id': fields.Integer(description = 'Fund ID'),
    'test_type': fields.String(description = 'Type of test (portfolio or trade)'),
    'would_alert': fields.Boolean(description = 'Whether the rule would alert'),
    'calculated_percentage': fields.Float(description = 'Calculated percentage'),
    'alert_level': fields.Float(description = 'Alert threshold level'),
    'alert_if': fields.String(description = 'Alert condition'),
    'alert_message': fields.String(description = 'Alert message'),
    'holdings_triggered': fields.Raw(description = 'Holdings that triggered the alert'),
    'test_trade_details': fields.Raw(description = 'Test trade details if applicable')
})

# Compliance check response model
compliance_check_response = Model('ComplianceCheckResponse', {
    'success': fields.Boolean(required = True, description = 'Indicates if the request was successful'),
    'fund_id': fields.Integer(description = 'Fund ID'),
    'fund_name': fields.String(description = 'Fund name'),
    'rules_checked': fields.Integer(description = 'Number of rules checked'),
    'alerts': fields.List(fields.Raw, description = 'List of alerts'),
    'alerts_count': fields.Integer(description = 'Number of alerts'),
    'alerted': fields.Boolean(description = 'Whether any alerts were generated'),
    'message': fields.String(description = 'Result message')
})

# Register additional models
api.models[holdings_list_response.name] = holdings_list_response
api.models[fund_holdings_response.name] = fund_holdings_response
api.models[compliance_check_response.name] = compliance_check_response
api.models[rule_test_request.name] = rule_test_request
api.models[rule_test_response.name] = rule_test_response
