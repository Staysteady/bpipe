import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pytest
from src.app import app, THEME

def test_app_creation():
    """Test that the app is created successfully"""
    assert app is not None
    assert app.title == "Dash"

def test_theme_configuration():
    """Test that theme colors are properly configured"""
    assert THEME['background'] == '#1a1a1a'
    assert THEME['card_background'] == '#2d2d2d'
    assert THEME['text'] == '#ffffff'
    assert THEME['accent'] == '#00cc96'

def test_app_layout_exists():
    """Test that the app has a layout"""
    assert app.layout is not None