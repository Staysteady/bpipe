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

# Create a simple unified layout that includes both login and dashboard
app.layout = html.Div([
    # Session stores (always present)
    dcc.Store(id='session-store', storage_type='session'),
    dcc.Store(id='user-store', storage_type='session'),
    dcc.Location(id='url', refresh=False),
    
    # Main content area
    html.Div(id='page-content'),
    
    # Hidden components that callbacks might reference (prevents callback errors)
    html.Div([
        html.Div(id='login-error', style={'display': 'none'}),
        html.Div(id='register-message', style={'display': 'none'}),
        html.Div(id='current-user-display', style={'display': 'none'}),
        html.Div(id='connection-status', style={'display': 'none'}),
        html.Div(id='price-cards-container', style={'display': 'none'}),
        dcc.Graph(id='simple-price-chart', style={'display': 'none'}),
        dcc.Dropdown(id='metal-selector', style={'display': 'none'}),
        dcc.Interval(id='interval-component', interval=30000, disabled=True),
        html.Button(id='login-button', style={'display': 'none'}),
        html.Button(id='register-button', style={'display': 'none'}),
        html.Button(id='logout-button', style={'display': 'none'}),
        html.A(id='show-register-link', style={'display': 'none'}),
        html.A(id='show-login-link', style={'display': 'none'}),
        dcc.Input(id='login-username', style={'display': 'none'}),
        dcc.Input(id='login-password', style={'display': 'none'}),
        dcc.Input(id='register-username', style={'display': 'none'}),
        dcc.Input(id='register-email', style={'display': 'none'}),
        dcc.Input(id='register-password', style={'display': 'none'}),
        dcc.Input(id='register-confirm-password', style={'display': 'none'}),
    ], id='hidden-components', style={'display': 'none'})
])

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
                    return create_dashboard_page()
            except Exception as e:
                logger.error(f"Session validation error: {e}")
        
        # Not authenticated, show login page
        if pathname == '/register':
            return create_register_page()
        else:
            return create_login_page()
            
    except Exception as e:
        logger.error(f"Page routing error: {e}")
        return create_login_page()

def create_login_page():
    """Create login page"""
    return html.Div([
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
                            id='login-username-active',
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
                            id='login-password-active',
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
                        id='login-button-active',
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
                    html.Div(id='login-error-active', style={'color': THEME['danger'], 'textAlign': 'center', 'marginBottom': '15px'}),
                    
                    # Register link
                    html.Div([
                        html.P("Don't have an account? ", style={'color': THEME['text'], 'display': 'inline'}),
                        html.A("Create Account", 
                               id='show-register-link-active',
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

def create_register_page():
    """Create registration page"""
    return html.Div([
        html.H1("Registration Page", style={'color': THEME['text'], 'textAlign': 'center'}),
        html.P("Registration form will be here", style={'color': THEME['text'], 'textAlign': 'center'}),
        html.A("Back to Login", href="/", style={'color': THEME['accent']})
    ], style={'backgroundColor': THEME['background'], 'minHeight': '100vh', 'padding': '20px'})

def create_dashboard_page():
    """Create dashboard page"""
    return html.Div([
        html.H1("Bloomberg Dashboard", style={'color': THEME['text'], 'textAlign': 'center'}),
        html.P("Welcome to the dashboard!", style={'color': THEME['text'], 'textAlign': 'center'}),
        html.Button("Logout", id='logout-button-active', style={'backgroundColor': THEME['danger'], 'color': 'white', 'border': 'none', 'padding': '10px'})
    ], style={'backgroundColor': THEME['background'], 'minHeight': '100vh', 'padding': '20px'})

# Login callback
@callback(
    [Output('session-store', 'data'),
     Output('user-store', 'data'),
     Output('login-error-active', 'children'),
     Output('url', 'pathname')],
    [Input('login-button-active', 'n_clicks')],
    [State('login-username-active', 'value'),
     State('login-password-active', 'value')],
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

# Navigation callback
@callback(
    Output('url', 'pathname', allow_duplicate=True),
    [Input('show-register-link-active', 'n_clicks')],
    prevent_initial_call=True
)
def show_register_page(n_clicks):
    if n_clicks:
        return "/register"
    return "/"

if __name__ == '__main__':
    app.run_server(debug=True)