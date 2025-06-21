import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
import tempfile
from datetime import datetime, timedelta
from src.data.bloomberg_client import BloombergClient
from src.data.database import DatabaseManager
from src.data.models import MetalPrice, Alert

@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    import tempfile
    
    # Create a temporary file name but don't create the file
    temp_dir = tempfile.gettempdir()
    db_path = os.path.join(temp_dir, f'test_db_{os.getpid()}_{id(object())}.duckdb')
    
    db = DatabaseManager(db_path)
    yield db
    
    # Cleanup
    db.disconnect()
    try:
        os.unlink(db_path)
    except OSError:
        pass

@pytest.fixture
def bloomberg_client():
    """Create Bloomberg client for testing"""
    return BloombergClient(use_mock=True)

def test_bloomberg_to_database_workflow(temp_db, bloomberg_client):
    """Test complete workflow from Bloomberg to database storage"""
    # Connect to both services
    assert temp_db.connect() == True
    assert bloomberg_client.connect() == True
    
    # Get data from Bloomberg
    metals = ['copper', 'aluminum']
    prices = bloomberg_client.get_lme_prices(metals)
    
    assert len(prices) == 2
    assert all(isinstance(price, MetalPrice) for price in prices)
    
    # Store data in database
    stored_count = temp_db.store_metal_prices(prices)
    assert stored_count == 2
    
    # Verify data was stored correctly
    stored_prices = temp_db.get_latest_prices(metals)
    assert len(stored_prices) == 2
    
    stored_metals = {p.metal_name for p in stored_prices}
    assert stored_metals == {'copper', 'aluminum'}
    
    # Verify data integrity
    for stored_price in stored_prices:
        original_price = next(p for p in prices if p.metal_name == stored_price.metal_name)
        assert stored_price.price == original_price.price
        assert stored_price.ticker == original_price.ticker
        assert stored_price.currency == original_price.currency

def test_historical_data_storage_and_retrieval(temp_db, bloomberg_client):
    """Test storing and retrieving historical data"""
    temp_db.connect()
    bloomberg_client.connect()
    
    # Simulate storing historical data over multiple time periods
    base_time = datetime.now() - timedelta(hours=24)
    
    for i in range(24):  # 24 hours of data
        # Get "current" prices (simulated)
        prices = bloomberg_client.get_lme_prices(['copper'])
        
        # Modify timestamp to simulate historical data
        for price in prices:
            price.timestamp = base_time + timedelta(hours=i)
            price.price = price.price + (i - 12) * 5  # Add some variation
        
        temp_db.store_metal_prices(prices)
    
    # Retrieve historical data
    start_date = base_time
    end_date = base_time + timedelta(hours=24)
    
    historical_df = temp_db.get_historical_prices('copper', start_date, end_date)
    
    assert not historical_df.empty
    assert len(historical_df) == 24
    assert historical_df['metal_name'].iloc[0] == 'copper'
    
    # Verify data is chronologically ordered
    timestamps = historical_df['timestamp'].tolist()
    assert timestamps == sorted(timestamps)

def test_price_monitoring_and_alerts(temp_db, bloomberg_client):
    """Test price monitoring and alert generation"""
    temp_db.connect()
    bloomberg_client.connect()
    
    # Get current prices
    prices = bloomberg_client.get_lme_prices(['copper'])
    copper_price = prices[0]
    
    # Store the price
    temp_db.store_metal_price(copper_price)
    
    # Create an alert based on current price
    alert = Alert(
        id='price_monitor_1',
        metal_name='copper',
        alert_type='price_threshold',
        threshold_value=copper_price.price - 100,  # Set threshold below current price
        current_value=copper_price.price,
        triggered_at=datetime.now(),
        message=f'Copper price {copper_price.price} exceeded threshold'
    )
    
    # Store alert
    assert temp_db.store_alert(alert) == True
    
    # Retrieve active alerts
    active_alerts = temp_db.get_active_alerts('copper')
    assert len(active_alerts) == 1
    assert active_alerts[0].metal_name == 'copper'

