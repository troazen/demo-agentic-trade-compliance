"""
Sample data seeding script for the Investment Operations Compliance System.
"""

import logging

import os
import sys
from decimal import Decimal
from datetime import datetime, date, timedelta
import random

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app import create_app
from app.models import db, Fund, Security, Issuer, SecuritiesPrice, Holding, Rule, RuleAttachment
from app.constants import TradeDirection, DenominatorType, AlertIf
from app.config import Config

logger = logging.getLogger(__name__)


def create_sample_issuers():
    """Create sample issuers."""
    logger.info("Creating sample issuers")
    
    issuers_data = [
        {
            'name': 'Apple Inc.',
            'gics_sector': 'Information Technology',
            'gics_industry_grp': 'Technology Hardware & Equipment',
            'gics_industry': 'Technology Hardware, Storage & Peripherals',
            'gics_sub_industry': 'Technology Hardware, Storage & Peripherals',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        },
        {
            'name': 'Microsoft Corporation',
            'gics_sector': 'Information Technology',
            'gics_industry_grp': 'Software & Services',
            'gics_industry': 'Systems Software',
            'gics_sub_industry': 'Systems Software',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        },
        {
            'name': 'Amazon.com Inc.',
            'gics_sector': 'Consumer Discretionary',
            'gics_industry_grp': 'Retail',
            'gics_industry': 'Internet & Direct Marketing Retail',
            'gics_sub_industry': 'Internet & Direct Marketing Retail',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        },
        {
            'name': 'Alphabet Inc.',
            'gics_sector': 'Communication Services',
            'gics_industry_grp': 'Media & Entertainment',
            'gics_industry': 'Interactive Media & Services',
            'gics_sub_industry': 'Interactive Media & Services',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        },
        {
            'name': 'Tesla Inc.',
            'gics_sector': 'Consumer Discretionary',
            'gics_industry_grp': 'Automobiles & Components',
            'gics_industry': 'Automobile Manufacturers',
            'gics_sub_industry': 'Automobile Manufacturers',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        },
        {
            'name': 'JPMorgan Chase & Co.',
            'gics_sector': 'Financials',
            'gics_industry_grp': 'Banks',
            'gics_industry': 'Diversified Banks',
            'gics_sub_industry': 'Diversified Banks',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        },
        {
            'name': 'Johnson & Johnson',
            'gics_sector': 'Health Care',
            'gics_industry_grp': 'Pharmaceuticals, Biotechnology & Life Sciences',
            'gics_industry': 'Pharmaceuticals',
            'gics_sub_industry': 'Pharmaceuticals',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        },
        {
            'name': 'Procter & Gamble Co.',
            'gics_sector': 'Consumer Staples',
            'gics_industry_grp': 'Household & Personal Products',
            'gics_industry': 'Household Products',
            'gics_sub_industry': 'Household Products',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        },
        {
            'name': 'Coca-Cola Co.',
            'gics_sector': 'Consumer Staples',
            'gics_industry_grp': 'Food, Beverage & Tobacco',
            'gics_industry': 'Soft Drinks & Non-alcoholic Beverages',
            'gics_sub_industry': 'Soft Drinks & Non-alcoholic Beverages',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        },
        {
            'name': 'Walt Disney Co.',
            'gics_sector': 'Communication Services',
            'gics_industry_grp': 'Media & Entertainment',
            'gics_industry': 'Movies & Entertainment',
            'gics_sub_industry': 'Movies & Entertainment',
            'country_domicile': 'United States',
            'country_incorporation': 'United States',
            'country_domicile_code': 'USA',
            'country_incorporation_code': 'USA'
        }
    ]
    
    issuers = []
    for issuer_data in issuers_data:
        issuer = Issuer(**issuer_data)
        db.session.add(issuer)
        issuers.append(issuer)
    
    db.session.commit()
    logger.info(f"Created {len(issuers)} issuers")
    return issuers


