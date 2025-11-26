"""
Sample data seeding script for the Investment Operations Compliance System.

This script initializes the database with data from Investment_Data.json when available,
or falls back to hardcoded sample data. It is automatically invoked on app startup
in development and testing environments when the database is empty.

To run manually:
    python scripts/seed_data.py

The script will:
    1. Load Investment_Data.json if available
    2. Create issuers and securities from JSON data
    3. Map GICS classifications and country data
    4. Generate historical price data
    5. Create sample funds, holdings, rules, and attachments
"""

import logging
import json
import os
import sys
from decimal import Decimal
from datetime import datetime, date, timedelta
import random
from typing import Dict, List, Any, Optional

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app import create_app
from app.models import db, Fund, Security, Issuer, SecuritiesPrice, Holding, Rule, RuleAttachment
from app.constants import TradeDirection, DenominatorType, AlertIf
from app.config import Config

logger = logging.getLogger(__name__)


def load_json_data(json_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load and parse Investment_Data.json file.
    
    Args:
        json_file_path: Path to the JSON file (relative to project root if not absolute)
        
    Returns:
        Dictionary containing parsed JSON data
    """
    # Default to looking in the project root
    if json_file_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        json_file_path = os.path.join(project_root, 'Investment_Data.json')
    
    logger.info(f"Loading JSON data from {json_file_path}")
    
    if not os.path.exists(json_file_path):
        logger.warning(f"JSON file not found: {json_file_path}")
        return {}
    
    try:
        with open(json_file_path, 'r', encoding = 'utf-8') as f:
            data = json.load(f)
        logger.info("JSON data loaded successfully")
        return data
    except Exception as e:
        logger.error(f"Failed to load JSON data: {e}")
        return {}


def extract_table_data(json_data: Dict[str, Any], table_name: str) -> Dict[str, Any]:
    """
    Extract specific table data from JSON structure.
    
    Args:
        json_data: Parsed JSON data
        table_name: Name of the table to extract
        
    Returns:
        Dictionary containing table structure and rows
    """
    if 'objects' not in json_data:
        logger.warning("No 'objects' key in JSON data")
        return {}
    
    for obj in json_data['objects']:
        if obj.get('name') == table_name and obj.get('type') == 'table':
            logger.info(f"Found table '{table_name}' with {len(obj.get('rows', []))} rows")
            return obj
    
    logger.warning(f"Table '{table_name}' not found in JSON data")
    return {}


def build_gics_lookup(json_data: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    """
    Build lookup dictionaries for GICS classification.
    
    Args:
        json_data: Parsed JSON data
        
    Returns:
        Dictionary mapping Primary_ID to GICS data for each category
    """
    lookups = {
        'sectors': {},
        'industry_groups': {},
        'industries': {},
        'sub_industries': {}
    }
    
    for table_name in lookups.keys():
        table_data = extract_table_data(json_data, table_name)
        if 'rows' in table_data and 'columns' in table_data:
            columns = [col['name'] for col in table_data['columns']]
            for row in table_data['rows']:
                if len(row) >= 3:
                    primary_id = row[0]
                    code = row[1]
                    name = row[2]
                    lookups[table_name][primary_id] = {'code': code, 'name': name}
    
    logger.info(f"Built GICS lookups: {sum(len(v) for v in lookups.values())} total entries")
    return lookups


def build_country_lookup(json_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Build lookup dictionary for country data.
    
    Args:
        json_data: Parsed JSON data
        
    Returns:
        Dictionary mapping country code to country name
    """
    countries = extract_table_data(json_data, 'countries')
    country_lookup = {}
    
    if 'rows' in countries:
        for row in countries['rows']:
            if len(row) >= 2:
                country_code = row[0]
                country_name = row[1]
                country_lookup[country_code] = country_name
    
    logger.info(f"Built country lookup with {len(country_lookup)} countries")
    return country_lookup


def create_issuers_from_json(json_data: Dict[str, Any], gics_lookups: Dict[str, Dict[str, Dict[str, str]]], 
                              country_lookup: Dict[str, str]) -> List[Issuer]:
    """
    Map JSON issuers table to application issuers schema with GICS and country data.
    
    Args:
        json_data: Parsed JSON data
        gics_lookups: GICS classification lookup dictionaries
        country_lookup: Country code to name lookup
        
    Returns:
        List of created Issuer objects
    """
    logger.info("Creating issuers from JSON data")
    
    issuers_table = extract_table_data(json_data, 'issuers')
    if not issuers_table or 'rows' not in issuers_table:
        logger.warning("No issuers table found in JSON, creating empty list")
        return []
    
    issuers = []
    unique_issuers = {}  # Use Issuer_Name as key to avoid duplicates
    
    # Only get "Ultimate Parent Issuer" or "Parent Issuer" types from JSON
    party_type_col_idx = 4  # Party_Type is the 5th column (index 4)
    issuer_code_col_idx = 0
    issuer_name_col_idx = 2
    country_code_col_idx = 3
    
    for row in issuers_table['rows']:
        if len(row) > party_type_col_idx:
            party_type = row[party_type_col_idx]
            issuer_name = row[issuer_name_col_idx]
            
            # Only process Ultimate Parent and Parent issuers (skip sub-issuers)
            if party_type in ('Ultimate Parent Issuer', 'Parent Issuer'):
                if issuer_name not in unique_issuers:
                    unique_issuers[issuer_name] = {
                        'name': issuer_name,
                        'country_code': row[country_code_col_idx] if len(row) > country_code_col_idx else None,
                        'issuer_code': row[issuer_code_col_idx]
                    }
    
    logger.info(f"Found {len(unique_issuers)} unique parent issuers from JSON")
    
    # Create issuer objects
    for issuer_name, issuer_data in unique_issuers.items():
        country_code = issuer_data.get('country_code')
        country_name = country_lookup.get(country_code, '') if country_code else None
        
        issuer = Issuer(
            name = issuer_data['name'],
            country_domicile_code = country_code if country_code else None,
            country_incorporation_code = country_code if country_code else None,
            country_domicile = country_name,
            country_incorporation = country_name
        )
        
        db.session.add(issuer)
        issuers.append(issuer)
    
    db.session.commit()
    logger.info(f"Created {len(issuers)} issuers from JSON data")
    return issuers


def create_securities_from_json(json_data: Dict[str, Any], issuers: List[Issuer], 
                                 gics_lookups: Dict[str, Dict[str, Dict[str, str]]],
                                 country_lookup: Dict[str, str]) -> List[Security]:
    """
    Map JSON companies table to application securities schema.
    
    Args:
        json_data: Parsed JSON data
        issuers: List of created issuer objects
        gics_lookups: GICS classification lookup dictionaries
        country_lookup: Country code to name lookup
        
    Returns:
        List of created Security objects
    """
    logger.info("Creating securities from JSON data")
    
    companies_table = extract_table_data(json_data, 'companies')
    if not companies_table or 'rows' not in companies_table:
        logger.warning("No companies table found in JSON, creating empty list")
        return []
    
    securities = []
    issuer_name_lookup = {issuer.name: issuer for issuer in issuers}
    
    # Company table columns: Primary_ID, Ticker, Name, Sector_FK, Industry_Group_FK, Industry_FK, Sub_Industry_FK, Issuer_Code
    ticker_col = 1
    name_col = 2
    sector_fk_col = 3
    industry_grp_fk_col = 4
    industry_fk_col = 5
    sub_industry_fk_col = 6
    issuer_code_col = 7
    
    for row in companies_table['rows']:
        if len(row) <= ticker_col or row[ticker_col] is None:
            continue
        
        ticker = row[ticker_col]
        security_name = row[name_col]
        
        # Map GICS data
        sector_fk = row[sector_fk_col] if len(row) > sector_fk_col else None
        industry_grp_fk = row[industry_grp_fk_col] if len(row) > industry_grp_fk_col else None
        industry_fk = row[industry_fk_col] if len(row) > industry_fk_col else None
        sub_industry_fk = row[sub_industry_fk_col] if len(row) > sub_industry_fk_col else None
        
        # Find matching issuer - try to match by security name
        issuer = None
        for iss in issuers:
            if iss.name.lower() in security_name.lower() or security_name.lower() in iss.name.lower():
                issuer = iss
                break
        
        # If no match found, try to find a generic issuer
        if issuer is None:
            # Check if we can find an issuer with similar name (partial match)
            for iss in issuers:
                security_words = set(security_name.lower().split())
                issuer_words = set(iss.name.lower().split())
                # If there's some overlap in words, use this issuer
                if security_words & issuer_words:
                    issuer = iss
                    break
        
        # If still no match, create a placeholder issuer
        if issuer is None:
            if len(securities) < 10:  # Only log for first few securities to reduce noise
                logger.debug(f"No issuer found for security {ticker}, creating placeholder issuer")
            issuer = Issuer(
                name = security_name,
                country_domicile_code = 'US',
                country_incorporation_code = 'US',
                country_domicile = 'United States',
                country_incorporation = 'United States'
            )
            db.session.add(issuer)
            db.session.flush()
        
        # Update issuer GICS data if available
        if sector_fk and sector_fk in gics_lookups.get('sectors', {}):
            issuer.gics_sector = gics_lookups['sectors'][sector_fk]['name']
        
        if industry_grp_fk and industry_grp_fk in gics_lookups.get('industry_groups', {}):
            issuer.gics_industry_grp = gics_lookups['industry_groups'][industry_grp_fk]['name']
        
        if industry_fk and industry_fk in gics_lookups.get('industries', {}):
            issuer.gics_industry = gics_lookups['industries'][industry_fk]['name']
        
        if sub_industry_fk and sub_industry_fk in gics_lookups.get('sub_industries', {}):
            issuer.gics_sub_industry = gics_lookups['sub_industries'][sub_industry_fk]['name']
        
        # Create security
        security = Security(
            ticker = ticker,
            name = security_name,
            issr_id = issuer.issr_id,
            shares_outstanding = random.randint(1000000, 50000000)  # Random placeholder
        )
        
        db.session.add(security)
        securities.append(security)
    
    db.session.commit()
    logger.info(f"Created {len(securities)} securities from JSON data")
    return securities


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


def create_holdings_from_account_positions(json_data: Dict[str, Any], funds: List[Fund], 
                                           securities: List[Security]) -> None:
    """
    Create holdings from account_positions table in JSON data.
    
    Args:
        json_data: Parsed JSON data
        funds: List of created fund objects
        securities: List of created security objects
    """
    logger.info("Creating holdings from account_positions data")
    
    positions_table = extract_table_data(json_data, 'account_positions')
    if not positions_table or 'rows' not in positions_table:
        logger.warning("No account_positions table found in JSON, skipping holdings from positions")
        return
    
    # Get column indices
    columns = [col['name'] for col in positions_table['columns']]
    security_col_idx = columns.index('Security')
    account_no_col_idx = columns.index('Account_No')
    quantity_col_idx = columns.index('Quantity')
    position_col_idx = columns.index('Position')
    
    # Create ticker lookup for securities
    ticker_lookup = {sec.ticker: sec for sec in securities}
    
    # Map Account_No to funds (assuming Account_No values map to funds by index)
    # Get unique Account_No values and sort them
    account_nos = sorted(set(row[account_no_col_idx] for row in positions_table['rows'] 
                             if len(row) > account_no_col_idx))
    account_to_fund = {}
    
    # Map Account_No to funds by index (if we have matching counts)
    if len(account_nos) <= len(funds):
        for idx, account_no in enumerate(account_nos):
            if idx < len(funds):
                account_to_fund[account_no] = funds[idx]
                logger.debug(f"Mapped Account_No {account_no} to fund {funds[idx].fund_name}")
    else:
        logger.warning(f"More Account_No values ({len(account_nos)}) than funds ({len(funds)}), mapping first {len(funds)}")
        for idx in range(len(funds)):
            account_to_fund[account_nos[idx]] = funds[idx]
    
    holdings_created = 0
    holdings_skipped = 0
    
    # Process each position
    for row in positions_table['rows']:
        if len(row) <= max(security_col_idx, account_no_col_idx, quantity_col_idx, position_col_idx):
            continue
        
        # Extract ticker from Security field (format: "TICKER - Name")
        security_field = row[security_col_idx]
        if ' - ' not in security_field:
            logger.debug(f"Skipping position with invalid Security format: {security_field}")
            holdings_skipped += 1
            continue
        
        ticker = security_field.split(' - ')[0].strip()
        
        # Only process Long positions (Short positions not supported per PRD)
        position = row[position_col_idx] if len(row) > position_col_idx else 'Long'
        if position != 'Long':
            logger.debug(f"Skipping {position} position for {ticker}")
            holdings_skipped += 1
            continue
        
        # Check if security exists
        if ticker not in ticker_lookup:
            logger.debug(f"Security {ticker} not found in securities, skipping")
            holdings_skipped += 1
            continue
        
        # Get fund for this Account_No
        account_no = row[account_no_col_idx]
        if account_no not in account_to_fund:
            logger.debug(f"Account_No {account_no} not mapped to any fund, skipping")
            holdings_skipped += 1
            continue
        
        fund = account_to_fund[account_no]
        quantity = row[quantity_col_idx]
        
        # Convert quantity to integer (no fractional shares per PRD)
        try:
            shares = int(float(quantity))
            if shares <= 0:
                logger.debug(f"Invalid shares quantity {shares} for {ticker}, skipping")
                holdings_skipped += 1
                continue
        except (ValueError, TypeError):
            logger.debug(f"Invalid quantity value {quantity} for {ticker}, skipping")
            holdings_skipped += 1
            continue
        
        # Check if holding already exists for this fund/ticker combination
        existing_holding = Holding.query.filter_by(
            fund_id = fund.fund_id,
            ticker = ticker
        ).first()
        
        if existing_holding:
            # Update existing holding by adding shares
            existing_holding.shares += Decimal(str(shares))
            logger.debug(f"Updated existing holding: {fund.fund_name} - {ticker} (+{shares} shares)")
        else:
            # Create new holding
            holding = Holding(
                fund_id = fund.fund_id,
                ticker = ticker,
                shares = Decimal(str(shares))
            )
            db.session.add(holding)
            logger.debug(f"Created holding: {fund.fund_name} - {ticker} ({shares} shares)")
            holdings_created += 1
    
    db.session.commit()
    logger.info(f"Created {holdings_created} holdings from account_positions, skipped {holdings_skipped} positions")


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
            'logic': "issuers.country_incorporation_code IN ('PRK', 'MMR', 'TKM')",
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
        # Check if rule already exists by name
        existing_rule = Rule.query.filter_by(rule_name=rule_data['rule_name']).first()
        if existing_rule:
            logger.info(f"Rule '{rule_data['rule_name']}' already exists, skipping")
            rules.append(existing_rule)
        else:
            rule = Rule(**rule_data)
            db.session.add(rule)
            rules.append(rule)
            logger.info(f"Created rule: {rule_data['rule_name']}")
    
    db.session.commit()
    logger.info(f"Ensured {len(rules)} compliance rules exist")
    return rules


def ensure_sample_rules_exist():
    """Ensure sample rules exist without dropping database. Can be called safely."""
    logger.info("Ensuring sample compliance rules exist")
    try:
        rules = create_sample_rules()
        logger.info(f"Sample rules check complete: {len(rules)} rules exist")
        return rules
    except Exception as e:
        logger.error(f"Error ensuring sample rules exist: {e}", exc_info=True)
        return []


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


def main(app=None):
    """
    Main seeding function.
    
    Args:
        app: Optional Flask app instance. If provided, uses this app instead of creating a new one.
             This prevents infinite loops when called from create_app().
    """
    import logging
    
    # Set up logging
    logging.basicConfig(
        level = logging.INFO,
        format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Starting data seeding process")
    
    # Use provided app or create a new one
    if app is None:
        # Skip auto-init to prevent infinite loop when creating app from seed script
        app = create_app(skip_auto_init=True)
        use_app_context = True
    else:
        # If app is provided, we're already in an app context from the caller
        use_app_context = False
    
    if use_app_context:
        with app.app_context():
            _seed_database(logger)
    else:
        # We're already in an app context, just run the seeding
        _seed_database(logger)


def _seed_database(logger):
    """Internal function to perform the actual database seeding."""
    # Clear existing data
    logger.info("Clearing existing data")
    db.drop_all()
    db.create_all()
    
    # Load JSON data
    json_data = load_json_data()
    
    # Build lookups from JSON
    gics_lookups = build_gics_lookup(json_data)
    country_lookup = build_country_lookup(json_data)
    
    # Create issuers and securities from JSON
    if json_data:
        logger.info("Creating issuers and securities from JSON data")
        issuers = create_issuers_from_json(json_data, gics_lookups, country_lookup)
        securities = create_securities_from_json(json_data, issuers, gics_lookups, country_lookup)
    else:
        logger.info("JSON data not available, using sample data")
        # Fall back to sample data if JSON is not available
        issuers = create_sample_issuers()
        securities = create_sample_securities(issuers)
    
    # Generate price data
    if securities:
        create_sample_prices(securities)
    
    # Create sample data for remaining tables
    funds = create_sample_funds()
    create_sample_holdings(funds, securities)
    
    # If JSON data is available, try to create additional holdings from account_positions
    if json_data:
        create_holdings_from_account_positions(json_data, funds, securities)
    
    rules = create_sample_rules()
    create_sample_rule_attachments(funds, rules)
    
    logger.info("Data seeding completed successfully")
    logger.info(f"Created: {len(issuers)} issuers, {len(securities)} securities, {len(funds)} funds, {len(rules)} rules")


if __name__ == '__main__':
    main()
