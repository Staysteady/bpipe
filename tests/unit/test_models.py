import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from datetime import datetime
from src.data.models import MetalPrice, Alert

def test_metal_price_creation():
    """Test MetalPrice object creation"""
    price = MetalPrice(
        ticker='LMCADY03 Comdty',
        metal_name='copper',
        price=8500.0,
        currency='USD',
        timestamp=datetime.now(),
        bid=8499.0,
        ask=8501.0
    )
    
    assert price.ticker == 'LMCADY03 Comdty'
    assert price.metal_name == 'copper'
    assert price.price == 8500.0
    assert price.currency == 'USD'
    assert price.bid == 8499.0
    assert price.ask == 8501.0

def test_metal_price_to_dict():
    """Test MetalPrice to_dict conversion"""
    timestamp = datetime.now()
    price = MetalPrice(
        ticker='LMCADY03 Comdty',
        metal_name='copper',
        price=8500.0,
        currency='USD',
        timestamp=timestamp
    )
    
    price_dict = price.to_dict()
    
    assert price_dict['ticker'] == 'LMCADY03 Comdty'
    assert price_dict['metal_name'] == 'copper'
    assert price_dict['price'] == 8500.0
    assert price_dict['currency'] == 'USD'
    assert price_dict['timestamp'] == timestamp.isoformat()

def test_metal_price_from_bloomberg_data():
    """Test MetalPrice creation from Bloomberg data"""
    bloomberg_data = {
        'PX_LAST': 8500.0,
        'PX_BID': 8499.0,
        'PX_ASK': 8501.0,
        'PX_VOLUME': 15000.0,
        'CRNCY': 'USD'
    }
    
    price = MetalPrice.from_bloomberg_data(
        ticker='LMCADY03 Comdty',
        metal_name='copper',
        bloomberg_data=bloomberg_data
    )
    
    assert price.ticker == 'LMCADY03 Comdty'
    assert price.metal_name == 'copper'
    assert price.price == 8500.0
    assert price.bid == 8499.0
    assert price.ask == 8501.0
    assert price.volume == 15000.0
    assert price.currency == 'USD'

def test_alert_creation():
    """Test Alert object creation"""
    alert = Alert(
        id='alert_1',
        metal_name='copper',
        alert_type='price_threshold',
        threshold_value=8600.0,
        current_value=8650.0,
        triggered_at=datetime.now(),
        message='Copper price exceeded threshold'
    )
    
    assert alert.id == 'alert_1'
    assert alert.metal_name == 'copper'
    assert alert.alert_type == 'price_threshold'
    assert alert.threshold_value == 8600.0
    assert alert.current_value == 8650.0
    assert alert.is_active == True

def test_alert_to_dict():
    """Test Alert to_dict conversion"""
    timestamp = datetime.now()
    alert = Alert(
        id='alert_1',
        metal_name='copper',
        alert_type='price_threshold',
        threshold_value=8600.0,
        current_value=8650.0,
        triggered_at=timestamp,
        message='Copper price exceeded threshold'
    )
    
    alert_dict = alert.to_dict()
    
    assert alert_dict['id'] == 'alert_1'
    assert alert_dict['metal_name'] == 'copper'
    assert alert_dict['alert_type'] == 'price_threshold'
    assert alert_dict['triggered_at'] == timestamp.isoformat()
    assert alert_dict['is_active'] == True