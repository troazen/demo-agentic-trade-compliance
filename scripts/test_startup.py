"""
Startup test script for Investment Operations Compliance System.

This script verifies that:
1. The database has been initialized
2. Core tables have data
3. API endpoints are accessible
4. Data relationships are working
"""

import os
import sys
import logging
from decimal import Decimal

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import create_app
from app.models import db, Fund, Security, Issuer, Holding, SecuritiesPrice, Rule, RuleAttachment
from app.constants import DenominatorType, AlertIf

# Set up logging
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database_initialization():
    """Test that database has been initialized with data."""
    logger.info("=" * 60)
    logger.info("TEST 1: Database Initialization")
    logger.info("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        # Check table counts
        fund_count = Fund.query.count()
        issuer_count = Issuer.query.count()
        security_count = Security.query.count()
        holding_count = Holding.query.count()
        rule_count = Rule.query.count()
        attachment_count = RuleAttachment.query.count()
        price_count = SecuritiesPrice.query.count()
        
        logger.info(f"\nDatabase Record Counts:")
        logger.info(f"  Funds: {fund_count}")
        logger.info(f"  Issuers: {issuer_count}")
        logger.info(f"  Securities: {security_count}")
        logger.info(f"  Holdings: {holding_count}")
        logger.info(f"  Rules: {rule_count}")
        logger.info(f"  Rule Attachments: {attachment_count}")
        logger.info(f"  Price Records: {price_count}")
        
        # Verify minimum expected data
        tests_passed = 0
        total_tests = 0
        
        total_tests += 1
        if fund_count > 0:
            logger.info("✓ PASS: At least one fund exists")
            tests_passed += 1
        else:
            logger.error("✗ FAIL: No funds found")
        
        total_tests += 1
        if issuer_count > 0:
            logger.info("✓ PASS: At least one issuer exists")
            tests_passed += 1
        else:
            logger.error("✗ FAIL: No issuers found")
        
        total_tests += 1
        if security_count > 0:
            logger.info("✓ PASS: At least one security exists")
            tests_passed += 1
        else:
            logger.error("✗ FAIL: No securities found")
        
        total_tests += 1
        if holding_count > 0:
            logger.info("✓ PASS: At least one holding exists")
            tests_passed += 1
        else:
            logger.error("✗ FAIL: No holdings found")
        
        total_tests += 1
        if rule_count > 0:
            logger.info("✓ PASS: At least one rule exists")
            tests_passed += 1
        else:
            logger.error("✗ FAIL: No rules found")
        
        total_tests += 1
        if attachment_count > 0:
            logger.info("✓ PASS: At least one rule attachment exists")
            tests_passed += 1
        else:
            logger.error("✗ FAIL: No rule attachments found")
        
        logger.info(f"\nTest Results: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests


def test_data_relationships():
    """Test that data relationships are correctly established."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 2: Data Relationships")
    logger.info("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        tests_passed = 0
        total_tests = 0
        
        # Test fund-holdings relationship
        fund = Fund.query.first()
        if fund:
            total_tests += 1
            if fund.holdings:
                logger.info(f"✓ PASS: Fund '{fund.fund_name}' has {len(fund.holdings)} holdings")
                tests_passed += 1
            else:
                logger.error(f"✗ FAIL: Fund '{fund.fund_name}' has no holdings")
        
        # Test security-issuer relationship
        security = Security.query.first()
        if security:
            total_tests += 1
            if security.issuer:
                logger.info(f"✓ PASS: Security '{security.ticker}' has issuer '{security.issuer.name}'")
                tests_passed += 1
            else:
                logger.error(f"✗ FAIL: Security '{security.ticker}' has no issuer")
        
        # Test rule-attachment relationship
        rule = Rule.query.first()
        if rule:
            total_tests += 1
            if rule.attachments:
                logger.info(f"✓ PASS: Rule '{rule.rule_name}' has {len(rule.attachments)} attachments")
                tests_passed += 1
            else:
                logger.error(f"✗ FAIL: Rule '{rule.rule_name}' has no attachments")
        
        # Test price data
        total_tests += 1
        price_records = SecuritiesPrice.query.limit(10).all()
        if price_records:
            logger.info(f"✓ PASS: Price data exists ({len(price_records)} records sampled)")
            tests_passed += 1
        else:
            logger.error("✗ FAIL: No price records found")
        
        logger.info(f"\nTest Results: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests


def test_fund_functionality():
    """Test fund calculation methods."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 3: Fund Functionality")
    logger.info("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        tests_passed = 0
        total_tests = 0
        
        fund = Fund.query.first()
        if not fund:
            logger.error("✗ FAIL: No fund available for testing")
            return 0, 0
        
        # Test holdings count
        total_tests += 1
        holdings_count = fund.get_holdings_count()
        if holdings_count >= 0:
            logger.info(f"✓ PASS: Fund '{fund.fund_name}' reports {holdings_count} holdings")
            tests_passed += 1
        else:
            logger.error("✗ FAIL: get_holdings_count() failed")
        
        # Test total assets calculation
        total_tests += 1
        try:
            total_assets = fund.calculate_total_assets()
            logger.info(f"✓ PASS: Fund '{fund.fund_name}' total assets calculated: ${total_assets}")
            tests_passed += 1
        except Exception as e:
            logger.error(f"✗ FAIL: calculate_total_assets() raised exception: {e}")
        
        logger.info(f"\nTest Results: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests


def test_api_readiness():
    """Test that API models are ready for API calls."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST 4: API Readiness")
    logger.info("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        tests_passed = 0
        total_tests = 0
        
        # Test Fund.to_dict()
        fund = Fund.query.first()
        if fund:
            total_tests += 1
            try:
                fund_dict = fund.to_dict()
                required_keys = ['fund_id', 'fund_name', 'cash', 'created_at', 'updated_at']
                if all(key in fund_dict for key in required_keys):
                    logger.info(f"✓ PASS: Fund.to_dict() returns all required keys")
                    tests_passed += 1
                else:
                    logger.error(f"✗ FAIL: Fund.to_dict() missing keys")
            except Exception as e:
                logger.error(f"✗ FAIL: Fund.to_dict() raised exception: {e}")
        
        # Test Security.to_dict()
        security = Security.query.first()
        if security:
            total_tests += 1
            try:
                security_dict = security.to_dict()
                required_keys = ['ticker', 'name', 'type', 'issr_id']
                if all(key in security_dict for key in required_keys):
                    logger.info(f"✓ PASS: Security.to_dict() returns all required keys")
                    tests_passed += 1
                else:
                    logger.error(f"✗ FAIL: Security.to_dict() missing keys")
            except Exception as e:
                logger.error(f"✗ FAIL: Security.to_dict() raised exception: {e}")
        
        # Test Rule.to_dict()
        rule = Rule.query.first()
        if rule:
            total_tests += 1
            try:
                rule_dict = rule.to_dict()
                required_keys = ['rule_id', 'rule_name', 'alert_message', 'denominator']
                if all(key in rule_dict for key in required_keys):
                    logger.info(f"✓ PASS: Rule.to_dict() returns all required keys")
                    tests_passed += 1
                else:
                    logger.error(f"✗ FAIL: Rule.to_dict() missing keys")
            except Exception as e:
                logger.error(f"✗ FAIL: Rule.to_dict() raised exception: {e}")
        
        logger.info(f"\nTest Results: {tests_passed}/{total_tests} passed")
        return tests_passed, total_tests


def display_sample_data():
    """Display sample data from the database."""
    logger.info("\n" + "=" * 60)
    logger.info("SAMPLE DATA")
    logger.info("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        # Display funds
        logger.info("\nFunds:")
        for fund in Fund.query.limit(5).all():
            logger.info(f"  {fund.fund_name}: Cash ${fund.cash}, Holdings: {fund.get_holdings_count()}")
        
        # Display securities
        logger.info(f"\nSecurities (showing up to 10 of {Security.query.count()}):")
        for security in Security.query.limit(10).all():
            issuer_name = security.issuer.name if security.issuer else "Unknown"
            logger.info(f"  {security.ticker}: {security.name} (Issuer: {issuer_name})")
        
        # Display rules
        logger.info(f"\nCompliance Rules:")
        for rule in Rule.query.all():
            logger.info(f"  {rule.rule_name} ({'Active' if rule.active else 'Inactive'})")


def main():
    """Run all startup tests."""
    logger.info("\n" + "=" * 60)
    logger.info("STARTUP TESTS FOR INVESTMENT OPERATIONS COMPLIANCE SYSTEM")
    logger.info("=" * 60 + "\n")
    
    try:
        # Run tests
        init_passed, init_total = test_database_initialization()
        rel_passed, rel_total = test_data_relationships()
        fund_passed, fund_total = test_fund_functionality()
        api_passed, api_total = test_api_readiness()
        
        # Calculate totals
        total_passed = init_passed + rel_passed + fund_passed + api_passed
        total_tests = init_total + rel_total + fund_total + api_total
        
        # Display sample data
        display_sample_data()
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests Passed: {total_passed}/{total_tests}")
        
        if total_passed == total_tests:
            logger.info("✓ ALL TESTS PASSED - System is ready for use!")
        else:
            logger.warning(f"⚠ SOME TESTS FAILED - {total_tests - total_passed} tests did not pass")
        
        return total_passed == total_tests
    
    except Exception as e:
        logger.error(f"Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

