import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
import tempfile
from datetime import datetime, timedelta
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
def sample_metal_price():
    """Create a sample MetalPrice object for testing"""
    return MetalPrice(
        ticker='LMCADY03 Comdty',
        metal_name='copper',
        price=8500.0,
        currency='USD',
        timestamp=datetime.now(),
        bid=8499.0,
        ask=8501.0,
        volume=15000.0,
        open_price=8480.0,
        high=8520.0,
        low=8460.0,
        previous_close=8495.0
    )

@pytest.fixture
def sample_alert():
    """Create a sample Alert object for testing"""
    return Alert(
        id='test_alert_1',
        metal_name='copper',
        alert_type='price_threshold',
        threshold_value=8600.0,
        current_value=8650.0,
        triggered_at=datetime.now(),
        message='Copper price exceeded threshold'
    )

def test_database_connection(temp_db):
    """Test database connection and disconnection"""
    assert temp_db.connect() == True
    assert temp_db.connection is not None
    
    temp_db.disconnect()
    assert temp_db.connection is None

def test_database_schema_initialization(temp_db):
    """Test that database schema is properly initialized"""
    temp_db.connect()
    
    # Check that tables exist using DuckDB's information schema
    tables = temp_db.connection.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
    ).fetchall()
    
    table_names = [table[0] for table in tables]
    assert 'metals_prices' in table_names
    assert 'alerts' in table_names
    assert 'daily_summaries' in table_names

def test_store_single_metal_price(temp_db, sample_metal_price):
    """Test storing a single MetalPrice"""
    temp_db.connect()
    
    result = temp_db.store_metal_price(sample_metal_price)
    assert result == True
    
    # Verify data was stored
    count = temp_db.connection.execute(
        "SELECT COUNT(*) FROM metals_prices"
    ).fetchone()[0]
    assert count == 1

def test_store_multiple_metal_prices(temp_db):
    """Test storing multiple MetalPrice objects"""
    temp_db.connect()
    
    prices = []
    for i, metal in enumerate(['copper', 'aluminum', 'zinc']):
        price = MetalPrice(
            ticker=f'LME{metal.upper()}03 Comdty',
            metal_name=metal,
            price=8500.0 + i * 100,
            currency='USD',
            timestamp=datetime.now() + timedelta(minutes=i),
            bid=8499.0 + i * 100,
            ask=8501.0 + i * 100
        )
        prices.append(price)
    
    stored_count = temp_db.store_metal_prices(prices)
    assert stored_count == 3
    
    # Verify data was stored
    count = temp_db.connection.execute(
        "SELECT COUNT(*) FROM metals_prices"
    ).fetchone()[0]
    assert count == 3

def test_get_latest_prices(temp_db):
    """Test retrieving latest prices"""
    temp_db.connect()
    
    # Store test data with different timestamps
    base_time = datetime.now()
    for i, metal in enumerate(['copper', 'aluminum']):
        for j in range(3):  # 3 entries per metal
            price = MetalPrice(
                ticker=f'LME{metal.upper()}03 Comdty',
                metal_name=metal,
                price=8500.0 + j * 10,
                currency='USD',
                timestamp=base_time + timedelta(minutes=i*10 + j),
                bid=8499.0 + j * 10,
                ask=8501.0 + j * 10
            )
            temp_db.store_metal_price(price)
    
    # Get latest prices for all metals
    latest_prices = temp_db.get_latest_prices()
    assert len(latest_prices) == 2  # copper and aluminum
    
    # Get latest prices for specific metal
    copper_prices = temp_db.get_latest_prices(['copper'])
    assert len(copper_prices) == 1
    assert copper_prices[0].metal_name == 'copper'

def test_get_historical_prices(temp_db):
    """Test retrieving historical prices"""
    temp_db.connect()
    
    # Store historical data
    base_time = datetime.now() - timedelta(days=5)
    for i in range(10):
        price = MetalPrice(
            ticker='LMCADY03 Comdty',
            metal_name='copper',
            price=8500.0 + i * 10,
            currency='USD',
            timestamp=base_time + timedelta(hours=i),
            bid=8499.0 + i * 10,
            ask=8501.0 + i * 10
        )
        temp_db.store_metal_price(price)
    
    # Get historical data
    start_date = base_time - timedelta(days=1)
    end_date = base_time + timedelta(days=1)
    
    df = temp_db.get_historical_prices('copper', start_date, end_date)
    assert not df.empty
    assert len(df) == 10
    assert 'price' in df.columns
    assert 'timestamp' in df.columns

