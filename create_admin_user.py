#!/usr/bin/env python3
"""
Script to create an initial admin user for the Bloomberg Terminal Dashboard
Run this once to set up your first admin account
"""

import sys
import os
sys.path.insert(0, 'src')

from src.data.database import DatabaseManager
from src.data.models import User

def create_admin_user():
    """Create initial admin user"""
    print("Bloomberg Terminal Dashboard - Admin User Setup")
    print("=" * 50)
    
    # Get admin credentials
    username = input("Enter admin username: ").strip()
    if not username:
        print("Error: Username cannot be empty")
        return False
    
    email = input("Enter admin email: ").strip()
    if not email:
        print("Error: Email cannot be empty")
        return False
    
    password = input("Enter admin password (min 6 characters): ").strip()
    if len(password) < 6:
        print("Error: Password must be at least 6 characters long")
        return False
    
    confirm_password = input("Confirm admin password: ").strip()
    if password != confirm_password:
        print("Error: Passwords do not match")
        return False
    
    # Create database connection
    db = DatabaseManager()
    if not db.connect():
        print("Error: Could not connect to database")
        return False
    
    try:
        # Check if username already exists
        existing_user = db.get_user_by_username(username)
        if existing_user:
            print(f"Error: Username '{username}' already exists")
            return False
        
        # Check if email already exists
        existing_email = db.get_user_by_email(email)
        if existing_email:
            print(f"Error: Email '{email}' is already registered")
            return False
        
        # Create admin user
        admin_user = User.create_user(username, email, password, role='admin')
        
        if db.create_user(admin_user):
            print(f"✅ Admin user '{username}' created successfully!")
            print(f"Email: {email}")
            print(f"Role: admin")
            print("\nYou can now run the dashboard and log in with these credentials.")
            return True
        else:
            print("Error: Failed to create admin user")
            return False
            
    except Exception as e:
        print(f"Error creating admin user: {e}")
        return False
    finally:
        db.disconnect()

def main():
    """Main function"""
    success = create_admin_user()
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()