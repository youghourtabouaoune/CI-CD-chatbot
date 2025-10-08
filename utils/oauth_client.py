# oauth_client.py (enhanced)
import os
import requests
from typing import Optional, Dict, Any
import secrets
from urllib.parse import urlencode

class OAuthClient:
    def __init__(self):
        self.config = {
            'google': {
                'client_id': os.environ.get('GOOGLE_OAUTH_CLIENT_ID'),
                'client_secret': os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET'),
                'auth_url': 'https://accounts.google.com/o/oauth2/auth',
                'token_url': 'https://oauth2.googleapis.com/token',
                'userinfo_url': 'https://www.googleapis.com/oauth2/v3/userinfo',
                'scope': 'openid email profile'
            },
            'github': {
                'client_id': os.environ.get('GITHUB_OAUTH_CLIENT_ID'),
                'client_secret': os.environ.get('GITHUB_OAUTH_CLIENT_SECRET'),
                'auth_url': 'https://github.com/login/oauth/authorize',
                'token_url': 'https://github.com/login/oauth/access_token',
                'userinfo_url': 'https://api.github.com/user',
                'user_emails_url': 'https://api.github.com/user/emails',
                'scope': 'user:email'
            }
        }

    def get_auth_url(self, provider: str, redirect_uri: str, state: str = None) -> Optional[str]:
        """Get OAuth authorization URL with state parameter for CSRF protection"""
        config = self.config.get(provider)
        if not config or not config['client_id']:
            return None

        params = {
            'client_id': config['client_id'],
            'redirect_uri': redirect_uri,
            'scope': config['scope'],
            'response_type': 'code'
        }

        if state:
            params['state'] = state

        if provider == 'google':
            params['access_type'] = 'offline'
            params['prompt'] = 'consent'
        
        return f"{config['auth_url']}?{urlencode(params)}"

    def exchange_code_for_token(self, provider: str, code: str, redirect_uri: str) -> Optional[Dict]:
        """Exchange authorization code for access token"""
        config = self.config.get(provider)
        if not config:
            return None

        data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'code': code,
            'redirect_uri': redirect_uri
        }

        headers = {}
        
        if provider == 'google':
            data['grant_type'] = 'authorization_code'
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            response = requests.post(config['token_url'], data=data, headers=headers)
        elif provider == 'github':
            headers['Accept'] = 'application/json'
            response = requests.post(config['token_url'], data=data, headers=headers)
        else:
            return None

        if response.status_code == 200:
            return response.json()
        return None

    def get_user_info(self, provider: str, access_token: str) -> Optional[Dict]:
        """Get user information from OAuth provider"""
        config = self.config.get(provider)
        if not config:
            return None

        headers = {}
        if provider == 'google':
            headers['Authorization'] = f'Bearer {access_token}'
            response = requests.get(config['userinfo_url'], headers=headers)
        elif provider == 'github':
            headers['Authorization'] = f'token {access_token}'
            headers['Accept'] = 'application/vnd.github.v3+json'
            response = requests.get(config['userinfo_url'], headers=headers)
        else:
            return None

        if response.status_code == 200:
            user_info = response.json()
            
            if provider == 'google':
                return {
                    'id': user_info['sub'],
                    'email': user_info['email'],
                    'verified_email': user_info.get('email_verified', False),
                    'first_name': user_info.get('given_name', ''),
                    'last_name': user_info.get('family_name', ''),
                    'picture': user_info.get('picture'),
                    'locale': user_info.get('locale'),
                    'provider': 'google'
                }
            elif provider == 'github':
                # Get primary email from GitHub
                email_response = requests.get(config['user_emails_url'], headers=headers)
                email = user_info.get('email', '')
                verified_email = False
                
                if email_response.status_code == 200:
                    emails = email_response.json()
                    primary_email = next((e for e in emails if e.get('primary') and e.get('verified')), None)
                    if primary_email:
                        email = primary_email.get('email')
                        verified_email = True
                    elif not email and emails:
                        # Fallback to first verified email
                        verified_email_obj = next((e for e in emails if e.get('verified')), None)
                        if verified_email_obj:
                            email = verified_email_obj.get('email')
                            verified_email = True

                # Split name into first and last name
                name_parts = user_info.get('name', '').split(' ', 1)
                first_name = name_parts[0] if name_parts else ''
                last_name = name_parts[1] if len(name_parts) > 1 else ''

                return {
                    'id': str(user_info['id']),
                    'email': email,
                    'verified_email': verified_email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'username': user_info.get('login'),
                    'picture': user_info.get('avatar_url'),
                    'blog': user_info.get('blog'),
                    'provider': 'github'
                }

        return None

    def validate_state(self, state: str, stored_state: str) -> bool:
        """Validate state parameter to prevent CSRF attacks"""
        return secrets.compare_digest(state, stored_state)