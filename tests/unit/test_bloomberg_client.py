import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from datetime import datetime, timedelta
from src.data.bloomberg_client import BloombergClient, MockBloombergAPI
from src.data.models import MetalPrice

def test_mock_bloomberg_api_connection():
    """Test MockBloombergAPI connection"""
    api = MockBloombergAPI()
    
    assert not api.is_connected
    assert api.connect() == True
    assert api.is_connected == True
    
    api.disconnect()
    assert api.is_connected == False

def test_mock_bloomberg_api_data_retrieval():
    """Test MockBloombergAPI data retrieval"""
    api = MockBloombergAPI()
    api.connect()
    
    tickers = ['LMCADY03 Comdty', 'LMAHDY03 Comdty']
    fields = ['PX_LAST', 'PX_BID', 'PX_ASK']
    
    data = api.get_reference_data(tickers, fields)
    
    assert len(data) == 2
    for ticker in tickers:
        assert ticker in data
        assert 'PX_LAST' in data[ticker]
        assert 'PX_BID' in data[ticker]
        assert 'PX_ASK' in data[ticker]
        assert isinstance(data[ticker]['PX_LAST'], float)

def test_bloomberg_client_initialization():
    """Test BloombergClient initialization"""
    client = BloombergClient(use_mock=True)
    
    assert client.use_mock == True
    assert client.api is not None
    assert client.is_connected == False

def test_bloomberg_client_connection():
    """Test BloombergClient connection"""
    client = BloombergClient(use_mock=True)
    
    assert client.connect() == True
    assert client.is_connected == True
    
    client.disconnect()
    assert client.is_connected == False

def test_bloomberg_client_lme_prices():
    """Test BloombergClient LME price retrieval"""
    client = BloombergClient(use_mock=True)
    client.connect()
    
    # Test getting prices for specific metals
    metals = ['copper', 'aluminum']
    prices = client.get_lme_prices(metals)
    
    assert len(prices) == 2
    assert all(isinstance(price, MetalPrice) for price in prices)
    assert {price.metal_name for price in prices} == {'copper', 'aluminum'}
    
    # Test all metals
    all_prices = client.get_lme_prices()
    assert len(all_prices) == 6  # All configured metals

def test_bloomberg_client_connection_error():
    """Test error handling when not connected"""
    client = BloombergClient(use_mock=True)
    
    with pytest.raises(ConnectionError):
        client.get_lme_prices(['copper'])

def test_bloomberg_client_invalid_metal():
    """Test error handling for invalid metal"""
    client = BloombergClient(use_mock=True)
    client.connect()
    
    with pytest.raises(ValueError):
        client.get_lme_prices(['invalid_metal'])

def test_bloomberg_client_historical_prices():
    """Test historical price retrieval"""
    client = BloombergClient(use_mock=True)
    client.connect()
    
    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    
    df = client.get_historical_prices('copper', start_date, end_date)
    
    assert not df.empty
    assert 'date' in df.columns
    assert 'price' in df.columns
    assert 'metal' in df.columns
    assert df['metal'].iloc[0] == 'copper'

def test_bloomberg_client_health_check():
    """Test health check functionality"""
    client = BloombergClient(use_mock=True)
    
    health = client.health_check()
    
    assert 'connected' in health
    assert 'mock_mode' in health
    assert 'timestamp' in health
    assert 'available_metals' in health
    assert health['mock_mode'] == True
    assert health['connected'] == False
    
    client.connect()
    health = client.health_check()
    assert health['connected'] == True