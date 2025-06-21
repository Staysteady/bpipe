#!/usr/bin/env python3
from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>Flask Test Server</h1><p>If you see this, the server is working!</p>'

if __name__ == '__main__':
    print("Starting Flask test server...")
    app.run(debug=True, host='127.0.0.1', port=8055)