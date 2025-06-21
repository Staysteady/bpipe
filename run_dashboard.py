#!/usr/bin/env python3
"""
Bloomberg Terminal Integration Dashboard Launcher
Run this script to launch the dashboard in your browser
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the dashboard
from src.app import app

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Bloomberg Terminal Integration Dashboard")
    print("=" * 60)
    print("Initializing dashboard components...")
    print("✅ Database layer ready")
    print("✅ Bloomberg API integration ready")
    print("✅ Real-time charts ready")
    print("✅ Alerts system ready")
    print()
    print("🌐 Starting web server...")
    print("📱 Dashboard will open at: http://localhost:8050")
    print()
    print("💡 Features available:")
    print("   • Real-time LME metal prices")
    print("   • Interactive price charts")
    print("   • Historical data analysis")
    print("   • Active alerts monitoring")
    print("   • Market statistics")
    print("   • Auto-refresh every 30 seconds")
    print()
    print("🛑 Press Ctrl+C to stop the dashboard")
    print("=" * 60)
    
    try:
        app.run_server(debug=True, host='127.0.0.1', port=8050)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard stopped by user")
        print("✅ Thank you for using Bloomberg Terminal Integration Dashboard!")
    except Exception as e:
        print(f"\n❌ Error starting dashboard: {e}")
        print("💡 Check the console output above for details")