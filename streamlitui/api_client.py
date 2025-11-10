"""
API client wrapper for backend API communication.
"""

import requests
import logging
from typing import Optional, Dict, Any, List
from streamlitui.config import API_BASE_URL, API_TIMEOUT

logger = logging.getLogger(__name__)


class APIClient:
    """Client for interacting with the backend API."""
    
    def __init__(self):
        self.base_url = API_BASE_URL
        self.timeout = API_TIMEOUT
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the API.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            json_data: JSON request body
            
        Returns:
            Response data as dictionary
            
        Raises:
            Exception: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            logger.debug(f"{method} {url}")
            response = requests.request(
                method = method,
                url = url,
                params = params,
                json = json_data,
                timeout = self.timeout
            )
            
            # Handle HTTP errors
            # Special case: 403 means trade created but has compliance alerts (per PRD)
            if response.status_code == 403:
                try:
                    return response.json()
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"API 403 response but could not parse JSON: {error_msg}")
                    raise Exception(error_msg)
            
            if response.status_code >= 400:
                try:
                    error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                    error_msg = error_data.get('error', f"HTTP {response.status_code}")
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"API error {response.status_code}: {error_msg}")
                raise Exception(error_msg)
            
            return response.json()
        except requests.exceptions.ConnectionError:
            logger.error("Cannot connect to backend API")
            raise Exception("Cannot connect to backend API. Please ensure the server is running.")
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            raise Exception("Request timeout. Please try again.")
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise
    
    # ========== Funds API ==========
    
    def get_funds(self) -> List[Dict[str, Any]]:
        """Get all funds."""
        response = self._make_request('GET', '/api/funds/')
        return response.get('funds', [])
    
    def get_fund(self, fund_id: int) -> Optional[Dict[str, Any]]:
        """Get fund details with holdings."""
        try:
            response = self._make_request('GET', f'/api/funds/{fund_id}')
            fund = response.get('fund')
            return fund if fund else None
        except Exception as e:
            logger.warning(f"Failed to get fund {fund_id}: {e}")
            return None
    
    def update_fund_cash(self, fund_id: int, cash: float) -> bool:
        """Update fund cash amount."""
        response = self._make_request('PUT', f'/api/funds/{fund_id}/cash', json_data = {'cash': cash})
        return response.get('success', False)
    
    def run_compliance_check(self, fund_id: int) -> Dict[str, Any]:
        """Run portfolio compliance check for a fund."""
        response = self._make_request('POST', f'/api/funds/{fund_id}/compliance-check')
        return response
    
    # ========== Securities API ==========
    
    def get_securities(self, search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all securities or search securities."""
        params = {}
        if search_query:
            params['q'] = search_query
        
        response = self._make_request('GET', '/api/securities/', params = params)
        return response.get('securities', [])
    
    def search_securities(self, query: str) -> List[Dict[str, Any]]:
        """Search securities by ticker or issuer name."""
        response = self._make_request('GET', '/api/securities/search', params = {'q': query})
        return response.get('securities', [])
    
    def get_security(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get security details by ticker."""
        try:
            response = self._make_request('GET', f'/api/securities/{ticker}')
            security = response.get('security')
            return security if security else None
        except Exception as e:
            logger.warning(f"Failed to get security {ticker}: {e}")
            return None
    
    def get_security_price(self, ticker: str) -> float:
        """Get current price for a security."""
        response = self._make_request('GET', f'/api/securities/{ticker}/price')
        return response.get('price')
    
    # ========== Trades API ==========
    
    def create_trade(
        self, 
        fund_id: int, 
        ticker: str, 
        direction: str, 
        shares: int
    ) -> Dict[str, Any]:
        """Create and submit a new trade."""
        response = self._make_request(
            'POST',
            '/api/trades/',
            json_data = {
                'fund_id': fund_id,
                'ticker': ticker,
                'direction': direction,
                'shares': shares
            }
        )
        return response
    
    def get_trade(self, trade_id: int) -> Optional[Dict[str, Any]]:
        """Get trade details by ID."""
        try:
            response = self._make_request('GET', f'/api/trades/{trade_id}')
            trade = response.get('trade')
            return trade if trade else None
        except Exception as e:
            logger.warning(f"Failed to get trade {trade_id}: {e}")
            return None
    
    def override_trade(self, trade_id: int, alerts: Dict[int, Dict[str, str]]) -> bool:
        """Override trade alerts and proceed."""
        response = self._make_request(
            'POST',
            f'/api/trades/{trade_id}/override',
            json_data = {'alerts': alerts}
        )
        return response.get('success', False)
    
    def cancel_trade(self, trade_id: int) -> bool:
        """Cancel a trade."""
        response = self._make_request('POST', f'/api/trades/{trade_id}/cancel')
        return response.get('success', False)
    
    def get_trades_for_fund(self, fund_id: int) -> List[Dict[str, Any]]:
        """Get all trades for a specific fund."""
        response = self._make_request('GET', f'/api/trades/fund/{fund_id}')
        return response.get('trades', [])
    
    # ========== Rules API ==========
    
    def get_rules(
        self, 
        fund_id: Optional[int] = None, 
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all rules with optional filters."""
        params = {}
        if fund_id:
            params['fund_id'] = fund_id
        if search_query:
            params['q'] = search_query
        
        response = self._make_request('GET', '/api/rules/', params = params)
        return response.get('rules', [])
    
    def get_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        """Get rule details including attachments."""
        try:
            response = self._make_request('GET', f'/api/rules/{rule_id}')
            logger.debug(f"API response for rule {rule_id}: {response}")
            rule = response.get('rule')
            if not rule:
                logger.warning(f"No rule data in response for rule {rule_id}. Response: {response}")
            return rule if rule else None
        except Exception as e:
            logger.error(f"Failed to get rule {rule_id}: {e}", exc_info = True)
            return None
    
    def create_rule(
        self,
        rule_name: str,
        alert_message: str,
        denominator: str,
        logic: Optional[str] = None,
        alert_if: Optional[str] = None,
        alert_level: Optional[float] = None,
        trade_compliance_mode: bool = True,
        portfolio_compliance_mode: bool = True
    ) -> Dict[str, Any]:
        """Create a new compliance rule."""
        response = self._make_request(
            'POST',
            '/api/rules/',
            json_data = {
                'rule_name': rule_name,
                'alert_message': alert_message,
                'denominator': denominator,
                'logic': logic,
                'alert_if': alert_if,
                'alert_level': alert_level,
                'trade_compliance_mode': trade_compliance_mode,
                'portfolio_compliance_mode': portfolio_compliance_mode
            }
        )
        return response.get('rule')
    
    def update_rule(
        self,
        rule_id: int,
        rule_name: Optional[str] = None,
        alert_message: Optional[str] = None,
        logic: Optional[str] = None,
        denominator: Optional[str] = None,
        alert_if: Optional[str] = None,
        alert_level: Optional[float] = None,
        trade_compliance_mode: Optional[bool] = None,
        portfolio_compliance_mode: Optional[bool] = None
    ) -> bool:
        """Update an existing rule."""
        data = {}
        if rule_name is not None:
            data['rule_name'] = rule_name
        if alert_message is not None:
            data['alert_message'] = alert_message
        if logic is not None:
            data['logic'] = logic
        if denominator is not None:
            data['denominator'] = denominator
        if alert_if is not None:
            data['alert_if'] = alert_if
        if alert_level is not None:
            data['alert_level'] = alert_level
        if trade_compliance_mode is not None:
            data['trade_compliance_mode'] = trade_compliance_mode
        if portfolio_compliance_mode is not None:
            data['portfolio_compliance_mode'] = portfolio_compliance_mode
        
        response = self._make_request('PUT', f'/api/rules/{rule_id}', json_data = data)
        return response.get('success', False)
    
    def delete_rule(self, rule_id: int) -> bool:
        """Deactivate a rule."""
        response = self._make_request('DELETE', f'/api/rules/{rule_id}')
        return response.get('success', False)
    
    def activate_rule(self, rule_id: int) -> bool:
        """Activate a rule."""
        response = self._make_request('POST', f'/api/rules/{rule_id}/activate')
        return response.get('success', False)
    
    def deactivate_rule(self, rule_id: int) -> bool:
        """Deactivate a rule."""
        response = self._make_request('POST', f'/api/rules/{rule_id}/deactivate')
        return response.get('success', False)
    
    def attach_rule_to_funds(self, rule_id: int, fund_ids: List[int]) -> List[int]:
        """Attach a rule to one or more funds."""
        response = self._make_request(
            'POST',
            f'/api/rules/{rule_id}/attach',
            json_data = {'fund_ids': fund_ids}
        )
        return response.get('attached_funds', [])
    
    def detach_rule_from_funds(self, rule_id: int, fund_ids: List[int]) -> List[int]:
        """Detach a rule from one or more funds."""
        response = self._make_request(
            'POST',
            f'/api/rules/{rule_id}/detach',
            json_data = {'fund_ids': fund_ids}
        )
        return response.get('detached_funds', [])
    
    def validate_rule_logic(self, logic: str) -> Dict[str, Any]:
        """Validate rule SQL logic."""
        response = self._make_request(
            'POST',
            '/api/rules/validate-logic',
            json_data = {'logic': logic}
        )
        return response
    
    def check_rule_name(self, rule_name: str, exclude_rule_id: Optional[int] = None) -> Dict[str, Any]:
        """Check if a rule name is available."""
        data = {'rule_name': rule_name}
        if exclude_rule_id:
            data['exclude_rule_id'] = exclude_rule_id
        
        response = self._make_request(
            'POST',
            '/api/rules/check-name',
            json_data = data
        )
        return response
    
    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema information for rule writing."""
        response = self._make_request('GET', '/api/rules/schema')
        return response
    
    def test_rule(
        self,
        rule_id: int,
        fund_id: int,
        test_trade: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Test a rule against a fund with optional simulated trade."""
        response = self._make_request(
            'POST',
            f'/api/rules/{rule_id}/test',
            json_data = {
                'fund_id': fund_id,
                'test_trade': test_trade
            }
        )
        return response
    
    # ========== Alerts API ==========
    
    def get_alerts(
        self,
        fund_id: Optional[int] = None,
        rule_id: Optional[int] = None,
        trade_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get alerts with optional filters."""
        params = {}
        if fund_id:
            params['fund_id'] = fund_id
        if rule_id:
            params['rule_id'] = rule_id
        if trade_id:
            params['trade_id'] = trade_id
        if status:
            params['status'] = status
        if limit:
            params['limit'] = limit
        
        response = self._make_request('GET', '/api/alerts/', params = params)
        return response.get('alerts', [])
    
    def get_alert(self, alert_id: int) -> Optional[Dict[str, Any]]:
        """Get alert details by ID."""
        try:
            response = self._make_request('GET', f'/api/alerts/{alert_id}')
            alert = response.get('alert')
            return alert if alert else None
        except Exception as e:
            logger.warning(f"Failed to get alert {alert_id}: {e}")
            return None
    
    def override_alert(self, alert_id: int, reason: str) -> bool:
        """Override alert with reason."""
        response = self._make_request(
            'PUT',
            f'/api/alerts/{alert_id}/override',
            json_data = {'reason': reason}
        )
        return response.get('success', False)
    
    def cancel_alert(self, alert_id: int) -> bool:
        """Cancel alert."""
        response = self._make_request('PUT', f'/api/alerts/{alert_id}/cancel')
        return response.get('success', False)
    
    def get_alerts_summary(self, fund_id: Optional[int] = None) -> Dict[str, Any]:
        """Get alert summary statistics."""
        params = {}
        if fund_id:
            params['fund_id'] = fund_id
        
        response = self._make_request('GET', '/api/alerts/summary', params = params)
        return response.get('summary')


# Create global API client instance
api_client = APIClient()