def create_sample_securities(issuers):
    """Create sample securities."""
    logger.info("Creating sample securities")
    
    securities_data = [
        {'ticker': 'AAPL', 'name': 'Apple Inc.', 'issuer_name': 'Apple Inc.', 'shares_outstanding': 15000000000},
        {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'issuer_name': 'Microsoft Corporation', 'shares_outstanding': 7500000000},
        {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'issuer_name': 'Amazon.com Inc.', 'shares_outstanding': 10000000000},
        {'ticker': 'GOOGL', 'name': 'Alphabet Inc. Class A', 'issuer_name': 'Alphabet Inc.', 'shares_outstanding': 12000000000},
        {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'issuer_name': 'Tesla Inc.', 'shares_outstanding': 3000000000},
        {'ticker': 'JPM', 'name': 'JPMorgan Chase & Co.', 'issuer_name': 'JPMorgan Chase & Co.', 'shares_outstanding': 3000000000},
        {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'issuer_name': 'Johnson & Johnson', 'shares_outstanding': 2600000000},
        {'ticker': 'PG', 'name': 'Procter & Gamble Co.', 'issuer_name': 'Procter & Gamble Co.', 'shares_outstanding': 2400000000},
        {'ticker': 'KO', 'name': 'Coca-Cola Co.', 'issuer_name': 'Coca-Cola Co.', 'shares_outstanding': 4300000000},
        {'ticker': 'DIS', 'name': 'Walt Disney Co.', 'issuer_name': 'Walt Disney Co.', 'shares_outstanding': 1800000000},
        {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'issuer_name': 'NVIDIA Corporation', 'shares_outstanding': 2500000000},
        {'ticker': 'META', 'name': 'Meta Platforms Inc.', 'issuer_name': 'Meta Platforms Inc.', 'shares_outstanding': 2700000000},
        {'ticker': 'NFLX', 'name': 'Netflix Inc.', 'issuer_name': 'Netflix Inc.', 'shares_outstanding': 450000000},
        {'ticker': 'ADBE', 'name': 'Adobe Inc.', 'issuer_name': 'Adobe Inc.', 'shares_outstanding': 460000000},
        {'ticker': 'CRM', 'name': 'Salesforce Inc.', 'issuer_name': 'Salesforce Inc.', 'shares_outstanding': 1000000000},
        {'ticker': 'ORCL', 'name': 'Oracle Corporation', 'issuer_name': 'Oracle Corporation', 'shares_outstanding': 2800000000},
        {'ticker': 'INTC', 'name': 'Intel Corporation', 'issuer_name': 'Intel Corporation', 'shares_outstanding': 4100000000},
        {'ticker': 'AMD', 'name': 'Advanced Micro Devices Inc.', 'issuer_name': 'Advanced Micro Devices Inc.', 'shares_outstanding': 1600000000},
        {'ticker': 'CSCO', 'name': 'Cisco Systems Inc.', 'issuer_name': 'Cisco Systems Inc.', 'shares_outstanding': 4200000000},
        {'ticker': 'IBM', 'name': 'International Business Machines Corp.', 'issuer_name': 'International Business Machines Corp.', 'shares_outstanding': 900000000},
        {'ticker': 'V', 'name': 'Visa Inc.', 'issuer_name': 'Visa Inc.', 'shares_outstanding': 2100000000},
        {'ticker': 'MA', 'name': 'Mastercard Inc.', 'issuer_name': 'Mastercard Inc.', 'shares_outstanding': 950000000},
        {'ticker': 'WMT', 'name': 'Walmart Inc.', 'issuer_name': 'Walmart Inc.', 'shares_outstanding': 2700000000},
        {'ticker': 'COST', 'name': 'Costco Wholesale Corporation', 'issuer_name': 'Costco Wholesale Corporation', 'shares_outstanding': 440000000},
        {'ticker': 'HD', 'name': 'Home Depot Inc.', 'issuer_name': 'Home Depot Inc.', 'shares_outstanding': 1000000000}
    ]
    
    # Create issuer lookup
    issuer_lookup = {issuer.name: issuer for issuer in issuers}
    
    securities = []
    for sec_data in securities_data:
        issuer = issuer_lookup.get(sec_data['issuer_name'])
        if issuer:
            security = Security(
                ticker = sec_data['ticker'],
                name = sec_data['name'],
                issr_id = issuer.issr_id,
                shares_outstanding = sec_data['shares_outstanding']
            )
            db.session.add(security)
            securities.append(security)
    
    db.session.commit()
    logger.info(f"Created {len(securities)} securities")
    return securities


