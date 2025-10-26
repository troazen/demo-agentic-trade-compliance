# Investment Operations Compliance System - Streamlit UI

Streamlit frontend for the Investment Operations Compliance System.

## Setup

1. Ensure you have Python 3.14 (or 3.13) installed
2. Install dependencies from the main project:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the backend API server:
   ```bash
   python run.py
   ```

4. Start the Streamlit UI:
   ```bash
   streamlit run streamlitui/app.py
   ```

## Configuration

The API base URL can be configured via:
- Environment variable: `API_BASE_URL` (default: `http://localhost:5000`)
- Or modify `streamlitui/config.py` directly

## Usage

### Navigation

The application uses Streamlit's built-in sidebar navigation with the following pages:

1. **Dashboard** - Overview of funds, securities, rules, and recent activity
2. **Funds** - View and manage investment funds
3. **Securities** - Search and view available securities
4. **Rules** - Manage compliance rules
5. **Alerts** - View and manage compliance alerts
6. **Compliance Results** - Results from portfolio compliance checks

### Features

- **Dark Theme**: Professional dark theme throughout
- **Real-time Data**: Connected to backend API for live data
- **Responsive Design**: Optimized for different screen sizes
- **Error Handling**: User-friendly error messages
- **Data Formatting**: Properly formatted currency, percentages, dates, and shares

## Architecture

```
streamlitui/
├── app.py                 # Main entry point
├── config.py              # Configuration
├── api_client.py          # API client wrapper
├── pages/                  # Streamlit pages
│   ├── 1_Dashboard.py
│   ├── 2_Funds.py
│   ├── 3_Securities.py
│   ├── 4_Rules.py
│   ├── 5_Alerts.py
│   └── 6_Compliance_Results.py
├── components/             # Reusable components (future enhancement)
└── utils/                  # Utility functions
    ├── formatting.py
    └── session_state.py
```

## Development

The UI communicates with the backend via REST API calls using the `api_client.py` wrapper. All API endpoints are documented and accessible at:

- Backend API: http://localhost:5000
- Swagger Documentation: http://localhost:5000/swagger/

