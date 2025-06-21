import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
import tempfile
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import pandas as pd

from src.app import (
    app, create_price_card, create_alerts_card, 
    update_price_cards, update_realtime_chart, 
    update_historical_chart, update_alerts_panel, 
    update_market_stats, THEME
)
from src.data.models import MetalPrice, Alert
from src.data.database import DatabaseManager

@pytest.fixture
def mock_db():
    """Create a mock database manager"""
    db = Mock(spec=DatabaseManager)
    return db

@pytest.fixture
def mock_bloomberg_client():
    """Create a mock Bloomberg client"""
    client = Mock()
    client.connected = True
    return client

@pytest.fixture
def sample_metal_prices():
    """Create sample metal price data"""
    base_time = datetime.now()
    return [
        MetalPrice(
            ticker='LMCADY03 Comdty',
            metal_name='copper',
            price=8500.0,
            currency='USD',
            timestamp=base_time,
            bid=8499.0,
            ask=8501.0,
            volume=15000.0
        ),
        MetalPrice(
            ticker='LMAHDY03 Comdty',
            metal_name='aluminum',
            price=2300.0,
            currency='USD',
            timestamp=base_time,
            bid=2299.0,
            ask=2301.0,
            volume=12000.0
        )
    ]

@pytest.fixture
def sample_alerts():
    """Create sample alert data"""
    return [
        Alert(
            id='alert_1',
            metal_name='copper',
            alert_type='price_threshold',
            threshold_value=8600.0,
            current_value=8650.0,
            triggered_at=datetime.now(),
            message='Copper price exceeded threshold'
        ),
        Alert(
            id='alert_2',
            metal_name='aluminum',
            alert_type='price_threshold',
            threshold_value=2400.0,
            current_value=2450.0,
            triggered_at=datetime.now() - timedelta(minutes=30),
            message='Aluminum price alert'
        )
    ]

def test_app_initialization():
    """Test that the Dash app initializes correctly"""
    assert app is not None
    assert app.title == "Dash"  # Default Dash title
    assert hasattr(app, 'layout')

def test_theme_configuration():
    """Test theme color configuration"""
    assert THEME['background'] == '#1a1a1a'
    assert THEME['card_background'] == '#2d2d2d'
    assert THEME['text'] == '#ffffff'
    assert THEME['accent'] == '#00cc96'
    assert 'success' in THEME
    assert 'warning' in THEME
    assert 'danger' in THEME

def test_create_price_card():
    """Test price card component creation"""
    card = create_price_card('copper', 8500.0, 15.0, 0.18)
    
    # Check that it returns a Div component
    assert card._namespace == 'dash_html_components'
    assert card._type == 'Div'
    
    # Check styling
    assert card.style['backgroundColor'] == THEME['card_background']
    assert card.style['borderRadius'] == '8px'
    
    # Check children components exist
    assert len(card.children) >= 2  # Should have at least metal name and price

def test_create_price_card_negative_change():
    """Test price card with negative price change"""
    card = create_price_card('aluminum', 2300.0, -25.0, -1.08)
    
    # Should still create a valid card
    assert card._type == 'Div'
    assert card.style['backgroundColor'] == THEME['card_background']

def test_create_alerts_card():
    """Test alerts card component creation"""
    card = create_alerts_card(3)
    
    assert card._type == 'Div'
    assert card.style['backgroundColor'] == THEME['card_background']
    assert len(card.children) >= 2  # Should have title and count

@patch('src.app.db')
@patch('src.app.bloomberg_client')
def test_update_price_cards_success(mock_bloomberg, mock_db, sample_metal_prices):
    """Test successful price cards update"""
    # Setup mocks
    mock_db.connection = True
    mock_db.connect.return_value = True
    mock_db.get_latest_prices.return_value = sample_metal_prices
    mock_db.get_active_alerts.return_value = []
    
    mock_bloomberg.connected = True
    mock_bloomberg.connect.return_value = True
    
    # Call the function
    price_cards, status = update_price_cards(0)
    
    # Verify results
    assert len(price_cards) == 3  # 2 metals + alerts card
    assert status.children[0].children == "✅ "
    
    # Verify database calls
    mock_db.get_latest_prices.assert_called_once()
    mock_db.get_active_alerts.assert_called_once()

@patch('src.app.db')
@patch('src.app.bloomberg_client')
def test_update_price_cards_connection_error(mock_bloomberg, mock_db):
    """Test price cards update with connection error"""
    # Setup mocks for connection failure
    mock_db.connection = None
    mock_db.connect.return_value = False
    mock_bloomberg.connected = False
    mock_bloomberg.connect.return_value = False
    
    # Call the function
    price_cards, status = update_price_cards(0)
    
    # Verify error handling
    assert price_cards == []
    assert "⚠️" in status.children[0].children

@patch('src.app.db')
def test_update_realtime_chart_with_data(mock_db):
    """Test real-time chart update with historical data"""
    # Create mock dataframe
    timestamps = [datetime.now() - timedelta(hours=i) for i in range(24, 0, -1)]
    df = pd.DataFrame({
        'timestamp': timestamps,
        'price': [8500 + i*2 for i in range(24)],
        'metal_name': ['copper'] * 24
    })
    
    mock_db.get_historical_prices.return_value = df
    
    # Call the function
    figure = update_realtime_chart('copper', 0)
    
    # Verify figure properties
    assert figure is not None
    assert len(figure.data) == 1  # One trace
    assert figure.data[0].name == 'COPPER Price'
    assert figure.layout.title.text == 'COPPER - Last 24 Hours'
    assert figure.layout.plot_bgcolor == THEME['background']