def test_price_statistics(temp_db):
    """Test price statistics calculation"""
    temp_db.connect()
    
    # Store test data
    base_time = datetime.now() - timedelta(days=2)
    prices = [8500, 8520, 8480, 8510, 8505]
    
    for i, price in enumerate(prices):
        metal_price = MetalPrice(
            ticker='LMCADY03 Comdty',
            metal_name='copper',
            price=float(price),
            currency='USD',
            timestamp=base_time + timedelta(hours=i),
            volume=15000.0 + i * 100
        )
        temp_db.store_metal_price(metal_price)
    
    # Get statistics
    stats = temp_db.get_price_statistics('copper', days=7)
    
    assert 'data_points' in stats
    assert 'avg_price' in stats
    assert 'min_price' in stats
    assert 'max_price' in stats
    assert stats['data_points'] == 5
    assert stats['min_price'] == 8480.0
    assert stats['max_price'] == 8520.0

def test_store_alert(temp_db, sample_alert):
    """Test storing alerts"""
    temp_db.connect()
    
    result = temp_db.store_alert(sample_alert)
    assert result == True
    
    # Verify alert was stored
    count = temp_db.connection.execute(
        "SELECT COUNT(*) FROM alerts"
    ).fetchone()[0]
    assert count == 1

def test_get_active_alerts(temp_db):
    """Test retrieving active alerts"""
    temp_db.connect()
    
    # Store test alerts
    alerts = [
        Alert(
            id='alert_1',
            metal_name='copper',
            alert_type='price_threshold',
            threshold_value=8600.0,
            current_value=8650.0,
            triggered_at=datetime.now(),
            message='Copper alert 1',
            is_active=True
        ),
        Alert(
            id='alert_2',
            metal_name='aluminum',
            alert_type='price_threshold',
            threshold_value=9000.0,
            current_value=9050.0,
            triggered_at=datetime.now(),
            message='Aluminum alert',
            is_active=True
        ),
        Alert(
            id='alert_3',
            metal_name='copper',
            alert_type='price_threshold',
            threshold_value=8500.0,
            current_value=8450.0,
            triggered_at=datetime.now() - timedelta(hours=1),
            message='Old copper alert',
            is_active=False
        )
    ]
    
    for alert in alerts:
        temp_db.store_alert(alert)
    
    # Get all active alerts
    active_alerts = temp_db.get_active_alerts()
    assert len(active_alerts) == 2  # Only active alerts
    
    # Get active alerts for specific metal
    copper_alerts = temp_db.get_active_alerts('copper')
    assert len(copper_alerts) == 1
    assert copper_alerts[0].metal_name == 'copper'
    assert copper_alerts[0].is_active == True

def test_generate_daily_summary(temp_db):
    """Test daily summary generation"""
    temp_db.connect()
    
    # Store data for a specific day
    test_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    prices = [8500, 8520, 8480, 8510, 8505]
    volumes = [15000, 16000, 14000, 15500, 15200]
    
    for i, (price, volume) in enumerate(zip(prices, volumes)):
        metal_price = MetalPrice(
            ticker='LMCADY03 Comdty',
            metal_name='copper',
            price=float(price),
            currency='USD',
            timestamp=test_date + timedelta(hours=i * 2),
            volume=float(volume)
        )
        temp_db.store_metal_price(metal_price)
    
    # Generate daily summary
    result = temp_db.generate_daily_summary(test_date, 'copper')
    assert result == True
    
    # Verify summary was created
    count = temp_db.connection.execute(
        "SELECT COUNT(*) FROM daily_summaries"
    ).fetchone()[0]
    assert count == 1

def test_health_check(temp_db):
    """Test database health check"""
    # Test when not connected
    health = temp_db.health_check()
    assert health['connected'] == False
    
    # Test when connected
    temp_db.connect()
    health = temp_db.health_check()
    
    assert health['connected'] == True
    assert 'database_path' in health
    assert 'tables' in health
    assert 'health_check_time' in health
    assert 'metals_prices' in health['tables']
    assert 'alerts' in health['tables']
    assert 'daily_summaries' in health['tables']

def test_connection_error_handling(temp_db):
    """Test error handling when not connected"""
    # Don't connect to database
    
    with pytest.raises(ConnectionError):
        temp_db.store_metal_price(MetalPrice(
            ticker='TEST', metal_name='test', price=100.0,
            currency='USD', timestamp=datetime.now()
        ))
    
    with pytest.raises(ConnectionError):
        temp_db.get_latest_prices()
    
    with pytest.raises(ConnectionError):
        temp_db.get_historical_prices('test', datetime.now(), datetime.now())