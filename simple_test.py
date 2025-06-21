#!/usr/bin/env python3
import dash
from dash import html, dcc
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Simple test app without callbacks
app = dash.Dash(__name__)

THEME = {
    'background': '#1a1a1a',
    'card_background': '#2d2d2d',
    'text': '#ffffff',
    'accent': '#00cc96',
}

app.layout = html.Div([
    html.H1("Test Dashboard", style={'color': THEME['text']}),
    
    # Test the new layout structure
    html.Div([
        # Left side - Chart
        html.Div([
            html.H4("Chart Section", style={'color': THEME['text']}),
            html.P("This should be 48% width", style={'color': THEME['text']})
        ], style={
            'backgroundColor': THEME['card_background'],
            'padding': '20px',
            'margin': '15px 5px 15px 0',
            'borderRadius': '8px',
            'width': '48%',
            'display': 'inline-block',
            'verticalAlign': 'top'
        }),
        
        # Right side - Mastodon
        html.Div([
            html.H4("Mastodon Section", style={'color': THEME['text']}),
            html.P("This should be 48% width", style={'color': THEME['text']})
        ], style={
            'backgroundColor': THEME['card_background'],
            'padding': '20px',
            'margin': '15px 0 15px 5px',
            'borderRadius': '8px',
            'width': '48%',
            'display': 'inline-block',
            'verticalAlign': 'top'
        })
    ], style={
        'width': '100%',
        'display': 'flex',
        'gap': '10px'
    })
], style={
    'backgroundColor': THEME['background'],
    'minHeight': '100vh',
    'padding': '20px'
})

if __name__ == '__main__':
    print("Starting simple test server...")
    app.run_server(debug=True, host='127.0.0.1', port=8054)