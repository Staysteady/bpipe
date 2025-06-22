import dash
from dash import html, dcc, Input, Output, State, callback, clientside_callback
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
from auth import auth_manager

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
app.title = "Bloomberg Terminal Dashboard"

# Add dcc.Store for session management
session_store = dcc.Store(id='session-store', storage_type='session')
user_store = dcc.Store(id='user-store', storage_type='session')

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

def create_login_layout():
    """Create login page layout"""
    return html.Div([
        # Session stores
        session_store,
        user_store,
        
        html.Div([
            html.Div([
                html.H1("Bloomberg Terminal Dashboard", 
                        style={'color': THEME['text'], 'textAlign': 'center', 'marginBottom': '10px'}),
                html.P("Please sign in to access the dashboard", 
                       style={'color': THEME['accent'], 'textAlign': 'center', 'marginBottom': '30px'}),
                
                # Login Form
                html.Div([
                    html.H3("Sign In", style={'color': THEME['text'], 'marginBottom': '20px'}),
                    
                    # Username field
                    html.Div([
                        html.Label("Username:", style={'color': THEME['text'], 'marginBottom': '5px', 'display': 'block'}),
                        dcc.Input(
                            id='login-username',
                            type='text',
                            placeholder='Enter your username',
                            style={
                                'width': '100%',
                                'padding': '10px',
                                'marginBottom': '15px',
                                'borderRadius': '5px',
                                'border': '1px solid #555',
                                'backgroundColor': THEME['background'],
                                'color': THEME['text']
                            }
                        )
                    ]),
                    
                    # Password field
                    html.Div([
                        html.Label("Password:", style={'color': THEME['text'], 'marginBottom': '5px', 'display': 'block'}),
                        dcc.Input(
                            id='login-password',
                            type='password',
                            placeholder='Enter your password',
                            style={
                                'width': '100%',
                                'padding': '10px',
                                'marginBottom': '20px',
                                'borderRadius': '5px',
                                'border': '1px solid #555',
                                'backgroundColor': THEME['background'],
                                'color': THEME['text']
                            }
                        )
                    ]),
                    
                    # Login button
                    html.Button(
                        "Sign In",
                        id='login-button',
                        n_clicks=0,
                        style={
                            'width': '100%',
                            'padding': '12px',
                            'backgroundColor': THEME['accent'],
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer',
                            'fontSize': '16px',
                            'marginBottom': '15px'
                        }
                    ),
                    
                    # Error message
                    html.Div(id='login-error', style={'color': THEME['danger'], 'textAlign': 'center', 'marginBottom': '15px'}),
                    
                    # Register link
                    html.Div([
                        html.P("Don't have an account? ", style={'color': THEME['text'], 'display': 'inline'}),
                        html.A("Create Account", 
                               id='show-register-link',
                               style={'color': THEME['accent'], 'cursor': 'pointer', 'textDecoration': 'underline'})
                    ], style={'textAlign': 'center'})
                    
                ], style={
                    'backgroundColor': THEME['card_background'],
                    'padding': '30px',
                    'borderRadius': '10px',
                    'width': '100%',
                    'maxWidth': '400px'
                })
                
            ], style={
                'display': 'flex',
                'flexDirection': 'column',
                'alignItems': 'center',
                'minHeight': '100vh',
                'justifyContent': 'center'
            })
        ], style={
            'backgroundColor': THEME['background'],
            'minHeight': '100vh',
            'padding': '20px',
            'fontFamily': 'Arial, sans-serif'
        })
    ])

