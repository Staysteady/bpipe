import duckdb
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
from pathlib import Path

try:
    from ..config import config
    from .models import MetalPrice, Alert, User, UserSession
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from config import config
    from data.models import MetalPrice, Alert, User, UserSession

class DatabaseManager:
    """DuckDB database manager for metals trading data"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        self.connection = None
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def connect(self) -> bool:
        """Connect to DuckDB database"""
        try:
            self.connection = duckdb.connect(self.db_path)
            self.logger.info(f"Connected to database: {self.db_path}")
            self._initialize_schema()
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from database"""
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.info("Disconnected from database")
    
    def _initialize_schema(self):
        """Initialize database schema with required tables"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        # Create metals_prices table for time-series data
        self.connection.execute("""
            CREATE SEQUENCE IF NOT EXISTS metals_prices_id_seq;
            
            CREATE TABLE IF NOT EXISTS metals_prices (
                id INTEGER PRIMARY KEY DEFAULT nextval('metals_prices_id_seq'),
                ticker VARCHAR NOT NULL,
                metal_name VARCHAR NOT NULL,
                price DOUBLE NOT NULL,
                currency VARCHAR NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                bid DOUBLE,
                ask DOUBLE,
                volume DOUBLE,
                open_price DOUBLE,
                high DOUBLE,
                low DOUBLE,
                previous_close DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for efficient time-series queries
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_metals_prices_timestamp 
            ON metals_prices(timestamp)
        """)
        
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_metals_prices_metal_timestamp 
            ON metals_prices(metal_name, timestamp)
        """)
        
        # Create alerts table
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id VARCHAR PRIMARY KEY,
                metal_name VARCHAR NOT NULL,
                alert_type VARCHAR NOT NULL,
                threshold_value DOUBLE NOT NULL,
                current_value DOUBLE NOT NULL,
                triggered_at TIMESTAMP NOT NULL,
                message TEXT NOT NULL,
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create daily_summaries table for performance optimization
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS daily_summaries (
                date DATE NOT NULL,
                metal_name VARCHAR NOT NULL,
                open_price DOUBLE,
                high_price DOUBLE,
                low_price DOUBLE,
                close_price DOUBLE,
                avg_price DOUBLE,
                total_volume DOUBLE,
                price_change DOUBLE,
                price_change_pct DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, metal_name)
            )
        """)
        
        # Create users table for authentication
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                username VARCHAR UNIQUE NOT NULL,
                email VARCHAR UNIQUE NOT NULL,
                password_hash VARCHAR NOT NULL,
                salt VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                role VARCHAR DEFAULT 'user'
            )
        """)
        
        # Create user_sessions table for session management
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT true,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Create indexes for sessions
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id 
            ON user_sessions(user_id)
        """)
        
        self.connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_expires 
            ON user_sessions(expires_at)
        """)
        
        self.logger.info("Database schema initialized successfully")
    
    def store_metal_price(self, price: MetalPrice) -> bool:
        """Store a single MetalPrice in the database"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            self.connection.execute("""
                INSERT INTO metals_prices (
                    ticker, metal_name, price, currency, timestamp,
                    bid, ask, volume, open_price, high, low, previous_close
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                price.ticker, price.metal_name, price.price, price.currency,
                price.timestamp, price.bid, price.ask, price.volume,
                price.open_price, price.high, price.low, price.previous_close
            ])
            return True
        except Exception as e:
            self.logger.error(f"Failed to store metal price: {e}")
            return False
    
    def store_metal_prices(self, prices: List[MetalPrice]) -> int:
        """Store multiple MetalPrice objects in the database"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        stored_count = 0
        for price in prices:
            if self.store_metal_price(price):
                stored_count += 1
        
        self.logger.info(f"Stored {stored_count}/{len(prices)} metal prices")
        return stored_count
    
    def get_latest_prices(self, metals: Optional[List[str]] = None) -> List[MetalPrice]:
        """Get the latest prices for specified metals"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        if metals:
            metal_filter = f"WHERE metal_name IN ({','.join(['?' for _ in metals])})"
            params = metals
        else:
            metal_filter = ""
            params = []
        
        # DuckDB syntax for getting latest record per group
        query = f"""
            WITH ranked_prices AS (
                SELECT *,
                       ROW_NUMBER() OVER (PARTITION BY metal_name ORDER BY timestamp DESC) as rn
                FROM metals_prices
                {metal_filter}
            )
            SELECT * FROM ranked_prices WHERE rn = 1
        """
        
        try:
            result = self.connection.execute(query, params).fetchall()
            columns = [desc[0] for desc in self.connection.description]
            
            prices = []
            for row in result:
                row_dict = dict(zip(columns, row))
                price = MetalPrice(
                    ticker=row_dict['ticker'],
                    metal_name=row_dict['metal_name'],
                    price=row_dict['price'],
                    currency=row_dict['currency'],
                    timestamp=row_dict['timestamp'],
                    bid=row_dict['bid'],
                    ask=row_dict['ask'],
                    volume=row_dict['volume'],
                    open_price=row_dict['open_price'],
                    high=row_dict['high'],
                    low=row_dict['low'],
                    previous_close=row_dict['previous_close']
                )
                prices.append(price)
            
            return prices
        except Exception as e:
            self.logger.error(f"Failed to get latest prices: {e}")
            return []
    
    def get_historical_prices(self, metal: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get historical prices for a metal within date range"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            query = """
                SELECT * FROM metals_prices
                WHERE metal_name = ?
                AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp ASC
            """
            
            result = self.connection.execute(query, [metal, start_date, end_date])
            df = result.df()
            
            self.logger.info(f"Retrieved {len(df)} historical records for {metal}")
            return df
        except Exception as e:
            self.logger.error(f"Failed to get historical prices: {e}")
            return pd.DataFrame()
    
    def get_price_statistics(self, metal: str, days: int = 30) -> Dict[str, Any]:
        """Get price statistics for a metal over specified days"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        start_date = datetime.now() - timedelta(days=days)
        
        try:
            query = """
                SELECT 
                    COUNT(*) as data_points,
                    AVG(price) as avg_price,
                    MIN(price) as min_price,
                    MAX(price) as max_price,
                    STDDEV(price) as price_stddev,
                    AVG(volume) as avg_volume,
                    SUM(volume) as total_volume
                FROM metals_prices
                WHERE metal_name = ?
                AND timestamp >= ?
            """
            
            result = self.connection.execute(query, [metal, start_date]).fetchone()
            columns = [desc[0] for desc in self.connection.description]
            
            stats = dict(zip(columns, result)) if result else {}
            return stats
        except Exception as e:
            self.logger.error(f"Failed to get price statistics: {e}")
            return {}
    
    def store_alert(self, alert: Alert) -> bool:
        """Store an alert in the database"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            self.connection.execute("""
                INSERT INTO alerts (
                    id, metal_name, alert_type, threshold_value,
                    current_value, triggered_at, message, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    metal_name = EXCLUDED.metal_name,
                    alert_type = EXCLUDED.alert_type,
                    threshold_value = EXCLUDED.threshold_value,
                    current_value = EXCLUDED.current_value,
                    triggered_at = EXCLUDED.triggered_at,
                    message = EXCLUDED.message,
                    is_active = EXCLUDED.is_active
            """, [
                alert.id, alert.metal_name, alert.alert_type,
                alert.threshold_value, alert.current_value,
                alert.triggered_at, alert.message, alert.is_active
            ])
            return True
        except Exception as e:
            self.logger.error(f"Failed to store alert: {e}")
            return False
    
    def get_active_alerts(self, metal: Optional[str] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by metal"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        if metal:
            query = "SELECT * FROM alerts WHERE is_active = true AND metal_name = ? ORDER BY triggered_at DESC"
            params = [metal]
        else:
            query = "SELECT * FROM alerts WHERE is_active = true ORDER BY triggered_at DESC"
            params = []
        
        try:
            result = self.connection.execute(query, params).fetchall()
            columns = [desc[0] for desc in self.connection.description]
            
            alerts = []
            for row in result:
                row_dict = dict(zip(columns, row))
                alert = Alert(
                    id=row_dict['id'],
                    metal_name=row_dict['metal_name'],
                    alert_type=row_dict['alert_type'],
                    threshold_value=row_dict['threshold_value'],
                    current_value=row_dict['current_value'],
                    triggered_at=row_dict['triggered_at'],
                    message=row_dict['message'],
                    is_active=row_dict['is_active']
                )
                alerts.append(alert)
            
            return alerts
        except Exception as e:
            self.logger.error(f"Failed to get active alerts: {e}")
            return []
    
    def generate_daily_summary(self, date: datetime, metal: str) -> bool:
        """Generate daily summary for a specific metal and date"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            # Get daily statistics using window functions
            query = """
                WITH daily_data AS (
                    SELECT *,
                           ROW_NUMBER() OVER (ORDER BY timestamp ASC) as first_row,
                           ROW_NUMBER() OVER (ORDER BY timestamp DESC) as last_row
                    FROM metals_prices
                    WHERE metal_name = ?
                    AND timestamp::DATE = ?
                ),
                aggregated AS (
                    SELECT 
                        metal_name,
                        MIN(timestamp) as first_timestamp,
                        MAX(timestamp) as last_timestamp,
                        MAX(price) as high_price,
                        MIN(price) as low_price,
                        AVG(price) as avg_price,
                        SUM(volume) as total_volume,
                        COUNT(*) as record_count
                    FROM daily_data
                    GROUP BY metal_name
                ),
                open_close AS (
                    SELECT 
                        MAX(CASE WHEN first_row = 1 THEN price END) as open_price,
                        MAX(CASE WHEN last_row = 1 THEN price END) as close_price
                    FROM daily_data
                )
                SELECT 
                    a.metal_name, a.first_timestamp, a.last_timestamp,
                    oc.open_price, a.high_price, a.low_price, oc.close_price,
                    a.avg_price, a.total_volume
                FROM aggregated a
                CROSS JOIN open_close oc
            """
            
            result = self.connection.execute(query, [metal, date.date()]).fetchone()
            
            if result:
                open_price, high_price, low_price, close_price, avg_price, total_volume = result[3:9]
                price_change = close_price - open_price
                price_change_pct = (price_change / open_price * 100) if open_price != 0 else 0
                
                # Insert or update daily summary using ON CONFLICT
                self.connection.execute("""
                    INSERT INTO daily_summaries (
                        date, metal_name, open_price, high_price, low_price,
                        close_price, avg_price, total_volume, price_change, price_change_pct
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (date, metal_name) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        avg_price = EXCLUDED.avg_price,
                        total_volume = EXCLUDED.total_volume,
                        price_change = EXCLUDED.price_change,
                        price_change_pct = EXCLUDED.price_change_pct
                """, [
                    date.date(), metal, open_price, high_price, low_price,
                    close_price, avg_price, total_volume, price_change, price_change_pct
                ])
                
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to generate daily summary: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check database health and return statistics"""
        if not self.connection:
            return {"connected": False}
        
        try:
            # Get table statistics
            tables_info = {}
            
            for table in ['metals_prices', 'alerts', 'daily_summaries']:
                count_result = self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                tables_info[table] = count_result[0] if count_result else 0
            
            # Get latest data timestamp
            latest_result = self.connection.execute(
                "SELECT MAX(timestamp) FROM metals_prices"
            ).fetchone()
            latest_data = latest_result[0] if latest_result[0] else None
            
            return {
                "connected": True,
                "database_path": self.db_path,
                "tables": tables_info,
                "latest_data_timestamp": latest_data,
                "health_check_time": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return {"connected": False, "error": str(e)}
    
    # User authentication methods
    def create_user(self, user: User) -> bool:
        """Create a new user in the database"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            self.connection.execute("""
                INSERT INTO users (
                    id, username, email, password_hash, salt,
                    created_at, last_login, is_active, role
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                user.id, user.username, user.email, user.password_hash,
                user.salt, user.created_at, user.last_login, 
                user.is_active, user.role
            ])
            self.logger.info(f"Created user: {user.username}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create user: {e}")
            return False
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            result = self.connection.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = true", 
                [username]
            ).fetchone()
            
            if result:
                columns = [desc[0] for desc in self.connection.description]
                row_dict = dict(zip(columns, result))
                
                return User(
                    id=row_dict['id'],
                    username=row_dict['username'],
                    email=row_dict['email'],
                    password_hash=row_dict['password_hash'],
                    salt=row_dict['salt'],
                    created_at=row_dict['created_at'],
                    last_login=row_dict['last_login'],
                    is_active=row_dict['is_active'],
                    role=row_dict['role']
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get user by username: {e}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            result = self.connection.execute(
                "SELECT * FROM users WHERE email = ? AND is_active = true", 
                [email]
            ).fetchone()
            
            if result:
                columns = [desc[0] for desc in self.connection.description]
                row_dict = dict(zip(columns, result))
                
                return User(
                    id=row_dict['id'],
                    username=row_dict['username'],
                    email=row_dict['email'],
                    password_hash=row_dict['password_hash'],
                    salt=row_dict['salt'],
                    created_at=row_dict['created_at'],
                    last_login=row_dict['last_login'],
                    is_active=row_dict['is_active'],
                    role=row_dict['role']
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get user by email: {e}")
            return None
    
    def update_user_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            self.connection.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                [datetime.now(), user_id]
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to update user last login: {e}")
            return False
    
    # Session management methods
    def create_session(self, session: UserSession) -> bool:
        """Create a new user session"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            self.connection.execute("""
                INSERT INTO user_sessions (
                    session_id, user_id, created_at, expires_at, is_active
                ) VALUES (?, ?, ?, ?, ?)
            """, [
                session.session_id, session.user_id, session.created_at,
                session.expires_at, session.is_active
            ])
            return True
        except Exception as e:
            self.logger.error(f"Failed to create session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[UserSession]:
        """Get session by session ID"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            result = self.connection.execute(
                "SELECT * FROM user_sessions WHERE session_id = ? AND is_active = true",
                [session_id]
            ).fetchone()
            
            if result:
                columns = [desc[0] for desc in self.connection.description]
                row_dict = dict(zip(columns, result))
                
                return UserSession(
                    session_id=row_dict['session_id'],
                    user_id=row_dict['user_id'],
                    created_at=row_dict['created_at'],
                    expires_at=row_dict['expires_at'],
                    is_active=row_dict['is_active']
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get session: {e}")
            return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a user session"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            self.connection.execute(
                "UPDATE user_sessions SET is_active = false WHERE session_id = ?",
                [session_id]
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to invalidate session: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            # First count how many will be affected
            count_result = self.connection.execute(
                "SELECT COUNT(*) FROM user_sessions WHERE expires_at < ? AND is_active = true",
                [datetime.now()]
            ).fetchone()
            cleaned_count = count_result[0] if count_result else 0
            
            # Then update them
            self.connection.execute(
                "UPDATE user_sessions SET is_active = false WHERE expires_at < ? AND is_active = true",
                [datetime.now()]
            )
            
            self.logger.info(f"Cleaned up {cleaned_count} expired sessions")
            return cleaned_count
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        if not self.connection:
            raise ConnectionError("Not connected to database")
        
        try:
            result = self.connection.execute(
                "SELECT * FROM users WHERE id = ? AND is_active = true", 
                [user_id]
            ).fetchone()
            
            if result:
                columns = [desc[0] for desc in self.connection.description]
                row_dict = dict(zip(columns, result))
                
                return User(
                    id=row_dict['id'],
                    username=row_dict['username'],
                    email=row_dict['email'],
                    password_hash=row_dict['password_hash'],
                    salt=row_dict['salt'],
                    created_at=row_dict['created_at'],
                    last_login=row_dict['last_login'],
                    is_active=row_dict['is_active'],
                    role=row_dict['role']
                )
            return None
        except Exception as e:
            self.logger.error(f"Failed to get user by ID: {e}")
            return None