def test_daily_summary_generation(temp_db, bloomberg_client):
    """Test daily summary generation with Bloomberg data"""
    temp_db.connect()
    bloomberg_client.connect()
    
    # Simulate a full day of trading data
    test_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    
    # Generate data for different times of day (open, mid-day, close)
    trading_times = [
        test_date,  # Market open
        test_date + timedelta(hours=4),  # Mid-morning
        test_date + timedelta(hours=8),  # Close
    ]
    
    stored_prices = []
    
    for i, trading_time in enumerate(trading_times):
        prices = bloomberg_client.get_lme_prices(['copper'])
        copper_price = prices[0]
        
        # Modify timestamp and add some price variation
        copper_price.timestamp = trading_time
        copper_price.price = copper_price.price + (i - 1) * 20  # Simulate price movement
        copper_price.volume = 15000 + i * 2000
        
        temp_db.store_metal_price(copper_price)
        stored_prices.append(copper_price)
    
    # Generate daily summary
    result = temp_db.generate_daily_summary(test_date, 'copper')
    assert result == True
    
    # Verify summary exists
    summary_count = temp_db.connection.execute(
        "SELECT COUNT(*) FROM daily_summaries WHERE metal_name = 'copper'"
    ).fetchone()[0]
    assert summary_count == 1

def test_performance_with_large_dataset(temp_db, bloomberg_client):
    """Test database performance with larger dataset"""
    temp_db.connect()
    bloomberg_client.connect()
    
    # Generate larger dataset (simulate 1 week of hourly data)
    start_time = datetime.now() - timedelta(days=7)
    
    # Store data in batches for better performance
    batch_size = 24  # 24 hours per batch
    total_records = 0
    
    for day in range(7):
        daily_prices = []
        
        for hour in range(24):
            timestamp = start_time + timedelta(days=day, hours=hour)
            
            # Get prices for all metals
            prices = bloomberg_client.get_lme_prices()
            
            # Modify timestamps
            for price in prices:
                price.timestamp = timestamp
                price.price = price.price + (hour - 12) * 2  # Add hourly variation
            
            daily_prices.extend(prices)
        
        # Store daily batch
        stored_count = temp_db.store_metal_prices(daily_prices)
        total_records += stored_count
    
    # Verify all data was stored
    actual_count = temp_db.connection.execute(
        "SELECT COUNT(*) FROM metals_prices"
    ).fetchone()[0]
    
    assert actual_count == total_records
    assert actual_count == 7 * 24 * 6  # 7 days * 24 hours * 6 metals
    
    # Test query performance on large dataset
    start_query_time = datetime.now()
    
    # Get latest prices (should be fast with index)
    latest_prices = temp_db.get_latest_prices()
    assert len(latest_prices) == 6  # 6 metals
    
    # Get statistics (should be reasonable with aggregation)
    stats = temp_db.get_price_statistics('copper', days=7)
    assert stats['data_points'] == 7 * 24  # 7 days * 24 hours
    
    query_time = (datetime.now() - start_query_time).total_seconds()
    assert query_time < 5.0  # Queries should complete within 5 seconds

def test_error_recovery_and_resilience(temp_db, bloomberg_client):
    """Test error recovery and data consistency"""
    temp_db.connect()
    bloomberg_client.connect()
    
    # Test partial failure scenario
    prices = bloomberg_client.get_lme_prices(['copper', 'aluminum'])
    
    # Store first price successfully
    assert temp_db.store_metal_price(prices[0]) == True
    
    # Simulate failure by disconnecting database
    temp_db.disconnect()
    
    # Attempt to store second price (should fail gracefully)
    try:
        temp_db.store_metal_price(prices[1])
        assert False, "Expected ConnectionError"
    except ConnectionError:
        pass  # Expected behavior
    
    # Reconnect and verify data consistency
    temp_db.connect()
    
    stored_prices = temp_db.get_latest_prices()
    assert len(stored_prices) == 1  # Only first price should be stored
    assert stored_prices[0].metal_name == prices[0].metal_name

def test_data_integrity_constraints(temp_db, bloomberg_client):
    """Test data integrity and constraints"""
    temp_db.connect()
    bloomberg_client.connect()
    
    # Get valid price data
    prices = bloomberg_client.get_lme_prices(['copper'])
    original_price = prices[0]
    
    # Store original price
    temp_db.store_metal_price(original_price)
    
    # Test duplicate storage (should work - time series allows duplicates)
    duplicate_result = temp_db.store_metal_price(original_price)
    assert duplicate_result == True
    
    # Verify both records exist
    copper_count = temp_db.connection.execute(
        "SELECT COUNT(*) FROM metals_prices WHERE metal_name = 'copper'"
    ).fetchone()[0]
    assert copper_count == 2