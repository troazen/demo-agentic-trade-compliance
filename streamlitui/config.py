"""
Configuration settings for the Streamlit UI.
"""

import os
import logging

# API Configuration
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5000')
API_TIMEOUT = 30  # seconds

# Application Configuration
PAGE_TITLE = "Investment Operations Compliance System"
PAGE_ICON = "📊"
LAYOUT = "wide"

# Theme Configuration (dark theme)
STREAMLIT_THEME = {
    "theme": {
        "primaryColor": "#1e90ff",
        "backgroundColor": "#0e1117",
        "secondaryBackgroundColor": "#262730",
        "textColor": "#fafafa"
    }
}

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

# Set up logger
logger = logging.getLogger(__name__)

