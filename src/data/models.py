from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd
import hashlib
import secrets

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

@dataclass
class User:
    """Data model for user authentication"""
    id: str
    username: str
    email: str
    password_hash: str
    salt: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True
    role: str = 'user'  # 'user', 'admin'
    
    @classmethod
    def create_user(cls, username: str, email: str, password: str, role: str = 'user') -> 'User':
        """Create a new user with hashed password"""
        user_id = secrets.token_urlsafe(16)
        salt = secrets.token_hex(32)
        password_hash = cls._hash_password(password, salt)
        
        return cls(
            id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            created_at=datetime.now(),
            role=role
        )
    
    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Hash password with salt using SHA-256"""
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash"""
        return self._hash_password(password, self.salt) == self.password_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'salt': self.salt,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'role': self.role
        }

@dataclass
class UserSession:
    """Data model for user sessions"""
    session_id: str
    user_id: str
    created_at: datetime
    expires_at: datetime
    is_active: bool = True
    
    @classmethod
    def create_session(cls, user_id: str, duration_hours: int = 24) -> 'UserSession':
        """Create a new user session"""
        session_id = secrets.token_urlsafe(32)
        created_at = datetime.now()
        expires_at = created_at + pd.Timedelta(hours=duration_hours)
        
        return cls(
            session_id=session_id,
            user_id=user_id,
            created_at=created_at,
            expires_at=expires_at
        )
    
    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'is_active': self.is_active
        }