def create_sample_prices(securities):
    """Create sample price data."""
    logger.info("Creating sample price data")
    
    # Generate prices for the last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days = 30)
    
    base_prices = {
        'AAPL': 150.00, 'MSFT': 300.00, 'AMZN': 120.00, 'GOOGL': 2500.00, 'TSLA': 200.00,
        'JPM': 140.00, 'JNJ': 160.00, 'PG': 150.00, 'KO': 60.00, 'DIS': 90.00,
        'NVDA': 400.00, 'META': 300.00, 'NFLX': 400.00, 'ADBE': 500.00, 'CRM': 200.00,
        'ORCL': 100.00, 'INTC': 30.00, 'AMD': 100.00, 'CSCO': 50.00, 'IBM': 140.00,
        'V': 200.00, 'MA': 350.00, 'WMT': 150.00, 'COST': 500.00, 'HD': 300.00
    }
    
    current_date = start_date
    while current_date <= end_date:
        for security in securities:
            base_price = base_prices.get(security.ticker, 100.00)
            # Add some random variation
            variation = random.uniform(0.95, 1.05)
            price = base_price * variation
            
            price_record = SecuritiesPrice(
                ticker = security.ticker,
                price_date = current_date,
                price = Decimal(str(round(price, 2)))
            )
            db.session.add(price_record)
        
        current_date += timedelta(days = 1)
    
    db.session.commit()
    logger.info("Created sample price data for 30 days")


def create_sample_funds():
    """Create sample funds."""
    logger.info("Creating sample funds")
    
    funds_data = [
        {'fund_name': 'Growth Fund', 'cash': Decimal('1000000.00')},
        {'fund_name': 'Value Fund', 'cash': Decimal('2000000.00')},
        {'fund_name': 'Technology Fund', 'cash': Decimal('500000.00')},
        {'fund_name': 'Balanced Fund', 'cash': Decimal('1500000.00')}
    ]
    
    funds = []
    for fund_data in funds_data:
        fund = Fund(**fund_data)
        db.session.add(fund)
        funds.append(fund)
    
    db.session.commit()
    logger.info(f"Created {len(funds)} funds")
    return funds


def create_sample_holdings(funds, securities):
    """Create sample holdings for funds."""
    logger.info("Creating sample holdings")
    
    # Define holdings for each fund
    fund_holdings = {
        'Growth Fund': [
            ('AAPL', 1000), ('MSFT', 500), ('GOOGL', 100), ('TSLA', 200), ('NVDA', 300)
        ],
        'Value Fund': [
            ('JPM', 2000), ('JNJ', 1000), ('PG', 800), ('KO', 1500), ('WMT', 600)
        ],
        'Technology Fund': [
            ('AAPL', 2000), ('MSFT', 1500), ('GOOGL', 200), ('NVDA', 1000), ('META', 500), ('NFLX', 300)
        ],
        'Balanced Fund': [
            ('AAPL', 500), ('MSFT', 400), ('JPM', 800), ('JNJ', 600), ('PG', 400), ('KO', 700)
        ]
    }
    
    for fund in funds:
        holdings = fund_holdings.get(fund.fund_name, [])
        for ticker, shares in holdings:
            security = next((s for s in securities if s.ticker == ticker), None)
            if security:
                holding = Holding(
                    fund_id = fund.fund_id,
                    ticker = ticker,
                    shares = Decimal(str(shares))
                )
                db.session.add(holding)
    
    db.session.commit()
    logger.info("Created sample holdings")