def create_register_layout():
    """Create registration page layout"""
    return html.Div([
        # Session stores
        session_store,
        user_store,
        
        html.Div([
            html.Div([
                html.H1("Bloomberg Terminal Dashboard", 
                        style={'color': THEME['text'], 'textAlign': 'center', 'marginBottom': '10px'}),
                html.P("Create your account to access the dashboard", 
                       style={'color': THEME['accent'], 'textAlign': 'center', 'marginBottom': '30px'}),
                
                # Registration Form
                html.Div([
                    html.H3("Create Account", style={'color': THEME['text'], 'marginBottom': '20px'}),
                    
                    # Username field
                    html.Div([
                        html.Label("Username:", style={'color': THEME['text'], 'marginBottom': '5px', 'display': 'block'}),
                        dcc.Input(
                            id='register-username',
                            type='text',
                            placeholder='Choose a username',
                            style={
                                'width': '100%',
                                'padding': '10px',
                                'marginBottom': '15px',
                                'borderRadius': '5px',
                                'border': '1px solid #555',
                                'backgroundColor': THEME['background'],
                                'color': THEME['text']
                            }
                        )
                    ]),
                    
                    # Email field
                    html.Div([
                        html.Label("Email:", style={'color': THEME['text'], 'marginBottom': '5px', 'display': 'block'}),
                        dcc.Input(
                            id='register-email',
                            type='email',
                            placeholder='Enter your email',
                            style={
                                'width': '100%',
                                'padding': '10px',
                                'marginBottom': '15px',
                                'borderRadius': '5px',
                                'border': '1px solid #555',
                                'backgroundColor': THEME['background'],
                                'color': THEME['text']
                            }
                        )
                    ]),
                    
                    # Password field
                    html.Div([
                        html.Label("Password:", style={'color': THEME['text'], 'marginBottom': '5px', 'display': 'block'}),
                        dcc.Input(
                            id='register-password',
                            type='password',
                            placeholder='Choose a password',
                            style={
                                'width': '100%',
                                'padding': '10px',
                                'marginBottom': '15px',
                                'borderRadius': '5px',
                                'border': '1px solid #555',
                                'backgroundColor': THEME['background'],
                                'color': THEME['text']
                            }
                        )
                    ]),
                    
                    # Confirm Password field
                    html.Div([
                        html.Label("Confirm Password:", style={'color': THEME['text'], 'marginBottom': '5px', 'display': 'block'}),
                        dcc.Input(
                            id='register-confirm-password',
                            type='password',
                            placeholder='Confirm your password',
                            style={
                                'width': '100%',
                                'padding': '10px',
                                'marginBottom': '20px',
                                'borderRadius': '5px',
                                'border': '1px solid #555',
                                'backgroundColor': THEME['background'],
                                'color': THEME['text']
                            }
                        )
                    ]),
                    
                    # Register button
                    html.Button(
                        "Create Account",
                        id='register-button',
                        n_clicks=0,
                        style={
                            'width': '100%',
                            'padding': '12px',
                            'backgroundColor': THEME['accent'],
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '5px',
                            'cursor': 'pointer',
                            'fontSize': '16px',
                            'marginBottom': '15px'
                        }
                    ),
                    
                    # Error/Success message
                    html.Div(id='register-message', style={'textAlign': 'center', 'marginBottom': '15px'}),
                    
                    # Login link
                    html.Div([
                        html.P("Already have an account? ", style={'color': THEME['text'], 'display': 'inline'}),
                        html.A("Sign In", 
                               id='show-login-link',
                               style={'color': THEME['accent'], 'cursor': 'pointer', 'textDecoration': 'underline'})
                    ], style={'textAlign': 'center'})
                    
                ], style={
                    'backgroundColor': THEME['card_background'],
                    'padding': '30px',
                    'borderRadius': '10px',
                    'width': '100%',
                    'maxWidth': '400px'
                })
                
            ], style={
                'display': 'flex',
                'flexDirection': 'column',
                'alignItems': 'center',
                'minHeight': '100vh',
                'justifyContent': 'center'
            })
        ], style={
            'backgroundColor': THEME['background'],
            'minHeight': '100vh',
            'padding': '20px',
            'fontFamily': 'Arial, sans-serif'
        })
    ])

