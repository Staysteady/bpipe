import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import os
from mastodon import Mastodon
import json

try:
    from ..config import config
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from config import config

class MastodonClient:
    """Mastodon API client for social media integration"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.mastodon = None
        self.is_connected = False
        self.credentials_file = 'data/mastodon_credentials.json'
        self.app_name = "Bloomberg Terminal Dashboard"
        
    def create_app(self, instance_url: str) -> Dict[str, str]:
        """
        Create Mastodon app and get client credentials
        
        Args:
            instance_url: Mastodon instance URL (e.g., 'https://mastodon.social')
            
        Returns:
            Dictionary with client_id and client_secret
        """
        try:
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.credentials_file), exist_ok=True)
            
            # Create app
            client_id, client_secret = Mastodon.create_app(
                self.app_name,
                api_base_url=instance_url,
                scopes=['read', 'write']
            )
            
            credentials = {
                'client_id': client_id,
                'client_secret': client_secret,
                'instance_url': instance_url
            }
            
            # Save credentials
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f)
                
            self.logger.info(f"Created Mastodon app for {instance_url}")
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to create Mastodon app: {e}")
            raise
    
    def get_auth_url(self, instance_url: str) -> str:
        """
        Get OAuth authorization URL
        
        Args:
            instance_url: Mastodon instance URL
            
        Returns:
            Authorization URL for user to visit
        """
        try:
            # Load or create app credentials
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file, 'r') as f:
                    credentials = json.load(f)
                    
                if credentials.get('instance_url') != instance_url:
                    credentials = self.create_app(instance_url)
            else:
                credentials = self.create_app(instance_url)
            
            # Initialize Mastodon client
            self.mastodon = Mastodon(
                client_id=credentials['client_id'],
                client_secret=credentials['client_secret'],
                api_base_url=instance_url
            )
            
            # Get authorization URL
            auth_url = self.mastodon.auth_request_url(
                scopes=['read', 'write'],
                redirect_uris='urn:ietf:wg:oauth:2.0:oob'  # For manual code entry
            )
            
            return auth_url
            
        except Exception as e:
            self.logger.error(f"Failed to get auth URL: {e}")
            raise
    
    def authenticate_with_code(self, auth_code: str) -> bool:
        """
        Complete OAuth authentication with authorization code
        
        Args:
            auth_code: Authorization code from user
            
        Returns:
            True if authentication successful
        """
        try:
            if not self.mastodon:
                raise ValueError("Must call get_auth_url first")
            
            # Exchange code for access token
            access_token = self.mastodon.log_in(
                code=auth_code,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob',
                scopes=['read', 'write']
            )
            
            # Update credentials file with access token
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)
            
            credentials['access_token'] = access_token
            
            with open(self.credentials_file, 'w') as f:
                json.dump(credentials, f)
            
            self.is_connected = True
            self.logger.info("Successfully authenticated with Mastodon")
            return True
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    def connect_with_saved_credentials(self) -> bool:
        """
        Connect using saved credentials
        
        Returns:
            True if connection successful
        """
        try:
            if not os.path.exists(self.credentials_file):
                self.logger.warning("No saved credentials found")
                return False
            
            with open(self.credentials_file, 'r') as f:
                credentials = json.load(f)
            
            if 'access_token' not in credentials:
                self.logger.warning("No access token in saved credentials")
                return False
            
            # Initialize authenticated client
            self.mastodon = Mastodon(
                access_token=credentials['access_token'],
                api_base_url=credentials['instance_url']
            )
            
            # Test connection
            account = self.mastodon.me()
            self.is_connected = True
            self.logger.info(f"Connected to Mastodon as @{account['username']}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect with saved credentials: {e}")
            return False
    
    def get_following_list(self) -> List[Dict[str, Any]]:
        """
        Get list of accounts the user is following
        
        Returns:
            List of account dictionaries
        """
        if not self.is_connected or not self.mastodon:
            raise ConnectionError("Not connected to Mastodon")
        
        try:
            account = self.mastodon.me()
            following = self.mastodon.account_following(account['id'])
            
            # Format for dashboard use
            formatted_following = []
            for account in following:
                formatted_following.append({
                    'id': account['id'],
                    'username': account['username'],
                    'display_name': account['display_name'] or account['username'],
                    'url': account['url'],
                    'avatar': account['avatar'],
                    'followers_count': account['followers_count'],
                    'following_count': account['following_count']
                })
            
            self.logger.info(f"Retrieved {len(formatted_following)} following accounts")
            return formatted_following
            
        except Exception as e:
            self.logger.error(f"Failed to get following list: {e}")
            return []
    
    def get_recent_posts(self, account_ids: List[str], limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent posts from specified accounts
        
        Args:
            account_ids: List of account IDs to get posts from
            limit: Maximum number of posts per account
            
        Returns:
            List of post dictionaries
        """
        if not self.is_connected or not self.mastodon:
            raise ConnectionError("Not connected to Mastodon")
        
        try:
            all_posts = []
            
            for account_id in account_ids:
                posts = self.mastodon.account_statuses(account_id, limit=limit)
                
                for post in posts:
                    formatted_post = {
                        'id': post['id'],
                        'account_id': post['account']['id'],
                        'account_username': post['account']['username'],
                        'account_display_name': post['account']['display_name'],
                        'content': post['content'],
                        'created_at': post['created_at'],
                        'url': post['url'],
                        'favourites_count': post['favourites_count'],
                        'reblogs_count': post['reblogs_count'],
                        'replies_count': post['replies_count'],
                        'media_attachments': [att['url'] for att in post['media_attachments']]
                    }
                    all_posts.append(formatted_post)
            
            # Sort by creation time (newest first)
            all_posts.sort(key=lambda x: x['created_at'], reverse=True)
            
            self.logger.info(f"Retrieved {len(all_posts)} posts from {len(account_ids)} accounts")
            return all_posts[:limit]  # Return only the most recent posts overall
            
        except Exception as e:
            self.logger.error(f"Failed to get recent posts: {e}")
            return []
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get authenticated user information
        
        Returns:
            User account dictionary
        """
        if not self.is_connected or not self.mastodon:
            return None
        
        try:
            account = self.mastodon.me()
            return {
                'id': account['id'],
                'username': account['username'],
                'display_name': account['display_name'],
                'url': account['url'],
                'avatar': account['avatar'],
                'followers_count': account['followers_count'],
                'following_count': account['following_count'],
                'statuses_count': account['statuses_count']
            }
        except Exception as e:
            self.logger.error(f"Failed to get user info: {e}")
            return None
    
    def disconnect(self):
        """Disconnect from Mastodon"""
        self.mastodon = None
        self.is_connected = False
        self.logger.info("Disconnected from Mastodon")
    
    def health_check(self) -> Dict[str, Any]:
        """Check Mastodon connection health"""
        return {
            'connected': self.is_connected,
            'has_credentials': os.path.exists(self.credentials_file),
            'timestamp': datetime.now().isoformat(),
            'user_info': self.get_user_info() if self.is_connected else None
        }