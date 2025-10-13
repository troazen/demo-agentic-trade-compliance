"""
SQLAlchemy database models and configuration.
"""

from flask_sqlalchemy import SQLAlchemy
from app.config import Config

# Initialize SQLAlchemy
db = SQLAlchemy()

# Import all models to ensure they are registered
from app.models.fund import Fund
from app.models.security import Security
from app.models.issuer import Issuer
from app.models.securities_price import SecuritiesPrice
from app.models.holding import Holding, HoldingStaging
from app.models.trade import Trade
from app.models.rule import Rule, RuleAttachment
from app.models.alert import Alert
