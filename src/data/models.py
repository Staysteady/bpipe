from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd

@dataclass
class MetalPrice:
    """Data model for metals pricing data"""
    ticker: str
    metal_name: str
    price: float
    currency: str
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    volume: Optional[float] = None
    open_price: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    previous_close: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'ticker': self.ticker,
            'metal_name': self.metal_name,
            'price': self.price,
            'currency': self.currency,
            'timestamp': self.timestamp.isoformat(),
            'bid': self.bid,
            'ask': self.ask,
            'volume': self.volume,
            'open_price': self.open_price,
            'high': self.high,
            'low': self.low,
            'previous_close': self.previous_close
        }
    
    @classmethod
    def from_bloomberg_data(cls, ticker: str, metal_name: str, bloomberg_data: Dict[str, Any]) -> 'MetalPrice':
        """Create MetalPrice from Bloomberg API response"""
        return cls(
            ticker=ticker,
            metal_name=metal_name,
            price=bloomberg_data.get('PX_LAST', 0.0),
            currency=bloomberg_data.get('CRNCY', 'USD'),
            timestamp=datetime.now(),
            bid=bloomberg_data.get('PX_BID'),
            ask=bloomberg_data.get('PX_ASK'),
            volume=bloomberg_data.get('PX_VOLUME'),
            open_price=bloomberg_data.get('PX_OPEN'),
            high=bloomberg_data.get('PX_HIGH'),
            low=bloomberg_data.get('PX_LOW'),
            previous_close=bloomberg_data.get('PX_PREV_CLOSE')
        )

@dataclass
class Alert:
    """Data model for price alerts"""
    id: str
    metal_name: str
    alert_type: str  # 'price_threshold', 'percentage_change', 'volume_spike'
    threshold_value: float
    current_value: float
    triggered_at: datetime
    message: str
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'metal_name': self.metal_name,
            'alert_type': self.alert_type,
            'threshold_value': self.threshold_value,
            'current_value': self.current_value,
            'triggered_at': self.triggered_at.isoformat(),
            'message': self.message,
            'is_active': self.is_active
        }