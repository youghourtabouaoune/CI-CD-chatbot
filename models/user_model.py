# user_model.py (FIXED - All critical bugs resolved)
import os
import json
import secrets
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
import uuid

class UserManager:
    def __init__(self, users_file='data/users.json'):
        self.users_file = users_file
        self.users = self._load_users()
        self._ensure_data_directory()
        
        # Security settings
        self.MAX_LOGIN_ATTEMPTS = 5
        self.LOCKOUT_DURATION = timedelta(minutes=30)
        self.PASSWORD_RESET_TIMEOUT = timedelta(hours=1)
        self.EMAIL_VERIFICATION_TIMEOUT = timedelta(hours=24)

    def _ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        # Ensure user-specific directories exist for all users
        if self.users:
            for user_id in self.users.keys():
                user_data_dir = f'data/users/{user_id}'
                os.makedirs(user_data_dir, exist_ok=True)

    def _load_users(self) -> Dict[str, Dict]:
        """Load users from JSON file"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not load users file: {e}")
        return {}

    def _save_users(self) -> bool:
        """Save users to JSON file"""
        try:
            # Ensure directory exists before saving
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving users: {e}")
            return False

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against bcrypt hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False

    def is_account_locked(self, user_data: Dict) -> bool:
        """Check if account is temporarily locked"""
        if user_data.get('login_attempts', 0) >= self.MAX_LOGIN_ATTEMPTS:
            lockout_until = user_data.get('lockout_until')
            if lockout_until:
                try:
                    lockout_time = datetime.fromisoformat(lockout_until)
                    if datetime.utcnow() < lockout_time:
                        return True
                    else:
                        # Reset lockout if time has passed
                        user_data['login_attempts'] = 0
                        user_data['lockout_until'] = None
                        # CRITICAL FIX: Save after modification
                        self._save_users()
                except (ValueError, TypeError):
                    # Invalid lockout_until format, reset
                    user_data['login_attempts'] = 0
                    user_data['lockout_until'] = None
                    self._save_users()
        return False

    def record_login_attempt(self, user_data: Dict, success: bool):
        """Record login attempt and handle lockout"""
        if success:
            user_data['login_attempts'] = 0
            user_data['lockout_until'] = None
            user_data['last_login'] = datetime.utcnow().isoformat()
        else:
            user_data['login_attempts'] = user_data.get('login_attempts', 0) + 1
            if user_data['login_attempts'] >= self.MAX_LOGIN_ATTEMPTS:
                user_data['lockout_until'] = (datetime.utcnow() + self.LOCKOUT_DURATION).isoformat()
        
        user_data['updated_at'] = datetime.utcnow().isoformat()
        # CRITICAL FIX: Always save after recording attempt
        self._save_users()

    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength"""
        if len(password) < 8:
            return {'valid': False, 'message': 'Password must be at least 8 characters long'}
        
        if not any(c.isupper() for c in password):
            return {'valid': False, 'message': 'Password must contain at least one uppercase letter'}
        
        if not any(c.islower() for c in password):
            return {'valid': False, 'message': 'Password must contain at least one lowercase letter'}
        
        if not any(c.isdigit() for c in password):
            return {'valid': False, 'message': 'Password must contain at least one number'}
        
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in password):
            return {'valid': False, 'message': 'Password must contain at least one special character'}
        
        return {'valid': True, 'message': 'Password is strong'}

    def create_user(self, email: str, password: str, first_name: str, last_name: str, 
                   accept_terms: bool = False, oauth_provider: str = None, 
                   oauth_id: str = None) -> Optional[Dict]:
        """Create a new user with enhanced security - FIXED VERSION"""
        # Check if user already exists
        for user_id, user_data in self.users.items():
            if user_data['email'].lower() == email.lower():
                return None

        # Validate password strength (only for non-OAuth users)
        if not oauth_provider:
            password_check = self.validate_password_strength(password)
            if not password_check['valid']:
                raise ValueError(password_check['message'])

        # Create new user ID
        user_id = str(uuid.uuid4())
        
        # Create user object
        user = {
            'id': user_id,
            'email': email.lower(),
            'password_hash': self.hash_password(password) if not oauth_provider else None,
            'first_name': first_name,
            'last_name': last_name,
            'api_key': None,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
            'last_login': None,
            'email_verified': bool(oauth_provider),  # OAuth users are automatically verified
            'email_verification_token': None,
            'email_verification_sent_at': None,
            'password_reset_token': None,
            'password_reset_sent_at': None,
            'login_attempts': 0,
            'lockout_until': None,
            'terms_accepted': accept_terms,
            'terms_accepted_at': datetime.utcnow().isoformat() if accept_terms else None,
            'privacy_policy_accepted': accept_terms,
            'privacy_policy_accepted_at': datetime.utcnow().isoformat() if accept_terms else None,
            'oauth_provider': oauth_provider,
            'oauth_id': oauth_id,
            'is_active': True
        }

        # CRITICAL FIX: Add user to dictionary BEFORE creating directories
        self.users[user_id] = user
        
        try:
            # Create user-specific directories with proper error handling
            user_data_dir = f'data/users/{user_id}'
            os.makedirs(user_data_dir, exist_ok=True)
            
            # Initialize user data files with error handling
            self._save_user_data(user_id, 'conversations', {})
            self._save_user_data(user_id, 'files', [])
            self._save_user_data(user_id, 'session_data', {
                'current_conversation_id': None,
                'conversations': {},
                'user_preferences': {},
                'last_active': datetime.utcnow().isoformat()
            })
        except Exception as e:
            print(f"Warning: Could not initialize user data files: {e}")
            # Continue anyway - files will be created on first use
        
        # CRITICAL FIX: Save users to file
        if self._save_users():
            return user
        else:
            # Rollback - remove user from dictionary on save failure
            del self.users[user_id]
            return None

    def generate_verification_token(self, user_id: str) -> str:
        """Generate email verification token"""
        token = secrets.token_urlsafe(32)
        user = self.get_user_by_id(user_id)
        if user:
            user['email_verification_token'] = token
            user['email_verification_sent_at'] = datetime.utcnow().isoformat()
            user['updated_at'] = datetime.utcnow().isoformat()
            # CRITICAL FIX: Save after modification
            self._save_users()
        return token

    def verify_email(self, token: str) -> bool:
        """Verify email using token"""
        for user_id, user_data in self.users.items():
            if user_data.get('email_verification_token') == token:
                # Check if token is expired
                sent_at = user_data.get('email_verification_sent_at')
                if sent_at:
                    try:
                        sent_time = datetime.fromisoformat(sent_at)
                        if datetime.utcnow() - sent_time > self.EMAIL_VERIFICATION_TIMEOUT:
                            return False
                    except (ValueError, TypeError):
                        return False
                
                user_data['email_verified'] = True
                user_data['email_verification_token'] = None
                user_data['email_verification_sent_at'] = None
                user_data['updated_at'] = datetime.utcnow().isoformat()
                # CRITICAL FIX: Save after modification
                self._save_users()
                return True
        return False

    def generate_password_reset_token(self, email: str) -> Optional[str]:
        """Generate password reset token"""
        user = self.get_user_by_email(email)
        if user:
            token = secrets.token_urlsafe(32)
            user['password_reset_token'] = token
            user['password_reset_sent_at'] = datetime.utcnow().isoformat()
            user['updated_at'] = datetime.utcnow().isoformat()
            # CRITICAL FIX: Save after modification
            self._save_users()
            return token
        return None

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token"""
        # Validate password strength
        password_check = self.validate_password_strength(new_password)
        if not password_check['valid']:
            raise ValueError(password_check['message'])
            
        for user_id, user_data in self.users.items():
            if user_data.get('password_reset_token') == token:
                # Check if token is expired
                sent_at = user_data.get('password_reset_sent_at')
                if sent_at:
                    try:
                        sent_time = datetime.fromisoformat(sent_at)
                        if datetime.utcnow() - sent_time > self.PASSWORD_RESET_TIMEOUT:
                            return False
                    except (ValueError, TypeError):
                        return False
                
                user_data['password_hash'] = self.hash_password(new_password)
                user_data['password_reset_token'] = None
                user_data['password_reset_sent_at'] = None
                user_data['login_attempts'] = 0  # Reset login attempts
                user_data['lockout_until'] = None  # Clear any lockout
                user_data['updated_at'] = datetime.utcnow().isoformat()
                # CRITICAL FIX: Save after modification
                self._save_users()
                return True
        return False

    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user with enhanced security - FIXED VERSION"""
        user = self.get_user_by_email(email)
        if not user:
            return None
        
        # Store user_id before any modifications
        user_id = user['id']
        
        if not user.get('is_active', True):
            return None

        # Check if account is locked
        if self.is_account_locked(user):
            raise Exception('Account temporarily locked due to too many failed login attempts')

        # For OAuth users without password
        if user.get('oauth_provider') and not user.get('password_hash'):
            raise Exception('Please use OAuth login for this account')

        # Verify password
        if user.get('password_hash') and self.verify_password(password, user['password_hash']):
            self.record_login_attempt(user, True)
            # CRITICAL FIX: Return fresh copy to ensure we have updated data
            return self.get_user_by_id(user_id)
        else:
            self.record_login_attempt(user, False)
            return None

    def get_user_by_oauth(self, provider: str, oauth_id: str) -> Optional[Dict]:
        """Get user by OAuth provider and ID"""
        for user_id, user_data in self.users.items():
            if (user_data.get('oauth_provider') == provider and 
                user_data.get('oauth_id') == oauth_id):
                return user_data
        return None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        email = email.lower()
        for user_id, user_data in self.users.items():
            if user_data['email'] == email:
                return user_data
        return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        return self.users.get(user_id)

    def update_user_api_key(self, user_id: str, api_key: str) -> bool:
        """Update user's API key"""
        user = self.get_user_by_id(user_id)
        if user:
            user['api_key'] = api_key
            user['updated_at'] = datetime.utcnow().isoformat()
            # CRITICAL FIX: Save after modification
            return self._save_users()
        return False

    def update_user_password(self, user_id: str, new_password: str) -> bool:
        """Update user's password"""
        # Validate password strength
        password_check = self.validate_password_strength(new_password)
        if not password_check['valid']:
            raise ValueError(password_check['message'])
            
        user = self.get_user_by_id(user_id)
        if user:
            user['password_hash'] = self.hash_password(new_password)
            user['updated_at'] = datetime.utcnow().isoformat()
            # CRITICAL FIX: Save after modification
            return self._save_users()
        return False

    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login time"""
        user = self.get_user_by_id(user_id)
        if user:
            user['last_login'] = datetime.utcnow().isoformat()
            user['updated_at'] = datetime.utcnow().isoformat()
            # CRITICAL FIX: Save after modification
            return self._save_users()
        return False

    def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        """Get user by API key"""
        for user_id, user_data in self.users.items():
            if user_data.get('api_key') == api_key:
                return user_data
        return None

    def _get_user_data_file(self, user_id: str, data_type: str) -> str:
        """Get path for user-specific data file"""
        user_data_dir = f'data/users/{user_id}'
        os.makedirs(user_data_dir, exist_ok=True)
        return os.path.join(user_data_dir, f'{data_type}.json')

    def _load_user_data(self, user_id: str, data_type: str) -> Dict:
        """Load user-specific data"""
        data_file = self._get_user_data_file(user_id, data_type)
        try:
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not load {data_type} for user {user_id}: {e}")
        return {} if data_type != 'files' else []

    def _save_user_data(self, user_id: str, data_type: str, data: Any) -> bool:
        """Save user-specific data"""
        try:
            data_file = self._get_user_data_file(user_id, data_type)
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving {data_type} for user {user_id}: {e}")
            return False

    def get_user_conversations(self, user_id: str) -> Dict:
        """Get user's conversations"""
        return self._load_user_data(user_id, 'conversations')

    def save_user_conversations(self, user_id: str, conversations: Dict) -> bool:
        """Save user's conversations"""
        return self._save_user_data(user_id, 'conversations', conversations)

    def get_user_files(self, user_id: str) -> List:
        """Get user's files"""
        data = self._load_user_data(user_id, 'files')
        return data if isinstance(data, list) else []

    def save_user_files(self, user_id: str, files: List) -> bool:
        """Save user's files"""
        return self._save_user_data(user_id, 'files', files)

    def get_user_session_data(self, user_id: str) -> Dict:
        """Get user's session data"""
        return self._load_user_data(user_id, 'session_data')

    def save_user_session_data(self, user_id: str, session_data: Dict) -> bool:
        """Save user's session data"""
        return self._save_user_data(user_id, 'session_data', session_data)

    def update_user_preferences(self, user_id: str, preferences: Dict) -> bool:
        """Update user's preferences"""
        session_data = self.get_user_session_data(user_id)
        session_data['user_preferences'] = preferences
        session_data['last_active'] = datetime.utcnow().isoformat()
        return self.save_user_session_data(user_id, session_data)

    def get_user_preferences(self, user_id: str) -> Dict:
        """Get user's preferences"""
        session_data = self.get_user_session_data(user_id)
        return session_data.get('user_preferences', {})

    def save_user_conversation(self, user_id: str, conversation_id: str, conversation_data: Dict) -> bool:
        """Save a specific conversation for user"""
        conversations = self.get_user_conversations(user_id)
        conversations[conversation_id] = conversation_data
        return self.save_user_conversations(user_id, conversations)

    def get_user_conversation(self, user_id: str, conversation_id: str) -> Optional[Dict]:
        """Get a specific conversation for user"""
        conversations = self.get_user_conversations(user_id)
        return conversations.get(conversation_id)

    def delete_user_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Delete a specific conversation for user"""
        conversations = self.get_user_conversations(user_id)
        if conversation_id in conversations:
            del conversations[conversation_id]
            return self.save_user_conversations(user_id, conversations)
        return False

    def update_current_conversation(self, user_id: str, conversation_id: str) -> bool:
        """Update user's current conversation"""
        session_data = self.get_user_session_data(user_id)
        session_data['current_conversation_id'] = conversation_id
        session_data['last_active'] = datetime.utcnow().isoformat()
        return self.save_user_session_data(user_id, session_data)

    def get_current_conversation(self, user_id: str) -> Optional[str]:
        """Get user's current conversation ID"""
        session_data = self.get_user_session_data(user_id)
        return session_data.get('current_conversation_id')

    def get_all_users(self) -> List[Dict]:
        """Get all users (for admin purposes)"""
        return list(self.users.values())

    def delete_user(self, user_id: str) -> bool:
        """Delete user and all their data"""
        try:
            # Remove user from users dictionary
            if user_id in self.users:
                del self.users[user_id]
            
            # Remove user data directory
            user_data_dir = f'data/users/{user_id}'
            if os.path.exists(user_data_dir):
                import shutil
                shutil.rmtree(user_data_dir)
            
            # CRITICAL FIX: Save after modification
            return self._save_users()
        except Exception as e:
            print(f"Error deleting user {user_id}: {e}")
            return False

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        user = self.get_user_by_id(user_id)
        if not user:
            return {}
        
        conversations = self.get_user_conversations(user_id)
        files = self.get_user_files(user_id)
        session_data = self.get_user_session_data(user_id)
        
        return {
            'user_id': user_id,
            'email': user['email'],
            'first_name': user['first_name'],
            'last_name': user['last_name'],
            'created_at': user['created_at'],
            'last_login': user.get('last_login'),
            'conversation_count': len(conversations),
            'file_count': len(files),
            'last_active': session_data.get('last_active'),
            'current_conversation': session_data.get('current_conversation_id')
        }
    
    def link_oauth_to_user(self, user_id: str, provider: str, oauth_id: str) -> bool:
        """Link OAuth provider to existing user"""
        user = self.get_user_by_id(user_id)
        if user:
            user['oauth_provider'] = provider
            user['oauth_id'] = oauth_id
            user['updated_at'] = datetime.utcnow().isoformat()
            # CRITICAL FIX: Save after modification
            return self._save_users()
        return False