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
    
    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix = '/api')
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
        logging.info("Database tables created/verified")
    
    return app
