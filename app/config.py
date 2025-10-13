"""
Application configuration settings.
"""

import os
from datetime import datetime, timezone, timedelta


class Config:
    """Base configuration class."""
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///compliance_system.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Timezone configuration (US Eastern - UTC-5 or UTC-4 depending on DST)
    # For simplicity, we'll use UTC-5 (EST) - in production you might want to handle DST
    TIMEZONE_OFFSET = timedelta(hours = -5)


def get_eastern_time():
    """Get current time in US Eastern timezone."""
    return datetime.now(timezone.utc) + Config.TIMEZONE_OFFSET
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')
    LOG_FILE = 'compliance_system.log'
    
    # API configuration
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = True


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    LOG_LEVEL = 'INFO'


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    LOG_LEVEL = 'WARNING'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