def create_sample_rules():
    """Create sample compliance rules."""
    logger.info("Creating sample compliance rules")
    
    rules_data = [
        {
            'rule_name': 'Max 30% in GICS technology sector issuers',
            'alert_message': 'This fund can only hold up to 30% in technology sector as defined by GICS',
            'trade_compliance_mode': True,
            'portfolio_compliance_mode': False,
            'logic': "issuers.gics_sector = 'Information Technology'",
            'denominator': DenominatorType.TOTAL_ASSETS,
            'alert_if': AlertIf.ABOVE,
            'alert_level': Decimal('30.0')
        },
        {
            'rule_name': 'Max 10% TA in non Benchmark Constituents (S&P 500)',
            'alert_message': 'This fund is intended to have the S&P 500 as a benchmark, but cannot hold more than 10% of total assets in other securities (ex cash)',
            'trade_compliance_mode': True,
            'portfolio_compliance_mode': True,
            'logic': "holdings.ticker NOT IN ('NVDA', 'MSFT', 'AAPL', 'GOOGL', 'AMZN', 'V', 'JPM', 'ORCL', 'WMT', 'NFLX', 'JNJ', 'ABBV', 'COST', 'BRK.B', 'TSLA', 'CAT', 'KO', 'WFC', 'MS', 'IBM', 'GE', 'PG', 'TMUS', 'ABT')",
            'denominator': DenominatorType.TOTAL_ASSETS,
            'alert_if': AlertIf.ABOVE,
            'alert_level': Decimal('10.0')
        },
        {
            'rule_name': 'No investment in OFAC restricted countries',
            'alert_message': 'US Regulations prohibit transacting in securities based in OFAC restricted countries.',
            'trade_compliance_mode': True,
            'portfolio_compliance_mode': True,
            'logic': "issuer.country_incorporation IN ('PRK', 'MMR', 'TKM')",
            'denominator': DenominatorType.PROHIBIT,
            'alert_if': None,
            'alert_level': None
        },
        {
            'rule_name': 'Max 5% of shares outstanding in any security 5(b)(1)',
            'alert_message': 'A US 40 Act fund diversification requirements limits investments in any one issuer to 5% of TNA, for at least 75% of the fund. For safety, we limit shares outstanding to 5% generally.',
            'trade_compliance_mode': True,
            'portfolio_compliance_mode': True,
            'logic': '',
            'denominator': DenominatorType.SHARES_OUTSTANDING_FE,
            'alert_if': AlertIf.ABOVE,
            'alert_level': Decimal('5.0')
        }
    ]
    
    rules = []
    for rule_data in rules_data:
        rule = Rule(**rule_data)
        db.session.add(rule)
        rules.append(rule)
    
    db.session.commit()
    logger.info(f"Created {len(rules)} compliance rules")
    return rules


def create_sample_rule_attachments(funds, rules):
    """Create sample rule attachments."""
    logger.info("Creating sample rule attachments")
    
    # Attach rules to funds
    attachments = [
        (funds[0].fund_id, rules[0].rule_id),  # Growth Fund - Tech sector rule
        (funds[0].fund_id, rules[1].rule_id),  # Growth Fund - S&P 500 rule
        (funds[0].fund_id, rules[2].rule_id),  # Growth Fund - OFAC rule
        (funds[0].fund_id, rules[3].rule_id),  # Growth Fund - Diversification rule
        
        (funds[1].fund_id, rules[1].rule_id),  # Value Fund - S&P 500 rule
        (funds[1].fund_id, rules[2].rule_id),  # Value Fund - OFAC rule
        (funds[1].fund_id, rules[3].rule_id),  # Value Fund - Diversification rule
        
        (funds[2].fund_id, rules[0].rule_id),  # Technology Fund - Tech sector rule
        (funds[2].fund_id, rules[1].rule_id),  # Technology Fund - S&P 500 rule
        (funds[2].fund_id, rules[2].rule_id),  # Technology Fund - OFAC rule
        (funds[2].fund_id, rules[3].rule_id),  # Technology Fund - Diversification rule
        
        (funds[3].fund_id, rules[1].rule_id),  # Balanced Fund - S&P 500 rule
        (funds[3].fund_id, rules[2].rule_id),  # Balanced Fund - OFAC rule
        (funds[3].fund_id, rules[3].rule_id),  # Balanced Fund - Diversification rule
    ]
    
    for fund_id, rule_id in attachments:
        attachment = RuleAttachment(
            fund_id = fund_id,
            rule_id = rule_id,
            active = True
        )
        db.session.add(attachment)
    
    db.session.commit()
    logger.info(f"Created {len(attachments)} rule attachments")


def main():
    """Main seeding function."""
    import logging
    
    # Set up logging
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting data seeding process")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Clear existing data
        logger.info("Clearing existing data")
        db.drop_all()
        db.create_all()
        
        # Create sample data
        issuers = create_sample_issuers()
        securities = create_sample_securities(issuers)
        create_sample_prices(securities)
        funds = create_sample_funds()
        create_sample_holdings(funds, securities)
        rules = create_sample_rules()
        create_sample_rule_attachments(funds, rules)
        
        logger.info("Data seeding completed successfully")
        logger.info(f"Created: {len(issuers)} issuers, {len(securities)} securities, {len(funds)} funds, {len(rules)} rules")


if __name__ == '__main__':
    main()
