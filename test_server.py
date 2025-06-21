#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

print("Starting minimal test...")
try:
    from src.app import app
    print("App imported successfully")
    print(f"App type: {type(app)}")
    print("Starting server...")
    app.run_server(debug=True, host='127.0.0.1', port=8053)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()