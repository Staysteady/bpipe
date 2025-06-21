import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from datetime import datetime, timedelta
from src.data.bloomberg_client import BloombergClient
from src.data.models import MetalPrice
from src.config import config

def test_end_to_end_lme_data_retrieval():
    """Test complete LME data retrieval workflow"""
    client = BloombergClient(use_mock=True)
    
    # Test connection
    assert client.connect() == True
    
    # Test health check
    health = client.health_check()
    assert health['connected'] == True
    assert health['mock_mode'] == True
    assert len(health['available_metals']) == 6
    
    # Test retrieving data for all metals
    all_prices = client.get_lme_prices()
    assert len(all_prices) == 6
    
    # Verify data quality
    for price in all_prices:
        assert isinstance(price, MetalPrice)
        assert price.price > 0
        assert price.currency == 'USD'
        assert price.metal_name in config.LME_METALS
        assert price.ticker == config.LME_METALS[price.metal_name]
        assert price.timestamp is not None
    
    # Test specific metals
    copper_prices = client.get_lme_prices(['copper'])
    assert len(copper_prices) == 1
    assert copper_prices[0].metal_name == 'copper'
    
    # Test historical data
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    
    historical_df = client.get_historical_prices('copper', start_date, end_date)
    assert not historical_df.empty
    assert 'price' in historical_df.columns
    assert 'date' in historical_df.columns
    assert historical_df['metal'].iloc[0] == 'copper'
    
    # Test disconnection
    client.disconnect()
    assert client.health_check()['connected'] == False

def test_data_model_integration():
    """Test data model integration with Bloomberg client"""
    client = BloombergClient(use_mock=True)
    client.connect()
    
    prices = client.get_lme_prices(['copper', 'aluminum'])
    
    # Test MetalPrice objects can be converted to dicts
    for price in prices:
        price_dict = price.to_dict()
        
        # Verify all required fields are present
        required_fields = ['ticker', 'metal_name', 'price', 'currency', 'timestamp']
        for field in required_fields:
            assert field in price_dict
        
        # Verify data types
        assert isinstance(price_dict['price'], float)
        assert isinstance(price_dict['timestamp'], str)

def test_error_handling_integration():
    """Test error handling in integration scenarios"""
    client = BloombergClient(use_mock=True)
    
    # Test operations without connection
    with pytest.raises(ConnectionError):
        client.get_lme_prices(['copper'])
    
    with pytest.raises(ConnectionError):
        client.get_historical_prices('copper', datetime.now(), datetime.now())
    
    # Connect and test invalid operations
    client.connect()
    
    with pytest.raises(ValueError):
        client.get_lme_prices(['nonexistent_metal'])
    
    with pytest.raises(ValueError):
        client.get_historical_prices('nonexistent_metal', datetime.now(), datetime.now())

def test_configuration_integration():
    """Test that configuration is properly used by Bloomberg client"""
    client = BloombergClient(use_mock=True)
    client.connect()
    
    # Test that all configured metals can be retrieved
    all_metals = list(config.LME_METALS.keys())
    prices = client.get_lme_prices(all_metals)
    
    retrieved_metals = {price.metal_name for price in prices}
    expected_metals = set(all_metals)
    
    assert retrieved_metals == expected_metals
    
    # Test that tickers match configuration
    for price in prices:
        expected_ticker = config.LME_METALS[price.metal_name]
        assert price.ticker == expected_ticker