"""
Investment Operations Compliance System - Flask Application Factory
"""

import logging
from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.models import db


def create_app(config_class = Config) -> Flask:
    """
    Create and configure Flask application instance.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize database
    db.init_app(app)
    
    # Enable CORS for Streamlit frontend
    CORS(app)
    
    # Configure logging
    logging.basicConfig(
        level = logging.DEBUG,
        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers = [
            logging.FileHandler('compliance_system.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Register API with Flask-RESTX
    from app.api import api
    api.init_app(app)
    
    # Create tables and check for auto-initialization
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified")
        
        # Check if database should be auto-initialized
        auto_init = getattr(config_class, 'AUTO_INITIALIZE_DB', False)
        
        if auto_init:
            # Check if database is empty
            from app.models import Fund
            
            fund_count = Fund.query.count()
            is_empty = fund_count == 0
            
            if is_empty:
                logger.info("Database appears to be empty, running automatic initialization...")
                try:
                    # Import and run the seed script
                    import sys
                    import os
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                    
                    from scripts.seed_data import main as seed_main
                    seed_main()
                    logger.info("Database auto-initialization completed successfully")
                except Exception as e:
                    logger.error(f"Database auto-initialization failed: {e}")
                    logger.error("Application will continue with empty database")
    
    return app
