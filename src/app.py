import dash
from dash import html, dcc, Input, Output, State, callback
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from data.bloomberg_client import BloombergClient
from data.database import DatabaseManager
from data.mastodon_client import MastodonClient

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

app = dash.Dash(__name__, suppress_callback_exceptions=True)

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
    
    # Chart and Mastodon section side by side
    html.Div([
        # Chart section (left half)
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
            'margin': '15px 5px 15px 0',
            'borderRadius': '8px',
            'width': '48%',
            'display': 'inline-block',
            'verticalAlign': 'top'
        }),
        
        # Mastodon section (right half)
        html.Div([
            html.H4("Mastodon Feed", style={'color': THEME['text'], 'marginBottom': '15px'}),
            
            # Connection status
            html.Div(id='mastodon-status', style={'marginBottom': '15px'}),
            
            # Connect button
            html.Button(
                "Connect to Mastodon", 
                id='mastodon-connect-btn',
                style={
                    'backgroundColor': THEME['accent'],
                    'color': 'white',
                    'border': 'none',
                    'padding': '10px 20px',
                    'borderRadius': '5px',
                    'cursor': 'pointer',
                    'marginBottom': '15px'
                }
            ),
            
            # Following selection (hidden until connected)
            html.Div([
                html.H5("Select Users to Follow:", style={'color': THEME['text'], 'marginBottom': '10px'}),
                dcc.Dropdown(
                    id='mastodon-following-selector',
                    multi=True,
                    placeholder="Select users to monitor...",
                    style={'marginBottom': '15px', 'backgroundColor': THEME['background']}
                )
            ], id='mastodon-following-section', style={'display': 'none'}),
            
            # Posts feed
            html.Div(id='mastodon-posts', style={
                'height': '400px',
                'overflowY': 'auto',
                'border': f'1px solid {THEME["accent"]}',
                'borderRadius': '5px',
                'padding': '10px'
            }),
            
            # Hidden elements for callbacks (initially not displayed)
            html.Div([
                dcc.Input(id='mastodon-auth-code', style={'display': 'none'}),
                html.Button(id='mastodon-submit-code', style={'display': 'none'})
            ], style={'display': 'none'})
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

# Mastodon callbacks
mastodon_client = MastodonClient()

@callback(
    [Output('mastodon-status', 'children'),
     Output('mastodon-following-section', 'style'),
     Output('mastodon-connect-btn', 'children'),
     Output('mastodon-following-selector', 'options')],
    [Input('mastodon-connect-btn', 'n_clicks')]
)
def handle_mastodon_connection(n_clicks):
    """Handle Mastodon connection button click"""
    if n_clicks is None:
        # Initial load - check for saved credentials
        if mastodon_client.connect_with_saved_credentials():
            user_info = mastodon_client.get_user_info()
            status = html.Div([
                html.Span(f"✅ Connected as @{user_info['username']}", 
                         style={'color': THEME['success']})
            ])
            # Also populate following list for saved credentials
            following_list = mastodon_client.get_following_list()
            options = [
                {
                    'label': f"@{account['username']} ({account['display_name']})",
                    'value': account['id']
                }
                for account in following_list
            ]
            return status, {'display': 'block'}, "Disconnect", options
        else:
            status = html.Div([
                html.Span("❌ Not connected", style={'color': THEME['danger']})
            ])
            return status, {'display': 'none'}, "Connect to Mastodon", []
    
    # Button clicked
    if mastodon_client.is_connected:
        # Disconnect
        mastodon_client.disconnect()
        status = html.Div([
            html.Span("❌ Disconnected", style={'color': THEME['danger']})
        ])
        return status, {'display': 'none'}, "Connect to Mastodon", []
    else:
        # Show connection instructions
        auth_url = mastodon_client.get_auth_url('https://mastodon.social')
        status = html.Div([
            html.P("To connect to Mastodon:", style={'color': THEME['text'], 'margin': '5px 0'}),
            html.P([
                "1. Visit: ",
                html.A("Authorization Link", href=auth_url, target="_blank", 
                      style={'color': THEME['accent']})
            ], style={'color': THEME['text'], 'margin': '5px 0'}),
            html.P("2. Copy the authorization code", style={'color': THEME['text'], 'margin': '5px 0'}),
            html.P("3. Enter it below:", style={'color': THEME['text'], 'margin': '5px 0'}),
            dcc.Input(
                id='mastodon-auth-code',
                type='text',
                placeholder='Enter authorization code...',
                style={'width': '100%', 'padding': '5px', 'marginBottom': '10px'}
            ),
            html.Button(
                "Submit Code",
                id='mastodon-submit-code',
                style={
                    'backgroundColor': THEME['accent'],
                    'color': 'white',
                    'border': 'none',
                    'padding': '8px 16px',
                    'borderRadius': '5px',
                    'cursor': 'pointer'
                }
            )
        ])
        return status, {'display': 'none'}, "Connect to Mastodon", []

@callback(
    Output('mastodon-following-selector', 'value'),
    [Input('mastodon-submit-code', 'n_clicks')],
    [State('mastodon-auth-code', 'value')]
)
def handle_auth_code(n_clicks, auth_code):
    """Handle authorization code submission"""
    if n_clicks is None or not auth_code:
        return []
    
    try:
        if mastodon_client.authenticate_with_code(auth_code):
            return []  # Clear selection after successful auth
        else:
            return []
    except Exception as e:
        logger.error(f"Error handling auth code: {e}")
        return []

@callback(
    Output('mastodon-posts', 'children'),
    [Input('interval-component', 'n_intervals'),
     Input('mastodon-following-selector', 'value')]
)
def update_mastodon_posts(n_intervals, selected_accounts):
    """Update Mastodon posts feed"""
    if not mastodon_client.is_connected or not selected_accounts:
        return html.Div([
            html.P("Connect to Mastodon and select accounts to see posts", 
                  style={'color': THEME['text'], 'textAlign': 'center', 'padding': '20px'})
        ])
    
    try:
        posts = mastodon_client.get_recent_posts(selected_accounts, limit=10)
        
        if not posts:
            return html.Div([
                html.P("No recent posts found", 
                      style={'color': THEME['text'], 'textAlign': 'center', 'padding': '20px'})
            ])
        
        post_elements = []
        for post in posts:
            # Strip HTML from content
            import re
            clean_content = re.sub(r'<[^>]+>', '', post['content'])
            if len(clean_content) > 200:
                clean_content = clean_content[:200] + "..."
            
            post_element = html.Div([
                html.Div([
                    html.Strong(f"@{post['account_username']}", 
                              style={'color': THEME['accent']}),
                    html.Span(f" • {post['created_at'].strftime('%H:%M')}", 
                             style={'color': THEME['text'], 'fontSize': '12px', 'marginLeft': '10px'})
                ], style={'marginBottom': '5px'}),
                html.P(clean_content, style={'color': THEME['text'], 'margin': '0 0 10px 0'}),
                html.Div([
                    html.Span(f"❤️ {post['favourites_count']}", 
                             style={'color': THEME['text'], 'fontSize': '12px', 'marginRight': '15px'}),
                    html.Span(f"🔄 {post['reblogs_count']}", 
                             style={'color': THEME['text'], 'fontSize': '12px', 'marginRight': '15px'}),
                    html.A("View", href=post['url'], target="_blank", 
                          style={'color': THEME['accent'], 'fontSize': '12px'})
                ])
            ], style={
                'backgroundColor': '#333',
                'padding': '10px',
                'margin': '5px 0',
                'borderRadius': '5px',
                'borderLeft': f'3px solid {THEME["accent"]}'
            })
            post_elements.append(post_element)
        
        return post_elements
        
    except Exception as e:
        logger.error(f"Error updating Mastodon posts: {e}")
        return html.Div([
            html.P(f"Error loading posts: {str(e)[:50]}...", 
                  style={'color': THEME['danger'], 'textAlign': 'center', 'padding': '20px'})
        ])

if __name__ == '__main__':
    app.run_server(debug=True)