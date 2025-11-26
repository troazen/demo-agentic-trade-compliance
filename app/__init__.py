"""
Investment Operations Compliance System - Flask Application Factory
"""

import os
import logging
from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.models import db


def create_app(config_class = Config, skip_auto_init = False) -> Flask:
    """
    Create and configure Flask application instance.
    
    Args:
        config_class: Configuration class to use
        skip_auto_init: If True, skip automatic database initialization (prevents infinite loops)
        
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize database
    db.init_app(app)
    
    # Enable CORS for Streamlit frontend
    CORS(app)
    
    # Configure logging - respect LOG_LEVEL from config or environment
    log_level = getattr(config_class, 'LOG_LEVEL', os.environ.get('LOG_LEVEL', 'INFO')).upper()
    logging.basicConfig(
        level = getattr(logging, log_level, logging.INFO),
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
        auto_init = getattr(config_class, 'AUTO_INITIALIZE_DB', False) and not skip_auto_init
        
        if auto_init:
            # Check if database is empty or missing critical data (rules)
            from app.models import Fund, Rule
            
            fund_count = Fund.query.count()
            rule_count = Rule.query.count()
            is_empty = fund_count == 0
            missing_rules = fund_count > 0 and rule_count == 0
            
            if is_empty:
                logger.info("Database appears to be empty, running automatic initialization...")
                try:
                    # Import and run the seed script
                    import sys
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                    
                    from scripts.seed_data import main as seed_main
                    # Pass the current app instance to prevent infinite loop
                    seed_main(app)
                    logger.info("Database auto-initialization completed successfully")
                except Exception as e:
                    logger.error(f"Database auto-initialization failed: {e}", exc_info=True)
                    logger.error("Application will continue with empty database")
            elif missing_rules:
                logger.warning(f"Database has {fund_count} funds but {rule_count} rules. Rules may be missing.")
                logger.info("Attempting to add missing rules without dropping existing data...")
                try:
                    # Import and run just the rules creation
                    import sys
                    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                    
                    from scripts.seed_data import ensure_sample_rules_exist
                    rules = ensure_sample_rules_exist()
                    if rules:
                        logger.info(f"Successfully added {len(rules)} sample rules")
                    else:
                        logger.warning("No rules were added. Check logs for errors.")
                except Exception as e:
                    logger.error(f"Failed to add missing rules: {e}", exc_info=True)
                    logger.warning("Consider running seed_data.py manually to populate rules: python scripts/seed_data.py")
    
    return app
