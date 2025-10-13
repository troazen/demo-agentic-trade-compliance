"""
Application constants and enumerations.
"""

from enum import Enum


class TradeStatus(Enum):
    """Trade status enumeration."""
    SUBMITTED = 'submitted'
    VALIDATING = 'validating'
    INVALID = 'invalid'
    COMPLIANCE = 'compliance'
    ALERT = 'alert'
    CANCELLED = 'cancelled'
    PROCESSED = 'processed'


class TradeDirection(Enum):
    """Trade direction enumeration."""
    BUY = 'BUY'
    SELL = 'SELL'


class AlertStatus(Enum):
    """Alert status enumeration."""
    PENDING = 'pending'
    OVERRIDDEN = 'overridden'
    CANCELLED = 'cancelled'


class AlertIf(Enum):
    """Alert condition enumeration."""
    ABOVE = 'above'
    BELOW = 'below'


class DenominatorType(Enum):
    """Compliance rule denominator types."""
    TOTAL_ASSETS = 'total_assets'
    NET_ASSETS = 'net_assets'
    TOTAL_ASSETS_EX_CASH = 'total_assets_ex_cash'
    PROHIBIT = 'prohibit'
    SHARES_OUTSTANDING_FE = 'shares_outstanding_fe'


# SQL keywords to block in rule logic
BLOCKED_SQL_KEYWORDS = [
    'DROP', 'INSERT', 'ALTER', 'UPDATE', 'DELETE', 'SELECT'
]

# Default rule logic for empty/null logic
DEFAULT_RULE_LOGIC = '1=1'

# Price decimal places
PRICE_DECIMAL_PLACES = 3

# Minimum shares for trade
MIN_TRADE_SHARES = 1
