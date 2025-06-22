#!/usr/bin/env python3
"""
Test script for the authentication system
"""

import sys
import os
sys.path.insert(0, 'src')

from src.data.database import DatabaseManager
from src.data.models import User, UserSession
from src.auth import AuthManager

def test_database_schema():
    """Test database schema creation"""
    print("Testing database schema...")
    
    db = DatabaseManager()
    if not db.connect():
        print("❌ Database connection failed")
        return False
    
    try:
        # Test database health
        health = db.health_check()
        print(f"✅ Database health check: {health}")
        
        # Check if tables exist
        tables = ['users', 'user_sessions', 'metals_prices', 'alerts']
        for table in tables:
            result = db.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            print(f"✅ Table '{table}' exists with {result[0]} records")
        
        return True
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        return False
    finally:
        db.disconnect()

def test_user_creation():
    """Test user creation and authentication"""
    print("\nTesting user creation and authentication...")
    
    auth = AuthManager()
    
    # Test user creation
    test_username = "testuser"
    test_email = "test@example.com"
    test_password = "testpassword123"
    
    success, error = auth.create_user_account(test_username, test_email, test_password)
    if success:
        print(f"✅ Test user '{test_username}' created successfully")
    else:
        print(f"❌ User creation failed: {error}")
        return False
    
    # Test authentication
    success, user, error = auth.authenticate_user(test_username, test_password)
    if success:
        print(f"✅ Authentication successful for user: {user.username}")
        print(f"   User ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   Session ID: {auth.get_current_session_id()}")
    else:
        print(f"❌ Authentication failed: {error}")
        return False
    
    # Test wrong password
    success, user, error = auth.authenticate_user(test_username, "wrongpassword")
    if not success:
        print("✅ Wrong password correctly rejected")
    else:
        print("❌ Wrong password was accepted (security issue!)")
        return False
    
    # Test logout
    if auth.logout_user():
        print("✅ Logout successful")
    else:
        print("❌ Logout failed")
        return False
    
    return True

def test_session_management():
    """Test session management"""
    print("\nTesting session management...")
    
    auth = AuthManager()
    
    # Create and authenticate a user
    success, user, error = auth.authenticate_user("testuser", "testpassword123")
    if not success:
        print(f"❌ Authentication failed: {error}")
        return False
    
    session_id = auth.get_current_session_id()
    print(f"✅ Session created: {session_id}")
    
    # Test session validation
    valid, validated_user = auth.validate_session(session_id)
    if valid:
        print(f"✅ Session validation successful for user: {validated_user.username}")
    else:
        print("❌ Session validation failed")
        return False
    
    # Test invalid session
    valid, _ = auth.validate_session("invalid_session_id")
    if not valid:
        print("✅ Invalid session correctly rejected")
    else:
        print("❌ Invalid session was accepted (security issue!)")
        return False
    
    return True

def cleanup_test_data():
    """Clean up test data"""
    print("\nCleaning up test data...")
    
    db = DatabaseManager()
    if not db.connect():
        return False
    
    try:
        # Remove test user
        db.connection.execute("DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE username = 'testuser')")
        db.connection.execute("DELETE FROM users WHERE username = 'testuser'")
        print("✅ Test data cleaned up")
        return True
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        return False
    finally:
        db.disconnect()

def main():
    """Main test function"""
    print("Bloomberg Terminal Dashboard - Authentication System Test")
    print("=" * 60)
    
    tests = [
        test_database_schema,
        test_user_creation,
        test_session_management,
        cleanup_test_data
    ]
    
    all_passed = True
    for test in tests:
        try:
            if not test():
                all_passed = False
                break
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            all_passed = False
            break
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All authentication tests passed!")
        print("\nNext steps:")
        print("1. Run 'python create_admin_user.py' to create your admin account")
        print("2. Run 'python run_dashboard.py' to start the dashboard")
        print("3. Navigate to http://localhost:8050 to access the login page")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()