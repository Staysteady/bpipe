import os
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

class Config:
    """Configuration settings for Bloomberg Terminal Integration Dashboard"""
    
    # Bloomberg Terminal Settings
    BLOOMBERG_HOST = os.getenv('BLOOMBERG_HOST', 'localhost')
    BLOOMBERG_PORT = int(os.getenv('BLOOMBERG_PORT', 8194))
    BLOOMBERG_TIMEOUT = int(os.getenv('BLOOMBERG_TIMEOUT', 30))
    
    # LME Metal Tickers
    LME_METALS = {
        'copper': 'LMCADY03 Comdty',
        'aluminum': 'LMAHDY03 Comdty', 
        'zinc': 'LMZSDY03 Comdty',
        'nickel': 'LMNIDY03 Comdty',
        'lead': 'LMPBDY03 Comdty',
        'tin': 'LMSNDY03 Comdty'
    }
    
    # Database Settings
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/metals_data.duckdb')
    
    # Update Frequencies (in seconds)
    REAL_TIME_UPDATE_FREQUENCY = int(os.getenv('REAL_TIME_UPDATE_FREQUENCY', 5))
    HISTORICAL_UPDATE_FREQUENCY = int(os.getenv('HISTORICAL_UPDATE_FREQUENCY', 3600))
    
    # Alert Settings
    DEFAULT_ALERT_THRESHOLDS = {
        'price_change_pct': 2.0,
        'volume_spike_multiplier': 3.0
    }

config = Config()