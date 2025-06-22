"""
Authentication module for Bloomberg Terminal Dashboard
Handles user authentication, session management, and login/logout functionality
"""

import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from functools import wraps

from data.database import DatabaseManager
from data.models import User, UserSession

logger = logging.getLogger(__name__)

class AuthManager:
    """Authentication manager for user login/logout and session handling"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.current_user = None
        self.current_session = None
        
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[User], Optional[str]]:
        """
        Authenticate user credentials
        Returns: (success, user, error_message)
        """
        try:
            if not self.db.connect():
                return False, None, "Database connection failed"
            
            # Get user by username
            user = self.db.get_user_by_username(username)
            if not user:
                return False, None, "Invalid username or password"
            
            # Verify password
            if not user.verify_password(password):
                return False, None, "Invalid username or password"
            
            # Update last login
            self.db.update_user_last_login(user.id)
            
            # Create new session
            session = UserSession.create_session(user.id)
            if not self.db.create_session(session):
                return False, None, "Failed to create session"
            
            # Clean up expired sessions
            self.db.cleanup_expired_sessions()
            
            # Set current user and session
            self.current_user = user
            self.current_session = session
            
            logger.info(f"User {username} authenticated successfully")
            return True, user, None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False, None, str(e)
        finally:
            self.db.disconnect()
    
    def create_user_account(self, username: str, email: str, password: str, role: str = 'user') -> Tuple[bool, Optional[str]]:
        """
        Create a new user account
        Returns: (success, error_message)
        """
        try:
            if not self.db.connect():
                return False, "Database connection failed"
            
            # Check if username already exists
            existing_user = self.db.get_user_by_username(username)
            if existing_user:
                return False, "Username already exists"
            
            # Check if email already exists
            existing_email = self.db.get_user_by_email(email)
            if existing_email:
                return False, "Email already registered"
            
            # Create new user
            user = User.create_user(username, email, password, role)
            if not self.db.create_user(user):
                return False, "Failed to create user account"
            
            logger.info(f"Created new user account: {username}")
            return True, None
            
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return False, str(e)
        finally:
            self.db.disconnect()
    
    def logout_user(self) -> bool:
        """Logout current user and invalidate session"""
        try:
            if not self.current_session:
                return True
            
            if not self.db.connect():
                return False
            
            # Invalidate current session
            success = self.db.invalidate_session(self.current_session.session_id)
            
            # Clear current user and session
            self.current_user = None
            self.current_session = None
            
            logger.info("User logged out successfully")
            return success
            
        except Exception as e:
            logger.error(f"Logout error: {e}")
            return False
        finally:
            self.db.disconnect()
    
    def validate_session(self, session_id: str) -> Tuple[bool, Optional[User]]:
        """
        Validate session and return user if valid
        Returns: (valid, user)
        """
        try:
            if not session_id:
                return False, None
            
            if not self.db.connect():
                return False, None
            
            # Get session
            session = self.db.get_session(session_id)
            if not session:
                return False, None
            
            # Check if session is expired
            if session.is_expired():
                self.db.invalidate_session(session_id)
                return False, None
            
            # Get user by ID from session
            user = self.db.get_user_by_id(session.user_id)
            if not user:
                self.db.invalidate_session(session_id)
                return False, None
            
            self.current_session = session
            self.current_user = user
            
            return True, user
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return False, None
        finally:
            self.db.disconnect()
    
    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated"""
        return self.current_user is not None and self.current_session is not None
    
    def get_current_user(self) -> Optional[User]:
        """Get currently authenticated user"""
        return self.current_user
    
    def get_current_session_id(self) -> Optional[str]:
        """Get current session ID"""
        return self.current_session.session_id if self.current_session else None
    
    def require_auth(self, session_id: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Check if request has valid authentication
        Returns: (authenticated, error_info)
        """
        if not session_id:
            return False, {"error": "No session provided", "redirect": "/login"}
        
        valid, user = self.validate_session(session_id)
        if not valid:
            return False, {"error": "Invalid or expired session", "redirect": "/login"}
        
        return True, None

def require_authentication(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # This would be used with Flask routes, but for Dash we'll handle it differently
        # in the callbacks
        return f(*args, **kwargs)
    return decorated_function

# Global auth manager instance
auth_manager = AuthManager()