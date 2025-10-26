"""
Formatting utility functions for displaying data.
"""

from typing import Optional, Union
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def format_currency(value: Optional[Union[float, Decimal, str]]) -> str:
    """
    Format a numeric value as currency.
    
    Args:
        value: Numeric value to format
        
    Returns:
        Formatted string (e.g., "$1,234.56")
    """
    if value is None or value == "":
        return "-"
    
    try:
        if isinstance(value, str):
            value = float(value)
        
        # Handle very large or very small numbers
        if abs(float(value)) >= 1e9:
            return f"${value / 1e9:.2f}B"
        elif abs(float(value)) >= 1e6:
            return f"${value / 1e6:.2f}M"
        elif abs(float(value)) >= 1e3:
            return f"${value / 1e3:.2f}K"
        else:
            return f"${value:,.2f}"
    except (ValueError, TypeError):
        logger.warning(f"Could not format currency value: {value}")
        return "-"


def format_percentage(value: Optional[Union[float, Decimal, str]]) -> str:
    """
    Format a numeric value as percentage.
    
    Args:
        value: Numeric value to format (assumed to be in decimal form, e.g., 0.1234 for 12.34%)
        
    Returns:
        Formatted string (e.g., "12.34%")
    """
    if value is None or value == "":
        return "-"
    
    try:
        if isinstance(value, str):
            value = float(value)
        
        return f"{value:.2f}%"
    except (ValueError, TypeError):
        logger.warning(f"Could not format percentage value: {value}")
        return "-"


def format_datetime(dt_string: Optional[str]) -> str:
    """
    Format a datetime string to user-friendly format.
    
    Args:
        dt_string: ISO format datetime string
        
    Returns:
        Formatted string (e.g., "2025-10-26 3:45 PM ET")
    """
    if not dt_string:
        return "-"
    
    try:
        from datetime import datetime
        
        # Parse ISO format datetime
        if 'T' in dt_string:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
        
        # Format as "YYYY-MM-DD HH:MM AM/PM ET"
        date_str = dt.strftime('%Y-%m-%d')
        time_str = dt.strftime('%-I:%M %p')
        
        return f"{date_str} {time_str} ET"
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not format datetime: {dt_string}, error: {e}")
        return dt_string


def format_shares(value: Optional[Union[int, float, Decimal, str]]) -> str:
    """
    Format a numeric value as number of shares.
    
    Args:
        value: Numeric value to format
        
    Returns:
        Formatted string (e.g., "1,234")
    """
    if value is None or value == "":
        return "-"
    
    try:
        if isinstance(value, str):
            value = float(value)
        
        return f"{int(value):,}"
    except (ValueError, TypeError):
        logger.warning(f"Could not format shares value: {value}")
        return "-"


def format_status(status: Optional[str]) -> str:
    """
    Format a status string with proper capitalization.
    
    Args:
        status: Status string (e.g., "processed", "alert", etc.)
        
    Returns:
        Capitalized status string
    """
    if not status:
        return "-"
    
    return status.replace('_', ' ').title()


def format_boolean(value: Optional[bool]) -> str:
    """
    Format a boolean value as Yes/No.
    
    Args:
        value: Boolean value
        
    Returns:
        "Yes" or "No"
    """
    if value is None:
        return "-"
    return "Yes" if value else "No"

