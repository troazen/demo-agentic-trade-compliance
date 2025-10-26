"""
Test script to verify database initialization from JSON.
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.models import db, Fund, Security, Issuer

def check_database_status():
    """Check the status of the database."""
    app = create_app()
    
    with app.app_context():
        funds = Fund.query.count()
        issuers = Issuer.query.count()
        securities = Security.query.count()
        
        print(f"Database Status:")
        print(f"  Funds: {funds}")
        print(f"  Issuers: {issuers}")
        print(f"  Securities: {securities}")
        
        if funds > 0:
            print("\nSample Fund Data:")
            for fund in Fund.query.limit(3).all():
                print(f"  - {fund.fund_name}: Cash ${fund.cash}, Holdings: {fund.get_holdings_count()}")
        
        if securities > 0:
            print(f"\nSample Securities ({min(5, securities)} of {securities}):")
            for security in Security.query.limit(5).all():
                print(f"  - {security.ticker}: {security.name}")

if __name__ == '__main__':
    check_database_status()

