# Trade Compliance System

A Python-based trade and portfolio compliance system designed for educational and testing purposes, inspired by features found in State Street's Charles River Development (CRD/CRIMS) and BlackRock's Aladdin platforms.

## Overview

This application monitors compliance of trades placed in open-end 40 Act mutual funds and similar. When orders are placed, custom-coded compliance rules are applied to each order, and if any warnings or alerts are triggered, users are notified and must enter comments before transactions can proceed.

## Key Features

- **Trade Management**: Place BUY/SELL orders with real-time compliance checking
- **Compliance Engine**: Custom SQL-based rules with configurable alert thresholds
- **Portfolio Monitoring**: Track fund holdings and cash positions
- **Alert System**: Override capabilities with detailed audit trails
- **REST API**: External integration support for AI agents and automation

## Tech Stack

- **Backend**: Python 3.14 with Flask and SQLAlchemy
- **Frontend**: Streamlit for web interface
- **Database**: SQLite for data persistence
- **API**: RESTful endpoints for external integration

## Architecture

- **Database Layer**: SQLite with Flask-SQLAlchemy ORM
- **Backend Services**: Flask application with modular service architecture
- **Frontend**: Streamlit-based web interface
- **Compliance Engine**: Rule-based validation system with SQL logic evaluation

## Core Components

### Trade Flow
1. Trade submission and validation
2. Cash/shares availability verification
3. Compliance rule execution
4. Alert handling with override capabilities
5. Trade processing and portfolio updates

### Compliance Rules
- **Rule Types**: Sector limits, concentration limits, prohibited securities, diversification requirements
- **Denominators**: Total Assets, Net Assets, Shares Outstanding, Prohibit
- **Modes**: Trade compliance and portfolio compliance
- **Logic**: SQL WHERE clause-based filtering

### Data Models
- **Funds**: Portfolio containers with cash and holdings
- **Securities**: Tradeable assets with pricing and attributes
- **Trades**: BUY/SELL transactions with status tracking
- **Rules**: Compliance logic with fund attachments
- **Alerts**: Violation records with override capabilities

## Getting Started

### Prerequisites
- Python 3.13 (or later)
- Virtual environment (recommended)

### Installation
1. Clone the repository
2. Set up virtual environment: `python -m venv venv`
3. Activate virtual environment:
   - Windows: `& .\venv\Scripts\activate.ps1`
   - macOS/Linux: `source venv/bin/activate`
4. Install dependencies: `python -m pip install -r requirements.txt`

### Running the Application

**Note**: This application requires running both backend and frontend separately.

#### Backend (Flask API)
```bash
python run.py
```
The Flask backend will start on `http://localhost:5000` with the REST API available at `http://localhost:5000/api`

#### Frontend (Streamlit)
```bash
streamlit run [frontend_app.py]
```
*Note: The Streamlit frontend application is not yet implemented. The backend API is ready for frontend integration.*

### API Testing
You can test the API endpoints directly:
- Health check: `GET http://localhost:5000/api/health`
- API documentation available at the respective endpoints

**Health Check Successful Response**
```
{
  "message": "Investment Operations Compliance System API is running",
  "status": "healthy"
}
```

## API Integration

The system provides REST API endpoints for:
- Fund and holdings management
- Trade execution and validation
- Compliance rule management
- Alert handling and overrides
- Security information lookup

## Use Cases

- **Educational**: Learn about portfolio compliance and risk management
- **Testing**: Validate compliance rules and trade scenarios
- **Development**: Build and test AI agent integrations
- **Prototyping**: Rapid development of compliance workflows

## Project Status

This is a development/educational project and is not intended for production use. The system prioritizes simplicity and rapid development over enterprise-grade security and scalability.

For detailed requirements and specifications, see [PRD.md](prd.md).
