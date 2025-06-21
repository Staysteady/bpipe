import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from data.bloomberg_client import BloombergClient
from data.database import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dark theme configuration
THEME = {
    'background': '#1a1a1a',
    'card_background': '#2d2d2d',
    'text': '#ffffff',
    'accent': '#00cc96',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'info': '#17a2b8'
}

app = dash.Dash(__name__)

def create_price_card(metal_name, price, change, change_pct):
    """Create a price card component for a metal"""
    color = THEME['success'] if change >= 0 else THEME['danger']
    arrow = '↑' if change >= 0 else '↓'
    
    return html.Div([
        html.H4(metal_name.upper(), style={'color': THEME['text'], 'margin': '0'}),
        html.H2(f"${price:.2f}", style={'color': THEME['text'], 'margin': '5px 0'}),
        html.Div([
            html.Span(f"{arrow} ${abs(change):.2f}", 
                     style={'color': color, 'fontSize': '14px', 'marginRight': '10px'}),
            html.Span(f"({change_pct:+.2f}%)", 
                     style={'color': color, 'fontSize': '14px'})
        ])
    ], style={
        'backgroundColor': THEME['card_background'],
        'padding': '15px',
        'margin': '5px',
        'borderRadius': '8px',
        'textAlign': 'center',
        'minWidth': '150px'
    })

def create_alerts_card(alert_count):
    """Create alerts summary card"""
    return html.Div([
        html.H4("Active Alerts", style={'color': THEME['text'], 'margin': '0'}),
        html.H2(str(alert_count), style={'color': THEME['warning'], 'margin': '5px 0'}),
        html.P("Price thresholds", style={'color': THEME['text'], 'fontSize': '12px', 'margin': '0'})
    ], style={
        'backgroundColor': THEME['card_background'],
        'padding': '15px',
        'margin': '5px',
        'borderRadius': '8px',
        'textAlign': 'center',
        'minWidth': '150px'
    })

app.layout = html.Div([
    # Header
    html.Div([
        html.H1("Bloomberg Terminal Integration Dashboard", 
                style={'color': THEME['text'], 'textAlign': 'center', 'margin': '0'}),
        html.P("Real-time LME Metals Trading Dashboard", 
               style={'color': THEME['accent'], 'textAlign': 'center', 'margin': '10px 0'})
    ], style={'marginBottom': '20px'}),
    
    # Auto-refresh interval component
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # Update every 30 seconds
        n_intervals=0
    ),
    
    # Status indicators
    html.Div([
        html.Div(id='connection-status', style={'marginBottom': '10px'})
    ]),
    
    # Price cards row
    html.Div([
        html.H3("Current LME Prices", style={'color': THEME['text'], 'marginBottom': '15px'}),
        html.Div(id='price-cards-container', style={
            'display': 'flex',
            'flexWrap': 'wrap',
            'justifyContent': 'center',
            'gap': '10px'
        })
    ], style={
        'backgroundColor': THEME['card_background'],
        'padding': '20px',
        'margin': '10px 0',
        'borderRadius': '8px'
    }),
    
    # Simple chart for now
    html.Div([
        html.H4("Real-time Price Chart", style={'color': THEME['text']}),
        dcc.Dropdown(
            id='metal-selector',
            options=[
                {'label': 'Copper', 'value': 'copper'},
                {'label': 'Aluminum', 'value': 'aluminum'},
                {'label': 'Zinc', 'value': 'zinc'},
                {'label': 'Nickel', 'value': 'nickel'},
                {'label': 'Lead', 'value': 'lead'},
                {'label': 'Tin', 'value': 'tin'}
            ],
            value='copper',
            style={'marginBottom': '10px', 'backgroundColor': THEME['background']}
        ),
        dcc.Graph(id='simple-price-chart')
    ], style={
        'backgroundColor': THEME['card_background'],
        'padding': '20px',
        'margin': '15px 0',
        'borderRadius': '8px'
    })
    
], style={
    'backgroundColor': THEME['background'], 
    'minHeight': '100vh', 
    'padding': '20px',
    'fontFamily': 'Arial, sans-serif'
})

# Simplified callback for price cards
@callback(
    [Output('price-cards-container', 'children'),
     Output('connection-status', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_price_cards(n):
    """Update price cards with latest LME prices"""
    try:
        # Try to get fresh data
        db = DatabaseManager()
        bloomberg_client = BloombergClient(use_mock=True)
        
        if not db.connect():
            return [], html.Div([
                html.Span("❌ Database connection failed", style={'color': THEME['danger']})
            ])
        
        if not bloomberg_client.connect():
            db.disconnect()
            return [], html.Div([
                html.Span("❌ Bloomberg connection failed", style={'color': THEME['danger']})
            ])
        
        # Get some data
        bloomberg_prices = bloomberg_client.get_lme_prices()
        if bloomberg_prices:
            db.store_metal_prices(bloomberg_prices)
        
        latest_prices = db.get_latest_prices()
        
        price_cards = []
        for price in latest_prices[:6]:  # Limit to 6 metals
            change = price.price * 0.002  # Mock change
            change_pct = 0.2
            
            card = create_price_card(price.metal_name, price.price, change, change_pct)
            price_cards.append(card)
        
        # Add alerts card
        active_alerts = db.get_active_alerts()
        alerts_card = create_alerts_card(len(active_alerts))
        price_cards.append(alerts_card)
        
        # Cleanup
        bloomberg_client.disconnect()
        db.disconnect()
        
        status = html.Div([
            html.Span("✅ All Systems Connected", style={'color': THEME['success']})
        ])
        
        return price_cards, status
        
    except Exception as e:
        logger.error(f"Error updating price cards: {e}")
        error_status = html.Div([
            html.Span(f"❌ Error: {str(e)[:50]}...", style={'color': THEME['danger']})
        ])
        return [], error_status

# Simplified chart callback
@callback(
    Output('simple-price-chart', 'figure'),
    [Input('metal-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_simple_chart(selected_metal, n):
    """Update simple price chart"""
    try:
        # Create a simple mock chart for now
        timestamps = [datetime.now() - timedelta(hours=i) for i in range(24, 0, -1)]
        base_price = 8500.0
        prices = [base_price + (24-i)*2 + (i%3)*5 for i in range(24)]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps,
            y=prices,
            mode='lines+markers',
            name=f'{selected_metal.upper()} Price',
            line=dict(color=THEME['accent'], width=2),
            marker=dict(size=4)
        ))
        
        fig.update_layout(
            plot_bgcolor=THEME['background'],
            paper_bgcolor=THEME['card_background'],
            font_color=THEME['text'],
            title=f'{selected_metal.upper()} - Last 24 Hours (Mock Data)',
            xaxis_title='Time',
            yaxis_title='Price (USD)',
            showlegend=False,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        
        fig.update_xaxes(gridcolor='#404040', showgrid=True)
        fig.update_yaxes(gridcolor='#404040', showgrid=True)
        
        return fig
        
    except Exception as e:
        logger.error(f"Error updating chart: {e}")
        # Return error figure
        fig = go.Figure()
        fig.update_layout(
            plot_bgcolor=THEME['background'],
            paper_bgcolor=THEME['card_background'],
            font_color=THEME['text'],
            title=f"Chart Error: {str(e)[:30]}..."
        )
        return fig

if __name__ == '__main__':
    app.run_server(debug=True)