#!/usr/bin/env python3
"""
Demo script to test Bloomberg Terminal Integration Dashboard
Run this to verify Bloomberg API integration is working
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.data.bloomberg_client import BloombergClient
from src.config import config
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Demo Bloomberg integration functionality"""
    print("=" * 60)
    print("Bloomberg Terminal Integration Dashboard - Demo")
    print("=" * 60)
    
    # Initialize Bloomberg client
    print("\n1. Initializing Bloomberg client (mock mode)...")
    client = BloombergClient(use_mock=True)
    
    # Test connection
    print("\n2. Connecting to Bloomberg Terminal...")
    if client.connect():
        print("✅ Connection successful!")
    else:
        print("❌ Connection failed!")
        return
    
    # Health check
    print("\n3. Running health check...")
    health = client.health_check()
    print(f"   Connected: {health['connected']}")
    print(f"   Mock mode: {health['mock_mode']}")
    print(f"   Available metals: {len(health['available_metals'])}")
    
    # Get current LME prices
    print("\n4. Retrieving current LME prices...")
    try:
        prices = client.get_lme_prices()
        print(f"   Retrieved prices for {len(prices)} metals:")
        
        for price in prices:
            print(f"   {price.metal_name.upper():>8}: ${price.price:8.2f} USD")
            print(f"            Bid: ${price.bid:8.2f} | Ask: ${price.ask:8.2f}")
    
    except Exception as e:
        print(f"❌ Error retrieving prices: {e}")
        return
    
    # Test specific metal
    print("\n5. Getting copper prices specifically...")
    try:
        copper_prices = client.get_lme_prices(['copper'])
        copper = copper_prices[0]
        print(f"   Copper: ${copper.price:.2f} USD")
        print(f"   Ticker: {copper.ticker}")
        print(f"   Volume: {copper.volume:,.0f}")
    
    except Exception as e:
        print(f"❌ Error retrieving copper prices: {e}")
    
    # Test historical data
    print("\n6. Retrieving historical data (last 7 days)...")
    try:
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        historical_df = client.get_historical_prices('copper', start_date, end_date)
        print(f"   Retrieved {len(historical_df)} historical data points")
        print(f"   Date range: {historical_df['date'].min()} to {historical_df['date'].max()}")
        print(f"   Price range: ${historical_df['price'].min():.2f} - ${historical_df['price'].max():.2f}")
    
    except Exception as e:
        print(f"❌ Error retrieving historical data: {e}")
    
    # Test configuration
    print("\n7. Configuration summary...")
    print(f"   Configured metals: {list(config.LME_METALS.keys())}")
    print(f"   Update frequency: {config.REAL_TIME_UPDATE_FREQUENCY}s")
    print(f"   Database path: {config.DATABASE_PATH}")
    
    # Cleanup
    print("\n8. Disconnecting...")
    client.disconnect()
    print("✅ Demo completed successfully!")
    
    print("\n" + "=" * 60)
    print("Next steps:")
    print("- Install actual Bloomberg API (blpapi) for real data")
    print("- Set up DuckDB database for data storage")
    print("- Build interactive Dash dashboard")
    print("- Implement real-time alerts")
    print("=" * 60)

if __name__ == "__main__":
    main()