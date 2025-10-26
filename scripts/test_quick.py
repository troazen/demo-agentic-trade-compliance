"""
Quick test to verify the SecuritiesPrice import fix.
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.models import Fund

app = create_app()

with app.app_context():
    fund = Fund.query.first()
    if fund:
        print(f"Fund: {fund.fund_name}")
        print(f"Holdings count: {fund.get_holdings_count()}")
        print(f"Calculating total assets...")
        try:
            total_assets = fund.calculate_total_assets()
            print(f"✓ SUCCESS: Total assets = ${total_assets}")
        except Exception as e:
            print(f"✗ FAILED: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("No funds found in database")