def create_dashboard_layout():
    """Create main dashboard layout"""
    return html.Div([
        # Session stores
        session_store,
        user_store,
        
        # Header with logout
        html.Div([
            html.Div([
                html.H1("Bloomberg Terminal Integration Dashboard", 
                        style={'color': THEME['text'], 'margin': '0', 'display': 'inline-block'}),
                html.Div([
                    html.Span(id='current-user-display', style={'color': THEME['accent'], 'marginRight': '15px'}),
                    html.Button(
                        "Logout",
                        id='logout-button',
                        style={
                            'backgroundColor': THEME['danger'],
                            'color': 'white',
                            'border': 'none',
                            'padding': '8px 16px',
                            'borderRadius': '5px',
                            'cursor': 'pointer'
                        }
                    )
                ], style={'float': 'right'})
            ], style={'overflow': 'hidden', 'marginBottom': '10px'}),
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
        
        # Chart section
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

# Initial layout with URL routing
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])

# Authentication callbacks
@callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')],
    [State('session-store', 'data')]
)
def display_page(pathname, session_data):
    """Route pages based on authentication status"""
    try:
        # Check if user has valid session
        session_id = session_data.get('session_id') if session_data else None
        
        if session_id:
            try:
                valid, user = auth_manager.validate_session(session_id)
                if valid:
                    # User is authenticated, show dashboard
                    return create_dashboard_layout()
            except Exception as e:
                logger.error(f"Session validation error: {e}")
        
        # Not authenticated, show login page
        if pathname == '/register':
            return create_register_layout()
        else:
            return create_login_layout()
            
    except Exception as e:
        logger.error(f"Page routing error: {e}")
        return create_login_layout()

@callback(
    [Output('session-store', 'data'),
     Output('user-store', 'data'),
     Output('login-error', 'children'),
     Output('url', 'pathname')],
    [Input('login-button', 'n_clicks')],
    [State('login-username', 'value'),
     State('login-password', 'value')],
    prevent_initial_call=True
)
def handle_login(n_clicks, username, password):
    """Handle user login"""
    if not n_clicks:
        return {}, {}, "", "/"
    
    if not username or not password:
        return {}, {}, "Please enter both username and password", "/"
    
    try:
        success, user, error_msg = auth_manager.authenticate_user(username, password)
        
        if success:
            session_data = {'session_id': auth_manager.get_current_session_id()}
            user_data = {'username': user.username, 'role': user.role}
            return session_data, user_data, "", "/dashboard"
        else:
            return {}, {}, error_msg or "Login failed", "/"
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return {}, {}, "An error occurred during login", "/"

@callback(
    [Output('register-message', 'children'),
     Output('register-message', 'style'),
     Output('url', 'pathname', allow_duplicate=True)],
    [Input('register-button', 'n_clicks')],
    [State('register-username', 'value'),
     State('register-email', 'value'),
     State('register-password', 'value'),
     State('register-confirm-password', 'value')],
    prevent_initial_call=True
)
def handle_register(n_clicks, username, email, password, confirm_password):
    """Handle user registration"""
    if not n_clicks:
        return "", {}, "/register"
    
    # Validation
    if not all([username, email, password, confirm_password]):
        return "Please fill in all fields", {'color': THEME['danger']}, "/register"
    
    if password != confirm_password:
        return "Passwords do not match", {'color': THEME['danger']}, "/register"
    
    if len(password) < 6:
        return "Password must be at least 6 characters long", {'color': THEME['danger']}, "/register"
    
    try:
        success, error_msg = auth_manager.create_user_account(username, email, password)
        
        if success:
            return "Account created successfully! You can now sign in.", {'color': THEME['success']}, "/"
        else:
            return error_msg or "Registration failed", {'color': THEME['danger']}, "/register"
            
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return "An error occurred during registration", {'color': THEME['danger']}, "/register"

@callback(
    [Output('session-store', 'data', allow_duplicate=True),
     Output('user-store', 'data', allow_duplicate=True),
     Output('url', 'pathname', allow_duplicate=True)],
    [Input('logout-button', 'n_clicks')],
    prevent_initial_call=True
)
def handle_logout(n_clicks):
    """Handle user logout"""
    if n_clicks:
        auth_manager.logout_user()
        return {}, {}, "/"
    return {}, {}, "/dashboard"

@callback(
    Output('current-user-display', 'children'),
    [Input('user-store', 'data')],
    prevent_initial_call=True
)
def update_current_user_display(user_data):
    """Update current user display"""
    try:
        if user_data and user_data.get('username'):
            return f"Welcome, {user_data['username']}"
        return ""
    except Exception:
        return ""

# Page navigation callbacks
@callback(
    Output('url', 'pathname', allow_duplicate=True),
    [Input('show-register-link', 'n_clicks')],
    prevent_initial_call=True
)
def show_register_page(n_clicks):
    if n_clicks:
        return "/register"
    return "/"

@callback(
    Output('url', 'pathname', allow_duplicate=True),
    [Input('show-login-link', 'n_clicks')],
    prevent_initial_call=True
)
def show_login_page(n_clicks):
    if n_clicks:
        return "/"
    return "/register"

# Dashboard callbacks (only active when authenticated)
@callback(
    [Output('price-cards-container', 'children'),
     Output('connection-status', 'children')],
    [Input('interval-component', 'n_intervals')],
    prevent_initial_call=True
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

@callback(
    Output('simple-price-chart', 'figure'),
    [Input('metal-selector', 'value'),
     Input('interval-component', 'n_intervals')],
    prevent_initial_call=True
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