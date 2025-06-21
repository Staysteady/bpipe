# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Bloomberg Terminal Integration Dashboard - a real-time LME (London Metal Exchange) metals trading dashboard built with Dash/Plotly. The application connects to Bloomberg Terminal API to fetch live metals prices and provides visualization and alerting capabilities.

## Development Commands

### Running the Application
```bash
python run_dashboard.py
```
The dashboard will be available at http://localhost:8050

### Testing
```bash
pytest tests/
pytest tests/unit/
pytest tests/integration/
```

### Installing Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Core Components

1. **src/app.py** - Main Dash application with dashboard UI, callbacks for real-time updates
2. **src/data/bloomberg_client.py** - Bloomberg Terminal API client (currently uses mock data)
3. **src/data/database.py** - DuckDB database manager for time-series metals data
4. **src/data/models.py** - Data models (MetalPrice, Alert)
5. **src/config.py** - Configuration management with LME metal tickers

### Data Flow
- BloombergClient fetches LME prices using configured tickers from config.LME_METALS
- DatabaseManager stores time-series data in DuckDB with tables: metals_prices, alerts, daily_summaries
- Dashboard auto-refreshes every 30 seconds via dcc.Interval component
- Price cards show current prices with change indicators
- Interactive charts display historical price data

### Database Schema
- **metals_prices**: Time-series price data with ticker, price, volume, OHLC data
- **alerts**: Price threshold and change alerts with active status
- **daily_summaries**: Aggregated daily statistics for performance optimization

### Configuration
- LME metal tickers defined in config.LME_METALS
- Database path configurable via DATABASE_PATH environment variable
- Bloomberg connection settings (host, port, timeout) via environment variables
- Update frequencies configurable (REAL_TIME_UPDATE_FREQUENCY, HISTORICAL_UPDATE_FREQUENCY)

## Key Development Notes

- Application currently uses mock Bloomberg data (BloombergClient.use_mock=True)
- DuckDB provides efficient time-series storage and querying capabilities
- Dark theme styling defined in THEME dictionary in app.py
- Callback pattern used for real-time dashboard updates
- Error handling includes connection status indicators and graceful fallbacks