@patch('src.app.db')
def test_update_realtime_chart_no_data(mock_db):
    """Test real-time chart update with no data (uses mock data)"""
    # Return empty dataframe
    mock_db.get_historical_prices.return_value = pd.DataFrame()
    
    # Call the function
    figure = update_realtime_chart('aluminum', 0)
    
    # Verify figure created with mock data
    assert figure is not None
    assert len(figure.data) == 1
    assert figure.layout.title.text == 'ALUMINUM - Last 24 Hours'

@patch('src.app.db')
def test_update_historical_chart_24h(mock_db):
    """Test historical chart update for 24h timeframe"""
    # Setup mock for multiple metals
    mock_db.get_historical_prices.return_value = pd.DataFrame()  # Empty data (will use mock)
    
    # Call the function
    figure = update_historical_chart('24h', 0)
    
    # Verify figure properties
    assert figure is not None
    assert len(figure.data) == 6  # 6 metals
    assert figure.layout.title.text == 'LME Prices - Last 24 Hours'
    assert figure.layout.plot_bgcolor == THEME['background']

@patch('src.app.db')
def test_update_historical_chart_7d(mock_db):
    """Test historical chart update for 7 days timeframe"""
    mock_db.get_historical_prices.return_value = pd.DataFrame()
    
    figure = update_historical_chart('7d', 0)
    
    assert figure is not None
    assert figure.layout.title.text == 'LME Prices - Last 7 Days'

@patch('src.app.db')
def test_update_alerts_panel_with_alerts(mock_db, sample_alerts):
    """Test alerts panel update with active alerts"""
    mock_db.get_active_alerts.return_value = sample_alerts
    
    # Call the function
    alert_items = update_alerts_panel(0)
    
    # Verify results
    assert len(alert_items) == 2
    
    # Check first alert item structure
    first_alert = alert_items[0]
    assert first_alert._type == 'Div'
    assert first_alert.style['backgroundColor'] == THEME['background']

@patch('src.app.db')
def test_update_alerts_panel_no_alerts(mock_db):
    """Test alerts panel update with no active alerts"""
    mock_db.get_active_alerts.return_value = []
    
    # Call the function
    result = update_alerts_panel(0)
    
    # Should return a div with "No active alerts" message
    assert result._type == 'Div'
    assert "No active alerts" in result.children[0].children

@patch('src.app.db')
def test_update_market_stats_with_data(mock_db):
    """Test market statistics update with data"""
    # Mock statistics data
    mock_stats = {
        'avg_price': 8500.0,
        'max_price': 8600.0,
        'min_price': 8400.0,
        'total_volume': 150000.0
    }
    mock_db.get_price_statistics.return_value = mock_stats
    
    # Call the function
    stats_cards = update_market_stats(0)
    
    # Verify results
    assert len(stats_cards) == 4  # 4 metals
    
    # Check first card structure
    first_card = stats_cards[0]
    assert first_card._type == 'Div'
    assert first_card.style['backgroundColor'] == THEME['background']

@patch('src.app.db')
def test_update_market_stats_no_data(mock_db):
    """Test market statistics update with no data"""
    mock_db.get_price_statistics.return_value = {}
    
    # Call the function
    stats_cards = update_market_stats(0)
    
    # Should still create cards but with "No data available"
    assert len(stats_cards) == 4
    for card in stats_cards:
        assert card._type == 'Div'

def test_chart_error_handling():
    """Test chart error handling with invalid data"""
    with patch('src.app.db') as mock_db:
        # Make the database call raise an exception
        mock_db.get_historical_prices.side_effect = Exception("Database error")
        
        # Call the function
        figure = update_realtime_chart('copper', 0)
        
        # Should return error figure
        assert figure is not None
        assert "Chart Error" in figure.layout.title.text

def test_dashboard_performance():
    """Test that dashboard components can be created efficiently"""
    import time
    
    start_time = time.time()
    
    # Create multiple price cards
    for i in range(10):
        card = create_price_card(f'metal_{i}', 8500.0 + i*100, 15.0, 0.18)
        assert card is not None
    
    # Create alerts card
    alerts_card = create_alerts_card(5)
    assert alerts_card is not None
    
    end_time = time.time()
    
    # Should complete quickly (under 1 second for 10 cards)
    assert (end_time - start_time) < 1.0

def test_theme_color_validation():
    """Test that all theme colors are valid hex codes"""
    import re
    
    hex_pattern = re.compile(r'^#[0-9a-fA-F]{6}$')
    
    for color_name, color_value in THEME.items():
        assert hex_pattern.match(color_value), f"Invalid hex color for {color_name}: {color_value}"

@patch('src.app.logger')
def test_error_logging(mock_logger):
    """Test that errors are properly logged"""
    with patch('src.app.db') as mock_db:
        mock_db.get_latest_prices.side_effect = Exception("Test error")
        mock_db.connection = True
        mock_db.connect.return_value = True
        
        with patch('src.app.bloomberg_client') as mock_bloomberg:
            mock_bloomberg.connected = True
            mock_bloomberg.connect.return_value = True
            
            # Call function that should log error
            update_price_cards(0)
            
            # Verify error was logged
            mock_logger.error.assert_called()

def test_dashboard_responsive_design():
    """Test that dashboard components have responsive styling"""
    # Test price card styling
    card = create_price_card('copper', 8500.0, 15.0, 0.18)
    
    # Check for responsive properties
    assert 'minWidth' in card.style
    assert card.style['textAlign'] == 'center'
    
    # Test alerts card styling
    alerts_card = create_alerts_card(3)
    assert 'minWidth' in alerts_card.style
    assert alerts_card.style['textAlign'] == 'center'