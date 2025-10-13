"""
Main application entry point for the Investment Operations Compliance System.
"""

import os
import sys
import logging
from flask import Flask

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.config import config

# Set up logging
logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers = [
        logging.FileHandler('compliance_system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main application entry point."""
    logger.info("Starting Investment Operations Compliance System")
    
    # Get configuration from environment
    config_name = os.environ.get('FLASK_ENV', 'development')
    logger.info(f"Using configuration: {config_name}")
    
    # Create Flask application
    app = create_app(config[config_name])
    
    # Get configuration
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Starting server on {host}:{port} (debug={debug})")
    
    # Run the application
    app.run(host = host, port = port, debug = debug)


if __name__ == '__main__':
    main()
