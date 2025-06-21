import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from src.config import config, Config

def test_config_singleton():
    """Test that config is properly instantiated"""
    assert config is not None
    assert isinstance(config, Config)

def test_bloomberg_settings():
    """Test Bloomberg Terminal configuration settings"""
    assert config.BLOOMBERG_HOST == 'localhost'
    assert config.BLOOMBERG_PORT == 8194
    assert config.BLOOMBERG_TIMEOUT == 30

def test_lme_metals_configuration():
    """Test that all expected LME metals are configured"""
    expected_metals = ['copper', 'aluminum', 'zinc', 'nickel', 'lead', 'tin']
    
    for metal in expected_metals:
        assert metal in config.LME_METALS
        assert 'Comdty' in config.LME_METALS[metal]

def test_alert_thresholds():
    """Test alert threshold configuration"""
    assert 'price_change_pct' in config.DEFAULT_ALERT_THRESHOLDS
    assert 'volume_spike_multiplier' in config.DEFAULT_ALERT_THRESHOLDS
    assert config.DEFAULT_ALERT_THRESHOLDS['price_change_pct'] > 0