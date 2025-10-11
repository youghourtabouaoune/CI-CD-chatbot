import os
import time
import json
import uuid
import hashlib
import platform
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_from_directory, send_file, session, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from config import config
from models.request_models import (
    CodeGenerationRequest, CodeGenerationResponse, 
    DocumentUploadResponse, HealthResponse, LoginRequest, SignupRequest
)
from utils.databricks_client import DatabricksClient
from utils.deepseek_client import DeepSeekClient
from utils.file_processor import FileProcessor
from utils.security import api_key_required, generate_api_key, verify_api_key, sanitize_filename, generate_csrf_token
from models.user_model import UserManager
from utils.oauth_client import OAuthClient
from utils.mail_service import EmailService

# Cross-platform file locking implementation
class CrossPlatformFileLock:
    """Cross-platform file locking that works on both Windows and Unix systems"""
    
    def __init__(self, filename, timeout=10, delay=0.05):
        self.filename = filename
        self.lockfile = f"{filename}.lock"
        self.timeout = timeout
        self.delay = delay
        self.is_locked = False
        self.fd = None
        self.system = platform.system()
        
    def acquire(self):
        """Acquire the lock"""
        start_time = time.time()
        
        while True:
            try:
                if self.system == "Windows":
                    # Windows implementation
                    try:
                        import msvcrt
                        self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                        # Lock the file
                        msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
                    except ImportError:
                        # Fallback for Windows without msvcrt
                        self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                else:
                    # Unix implementation (Linux, macOS)
                    import fcntl
                    self.fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                
                self.is_locked = True
                return True
                
            except (OSError, IOError) as e:
                if e.errno != 17:  # EEXIST
                    raise
                
                if (time.time() - start_time) >= self.timeout:
                    return False
                
                time.sleep(self.delay)
    
    def release(self):
        """Release the lock"""
        if self.is_locked:
            try:
                if self.system == "Windows":
                    try:
                        import msvcrt
                        msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
                    except ImportError:
                        pass
                else:
                    import fcntl
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
                os.close(self.fd)
                try:
                    os.unlink(self.lockfile)
                except:
                    pass
                self.is_locked = False
            except (OSError, IOError):
                pass
    
    def __enter__(self):
        """Context manager entry"""
        self.acquire()
        return self
    
    def __exit__(self, type, value, traceback):
        """Context manager exit"""
        self.release()

# Load environment variables
load_dotenv()

def create_app(config_name='default'):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config[config_name])
    
    # Session configuration - Using Flask's built-in client-side sessions
    app.secret_key = os.environ.get('SESSION_SECRET', 'dev-session-secret-change-in-production')
    app.config.update(
        SESSION_COOKIE_NAME='cicd_session',
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=False,  # Set to True in production with HTTPS
        SESSION_COOKIE_SAMESITE='Lax',
        PERMANENT_SESSION_LIFETIME=timedelta(days=7)
    )
    
    # Initialize extensions
    CORS(app, origins=['*'], supports_credentials=True)
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=app.config['RATELIMIT_DEFAULT'].split(';')
    )
    
    # Initialize services
    databricks_client = DatabricksClient(model_configs=app.config['MODEL_CONFIGS'])
    deepseek_client = DeepSeekClient(model_configs=app.config['MODEL_CONFIGS'])
    file_processor = FileProcessor(
        upload_folder=app.config['UPLOAD_FOLDER'],
        allowed_extensions=app.config['ALLOWED_EXTENSIONS']
    )
    user_manager = UserManager()
    oauth_client = OAuthClient()
    email_service = EmailService()
    
    # Usage tracking file
    USAGE_FILE = 'data/usage_tracking.json'
    
    def ensure_data_directories():
        """Ensure all required data directories exist"""
        os.makedirs('data/sessions', exist_ok=True)
        os.makedirs('data/users', exist_ok=True)
        os.makedirs('static/uploads/documents', exist_ok=True)
        os.makedirs('static/uploads/licenses', exist_ok=True)
        os.makedirs('templates', exist_ok=True)
        os.makedirs('models', exist_ok=True)
        os.makedirs('utils', exist_ok=True)
        os.makedirs('data', exist_ok=True)
    
    def load_usage_data():
        """Load usage tracking data from JSON file with cross-platform file locking"""
        ensure_data_directories()
        try:
            if os.path.exists(USAGE_FILE):
                with CrossPlatformFileLock(USAGE_FILE, timeout=10) as lock:
                    with open(USAGE_FILE, 'r') as f:
                        data = json.load(f)
                    # Convert string timestamps back to datetime objects for calculation
                    for client_id, client_data in data.items():
                        if 'first_request' in client_data:
                            # Ensure first_request is a datetime object for calculations
                            first_request_str = client_data['first_request']
                            client_data['first_request'] = datetime.fromisoformat(first_request_str)
                        if 'last_request' in client_data and isinstance(client_data['last_request'], str):
                            client_data['last_request'] = datetime.fromisoformat(client_data['last_request'])
                    return data
        except (json.JSONDecodeError, FileNotFoundError, KeyError, Exception) as e:
            print(f"Error loading usage data: {e}")
        return {}

    def save_usage_data(data):
        """Save usage tracking data to JSON file with cross-platform file locking"""
        try:
            # Convert datetime objects to strings for JSON serialization
            serializable_data = {}
            for client_id, client_data in data.items():
                serializable_data[client_id] = client_data.copy()
                if 'first_request' in serializable_data[client_id]:
                    serializable_data[client_id]['first_request'] = serializable_data[client_id]['first_request'].isoformat()
                if 'last_request' in serializable_data[client_id]:
                    serializable_data[client_id]['last_request'] = serializable_data[client_id]['last_request'].isoformat()
            
            with CrossPlatformFileLock(USAGE_FILE, timeout=10) as lock:
                with open(USAGE_FILE, 'w') as f:
                    json.dump(serializable_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving usage data: {e}")
            return False

    def get_client_identifier():
        """Get unique identifier for client (IP + User-Agent)"""
        ip = request.remote_addr or 'unknown'
        user_agent = request.headers.get('User-Agent', 'unknown')[:50]
        return hashlib.sha256(f"{ip}_{user_agent}".encode()).hexdigest()

    def can_make_request(user_id=None, increment=False):
        """Check if user/client can make a request and optionally increment counter"""
        usage_data = load_usage_data()
        
        # Use user_id if authenticated, otherwise use client identifier
        if user_id:
            identifier = f"user_{user_id}"  # Prefix to avoid conflicts
            max_requests = 100  # 100 requests per RESET PERIOD for authenticated users
            is_authenticated = True
            reset_hours = 7  # 7 hours for logged-in users
        else:
            identifier = get_client_identifier()
            max_requests = 5  # 5 requests per RESET PERIOD for unauthenticated users
            is_authenticated = False
            reset_hours = 4  # 4 hours for non-logged-in users
        
        now = datetime.utcnow()
        
        if identifier not in usage_data:
            # First request - initialize with 0 count
            usage_data[identifier] = {
                'request_count': 0,
                'first_request': now,
                'last_request': now,
                'is_authenticated': is_authenticated,
                'user_id': user_id if user_id else None,
                'reset_hours': reset_hours  # Store the reset period
            }
    
        client_data = usage_data[identifier]
        
        # Ensure first_request is a datetime object
        if isinstance(client_data['first_request'], str):
            client_data['first_request'] = datetime.fromisoformat(client_data['first_request'])
        
        # Get the reset period for this client (handle legacy data)
        client_reset_hours = client_data.get('reset_hours', reset_hours)
        
        # Reset counter if it's been more than the reset period since first request
        time_since_first_request = now - client_data['first_request']
        if time_since_first_request > timedelta(hours=client_reset_hours):
            print(f"Resetting usage counter for {identifier}. Time since first request: {time_since_first_request}")
            client_data['request_count'] = 0
            client_data['first_request'] = now
            client_data['reset_hours'] = reset_hours  # Update reset hours in case it changed
        
        current_count = client_data['request_count']
        print(f"Current usage for {identifier}: {current_count}/{max_requests} (resets every {client_reset_hours} hours)")
        
        # Check if limit exceeded
        if current_count >= max_requests:
            # Calculate time until reset
            reset_time = client_data['first_request'] + timedelta(hours=client_reset_hours)
            time_until_reset = reset_time - now
            minutes_until_reset = max(0, int(time_until_reset.total_seconds() / 60))
            
            # Update last_request time but don't increment count
            client_data['last_request'] = now
            save_usage_data(usage_data)
            print(f"Usage limit exceeded for {identifier}. {minutes_until_reset} minutes until reset")
            return False, minutes_until_reset
        
        # If increment is True and request is allowed, increment counter
        if increment:
            client_data['request_count'] = current_count + 1
            client_data['last_request'] = now
            client_data['is_authenticated'] = is_authenticated
            client_data['user_id'] = user_id if user_id else None
            client_data['reset_hours'] = reset_hours  # Ensure reset hours is saved
            
            save_usage_data(usage_data)
            print(f"Request allowed and incremented for {identifier}. New count: {client_data['request_count']}/{max_requests}")
        
        return True, 0

    def track_request_check_only(user_id=None):
        """Check if request is allowed without incrementing counter"""
        return can_make_request(user_id, increment=False)

    def track_request_increment(user_id=None):
        """Increment request counter after successful generation"""
        return can_make_request(user_id, increment=True)

    def get_usage_info(user_id=None):
        """Get usage information for a user/client"""
        """Get usage information for a user/client"""
        usage_data = load_usage_data()
        
        if user_id:
            identifier = f"user_{user_id}"
            max_requests = 100
            is_authenticated = True
            reset_hours = 7  # 7 hours for logged-in users
        else:
            identifier = get_client_identifier()
            max_requests = 5
            is_authenticated = False
            reset_hours = 4  # 4 hours for non-logged-in users
        
        client_data = usage_data.get(identifier, {})
        request_count = client_data.get('request_count', 0)
        first_request = client_data.get('first_request')
        
        # Get the reset period for this client (handle legacy data)
        client_reset_hours = client_data.get('reset_hours', reset_hours)
        
        # Ensure first_request is a datetime object
        if first_request and isinstance(first_request, str):
            first_request = datetime.fromisoformat(first_request)
        
        # Apply reset logic for accurate remaining count
        now = datetime.utcnow()
        if first_request:
            time_since_first_request = now - first_request
            if time_since_first_request > timedelta(hours=client_reset_hours):
                # If reset period has passed, remaining should be max_requests
                remaining_requests = max_requests
                request_count = 0  # Reset the count for display
            else:
                remaining_requests = max(0, max_requests - request_count)
        else:
            remaining_requests = max_requests
        
        # Calculate time until reset
        reset_time = None
        minutes_until_reset = 0
        if first_request:
            reset_time = first_request + timedelta(hours=client_reset_hours)
            time_until_reset = reset_time - now
            minutes_until_reset = max(0, int(time_until_reset.total_seconds() / 60))
        
        return {
            'is_authenticated': is_authenticated,
            'request_count': request_count,
            'max_requests': max_requests,
            'remaining_requests': remaining_requests,
            'minutes_until_reset': minutes_until_reset,
            'reset_time': reset_time.isoformat() if reset_time else None,
            'reset_hours': client_reset_hours
        }

    def get_user_session_data(user_id):
        """Get user-specific session data"""
        session_data_file = f'data/users/{user_id}/session_data.json'
        try:
            if os.path.exists(session_data_file):
                with open(session_data_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            'current_conversation_id': None,
            'conversations': {},
            'user_preferences': {},
            'last_active': datetime.utcnow().isoformat()
        }
    
    def save_user_session_data(user_id, session_data):
        """Save user-specific session data"""
        try:
            session_data_file = f'data/users/{user_id}/session_data.json'
            session_data['last_active'] = datetime.utcnow().isoformat()
            with open(session_data_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving session data: {e}")
            return False
    
    def clear_user_session_data(user_id):
        """Clear user session data on logout"""
        try:
            # Don't delete the entire session file, just clear sensitive data
            session_data = get_user_session_data(user_id)
            session_data['current_conversation_id'] = None
            session_data['last_active'] = datetime.utcnow().isoformat()
            save_user_session_data(user_id, session_data)
            
            # Clear Flask session
            session.clear()
            return True
        except Exception as e:
            print(f"Error clearing session data: {e}")
            return False

    def get_client_for_model(model_name):
        """Get the appropriate client based on model provider"""
        model_config = app.config['MODEL_CONFIGS'].get(model_name, {})
        provider = model_config.get('provider', 'databricks')
        
        if provider == 'deepseek':
            return deepseek_client
        else:
            return databricks_client

    # Enhanced authentication routes
    @app.route('/api/auth/signup', methods=['POST', 'OPTIONS'])
    @limiter.limit("10 per minute")
    def signup():
        """User registration endpoint with enhanced security - FIXED VERSION"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
                
            # Check if terms are accepted
            if not data.get('accept_terms', False):
                return jsonify({
                    'success': False,
                    'error': 'You must accept the Terms of Service and Privacy Policy to create an account'
                }), 400
                
            # Validate required fields
            required_fields = ['email', 'password', 'first_name', 'last_name']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }), 400
            
            # Create SignupRequest for validation
            try:
                signup_data = SignupRequest(**data)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid data format: {str(e)}'
                }), 400
            
            # Check if user already exists
            existing_user = user_manager.get_user_by_email(signup_data.email)
            if existing_user:
                return jsonify({
                    'success': False,
                    'error': 'User with this email already exists'
                }), 400
            
            # Create user
            try:
                user = user_manager.create_user(
                    email=signup_data.email,
                    password=signup_data.password,
                    first_name=signup_data.first_name,
                    last_name=signup_data.last_name,
                    accept_terms=data.get('accept_terms', False)
                )
            except ValueError as e:
                # Password validation or other validation errors
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
            except Exception as e:
                # Unexpected errors during user creation
                print(f"Error creating user: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'error': 'Failed to create user account. Please try again.'
                }), 500
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Failed to create user. Please try again.'
                }), 500
            
            # Generate API key for the user
            api_key = generate_api_key(user['id'])
            
            # Store API key for the user
            success = user_manager.update_user_api_key(user['id'], api_key)
            if not success:
                print(f"Warning: Failed to update API key for user {user['id']}")
            
            # CRITICAL FIX: Get fresh user data after API key update
            user = user_manager.get_user_by_id(user['id'])
            
            # Generate email verification token and send verification email
            try:
                verification_token = user_manager.generate_verification_token(user['id'])
                email_service.send_email_verification(
                    user['email'], 
                    verification_token, 
                    user['first_name']
                )
            except Exception as e:
                # Log error but don't fail the signup
                print(f"Failed to send verification email: {e}")
            
            # Send welcome email
            try:
                email_service.send_welcome_email(user['email'], user['first_name'])
            except Exception as e:
                # Log error but don't fail the signup
                print(f"Failed to send welcome email: {e}")
            
            # Initialize user usage tracking with 100 requests
            try:
                usage_data = load_usage_data()
                user_identifier = f"user_{user['id']}"
                
                usage_data[user_identifier] = {
                    'request_count': 0,
                    'first_request': datetime.utcnow(),
                    'last_request': datetime.utcnow(),
                    'is_authenticated': True,
                    'user_id': user['id'],
                    'reset_hours': 7
                }
                
                save_usage_data(usage_data)
            except Exception as e:
                # Log error but don't fail the signup
                print(f"Failed to initialize usage tracking: {e}")
            
            # Get current usage info to return
            current_usage = get_usage_info(user['id'])
            
            return jsonify({
                'success': True,
                'message': 'User created successfully. Please check your email to verify your account.',
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'email_verified': user.get('email_verified', False)
                },
                'api_key': api_key,
                'current_usage': current_usage,
                'requires_verification': not user.get('email_verified', False)
            }), 201
            
        except Exception as e:
            print(f"Signup error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Registration error. Please try again.'
            }), 500

    @app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
    @limiter.limit("10 per minute")
    def login():
        """User login endpoint with enhanced security - FIXED VERSION"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
                
            # Validate required fields
            if not data.get('email') or not data.get('password'):
                return jsonify({
                    'success': False,
                    'error': 'Email and password are required'
                }), 400
            
            try:
                login_data = LoginRequest(**data)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': f'Invalid data format: {str(e)}'
                }), 400
            
            # Authenticate user
            try:
                user = user_manager.authenticate_user(login_data.email, login_data.password)
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 401
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Invalid email or password'
                }), 401
            
            # Check if email is verified
            if not user.get('email_verified', False):
                return jsonify({
                    'success': False,
                    'error': 'Please verify your email address before logging in',
                    'requires_verification': True
                }), 401
            
            # Check if account is active
            if not user.get('is_active', True):
                return jsonify({
                    'success': False,
                    'error': 'Account is deactivated. Please contact support.'
                }), 401
            
            # Generate new API key on login
            api_key = generate_api_key(user['id'])
            user_manager.update_user_api_key(user['id'], api_key)
            
            # CRITICAL FIX: Get fresh user data after API key update
            user = user_manager.get_user_by_id(user['id'])
            
            # Store user session
            session.permanent = True
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['login_time'] = datetime.utcnow().isoformat()
            session['csrf_token'] = generate_csrf_token()
            
            # Update last login
            if hasattr(user_manager, 'update_last_login'):
                user_manager.update_last_login(user['id'])
                # Get fresh user data after login time update
                user = user_manager.get_user_by_id(user['id'])
            
            # Load existing usage data
            usage_data = load_usage_data()
            user_identifier = f"user_{user['id']}"
            
            if user_identifier not in usage_data:
                usage_data[user_identifier] = {
                    'request_count': 0,
                    'first_request': datetime.utcnow(),
                    'last_request': datetime.utcnow(),
                    'is_authenticated': True,
                    'user_id': user['id'],
                    'reset_hours': 7
                }
            else:
                usage_data[user_identifier]['is_authenticated'] = True
                usage_data[user_identifier]['user_id'] = user['id']
                now = datetime.utcnow()
                first_request = usage_data[user_identifier]['first_request']
                if isinstance(first_request, str):
                    first_request = datetime.fromisoformat(first_request)
                
                time_since_first_request = now - first_request
                if time_since_first_request > timedelta(hours=7):
                    usage_data[user_identifier]['request_count'] = 0
                    usage_data[user_identifier]['first_request'] = now
            
            save_usage_data(usage_data)
            
            # Get current usage info to return
            current_usage = get_usage_info(user['id'])
            
            # Load user session data
            user_session_data = get_user_session_data(user['id'])
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'email_verified': user.get('email_verified', False)
                },
                'api_key': api_key,
                'session_data': user_session_data,
                'current_usage': current_usage,
                'csrf_token': session['csrf_token']
            }), 200
            
        except Exception as e:
            print(f"Login error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Login error. Please try again.'
            }), 500

    @app.route('/api/auth/verify-email', methods=['POST', 'OPTIONS'])
    @limiter.limit("5 per minute")
    def request_verification_email():
        """Request email verification"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            data = request.get_json()
            if not data or not data.get('email'):
                return jsonify({
                    'success': False,
                    'error': 'Email address is required'
                }), 400
                
            user = user_manager.get_user_by_email(data['email'])
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
                
            if user.get('email_verified', False):
                return jsonify({
                    'success': False,
                    'error': 'Email is already verified'
                }), 400
                
            # Generate new verification token
            verification_token = user_manager.generate_verification_token(user['id'])
            success = email_service.send_email_verification(
                user['email'], 
                verification_token, 
                user['first_name']
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Verification email sent successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to send verification email'
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error sending verification email: {str(e)}'
            }), 500

    @app.route('/api/auth/verify-email/<token>', methods=['GET', 'POST', 'OPTIONS'])
    def verify_email(token):
        """Verify email address using token"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            success = user_manager.verify_email(token)
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Email verified successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Invalid or expired verification token'
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Verification error: {str(e)}'
            }), 500

    @app.route('/api/auth/forgot-password', methods=['POST', 'OPTIONS'])
    @limiter.limit("5 per minute")
    def forgot_password():
        """Request password reset"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            data = request.get_json()
            if not data or not data.get('email'):
                return jsonify({
                    'success': False,
                    'error': 'Email address is required'
                }), 400
                
            user = user_manager.get_user_by_email(data['email'])
            if not user:
                # Don't reveal whether email exists for security
                return jsonify({
                    'success': True,
                    'message': 'If the email exists, a password reset link has been sent'
                }), 200
                
            # Check if user uses OAuth (no password)
            if user.get('oauth_provider') and not user.get('password_hash'):
                return jsonify({
                    'success': False,
                    'error': f'This account uses {user["oauth_provider"].title()} authentication. Please use OAuth login.'
                }), 400
                
            # Generate password reset token
            reset_token = user_manager.generate_password_reset_token(user['email'])
            if reset_token:
                success = email_service.send_password_reset_email(
                    user['email'], 
                    reset_token, 
                    user['first_name']
                )
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': 'Password reset email sent successfully'
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to send password reset email'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to generate reset token'
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Password reset request error: {str(e)}'
            }), 500

    @app.route('/api/auth/reset-password', methods=['POST', 'OPTIONS'])
    @limiter.limit("5 per minute")
    def reset_password():
        """Reset password using token - FIXED VERSION"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            data = request.get_json()
            if not data or not data.get('token') or not data.get('new_password'):
                return jsonify({
                    'success': False,
                    'error': 'Token and new password are required'
                }), 400
            
            try:
                success = user_manager.reset_password(data['token'], data['new_password'])
                if success:
                    return jsonify({
                        'success': True,
                        'message': 'Password reset successfully'
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid or expired reset token'
                    }), 400
            except ValueError as e:
                # Password validation error
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
                    
        except Exception as e:
            print(f"Password reset error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Password reset error. Please try again.'
            }), 500

    @app.route('/api/auth/oauth/<provider>', methods=['GET', 'OPTIONS'])
    def oauth_init(provider):
        """Initialize OAuth flow"""
        if request.method == 'OPTIONS':
            return '', 200
            
        if provider not in ['google', 'github']:
            return jsonify({
                'success': False,
                'error': 'Unsupported OAuth provider'
            }), 400
            
        # Generate state parameter for CSRF protection
        state = generate_csrf_token()
        session['oauth_state'] = state
        session['oauth_provider'] = provider
        
        redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
        auth_url = oauth_client.get_auth_url(provider, redirect_uri, state)
        
        if auth_url:
            return jsonify({
                'success': True,
                'auth_url': auth_url
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'OAuth configuration error'
            }), 500

    @app.route('/api/auth/oauth/<provider>/callback', methods=['GET', 'OPTIONS'])
    def oauth_callback(provider):
        """Handle OAuth callback - FIXED VERSION"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            # Verify state parameter
            state = request.args.get('state')
            stored_state = session.get('oauth_state')
            stored_provider = session.get('oauth_provider')
            
            if not oauth_client.validate_state(state, stored_state) or stored_provider != provider:
                return jsonify({
                    'success': False,
                    'error': 'Invalid OAuth state'
                }), 400
                
            # Clear state from session
            session.pop('oauth_state', None)
            session.pop('oauth_provider', None)
            
            code = request.args.get('code')
            if not code:
                return jsonify({
                    'success': False,
                    'error': 'Authorization code not provided'
                }), 400
                
            redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
            token_data = oauth_client.exchange_code_for_token(provider, code, redirect_uri)
            
            if not token_data or 'access_token' not in token_data:
                return jsonify({
                    'success': False,
                    'error': 'Failed to obtain access token'
                }), 400
                
            # Get user info from provider
            user_info = oauth_client.get_user_info(provider, token_data['access_token'])
            if not user_info:
                return jsonify({
                    'success': False,
                    'error': 'Failed to get user information'
                }), 400
                
            # Check if user already exists by OAuth ID
            user = user_manager.get_user_by_oauth(provider, user_info['id'])
            if not user:
                # Check if user exists by email
                user = user_manager.get_user_by_email(user_info['email'])
                if user:
                    # CRITICAL FIX: Link OAuth to existing account using helper method
                    success = user_manager.link_oauth_to_user(user['id'], provider, user_info['id'])
                    if not success:
                        return jsonify({
                            'success': False,
                            'error': 'Failed to link OAuth to existing account'
                        }), 500
                    # Get fresh user data after modification
                    user = user_manager.get_user_by_id(user['id'])
                else:
                    # Create new user with OAuth
                    try:
                        user = user_manager.create_user(
                            email=user_info['email'],
                            password=str(uuid.uuid4()),  # Random password for OAuth users
                            first_name=user_info['first_name'],
                            last_name=user_info['last_name'],
                            accept_terms=True,  # OAuth users accept terms by using the service
                            oauth_provider=provider,
                            oauth_id=user_info['id']
                        )
                        
                        if not user:
                            return jsonify({
                                'success': False,
                                'error': 'Failed to create user account'
                            }), 500
                            
                        # Send welcome email
                        try:
                            email_service.send_welcome_email(user['email'], user['first_name'])
                        except Exception as e:
                            # Log error but don't fail the signup
                            print(f"Failed to send welcome email: {e}")
                            
                    except ValueError as e:
                        return jsonify({
                            'success': False,
                            'error': str(e)
                        }), 400
            
            # Generate API key
            api_key = generate_api_key(user['id'])
            user_manager.update_user_api_key(user['id'], api_key)
            
            # CRITICAL FIX: Get fresh user data after API key update
            user = user_manager.get_user_by_id(user['id'])
            
            # Store user session
            session.permanent = True
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['login_time'] = datetime.utcnow().isoformat()
            session['csrf_token'] = generate_csrf_token()
            
            # Update last login
            if hasattr(user_manager, 'update_last_login'):
                user_manager.update_last_login(user['id'])
            
            # Initialize usage tracking if needed
            usage_data = load_usage_data()
            user_identifier = f"user_{user['id']}"
            
            if user_identifier not in usage_data:
                usage_data[user_identifier] = {
                    'request_count': 0,
                    'first_request': datetime.utcnow(),
                    'last_request': datetime.utcnow(),
                    'is_authenticated': True,
                    'user_id': user['id'],
                    'reset_hours': 7
                }
                save_usage_data(usage_data)
            
            # Get current usage info
            current_usage = get_usage_info(user['id'])
            
            # Load user session data
            user_session_data = get_user_session_data(user['id'])
            
            return jsonify({
                'success': True,
                'message': 'OAuth login successful',
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'email_verified': user.get('email_verified', True)
                },
                'api_key': api_key,
                'session_data': user_session_data,
                'current_usage': current_usage,
                'csrf_token': session['csrf_token']
            }), 200
            
        except Exception as e:
            print(f"OAuth callback error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': f'OAuth error: {str(e)}'
            }), 500

    @app.route('/api/auth/change-password', methods=['POST', 'OPTIONS'])
    @api_key_required
    @limiter.limit("5 per minute")
    def change_password():
        """Change user password - FIXED VERSION"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401
                
            data = request.get_json()
            if not data or not data.get('current_password') or not data.get('new_password'):
                return jsonify({
                    'success': False,
                    'error': 'Current password and new password are required'
                }), 400
                
            user = user_manager.get_user_by_id(user_id)
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
            
            # Check if user uses OAuth (no password)
            if user.get('oauth_provider') and not user.get('password_hash'):
                return jsonify({
                    'success': False,
                    'error': 'Cannot change password for OAuth accounts'
                }), 400
                
            # Verify current password
            if not user_manager.verify_password(data['current_password'], user['password_hash']):
                return jsonify({
                    'success': False,
                    'error': 'Current password is incorrect'
                }), 400
            
            # Check if new password is same as current
            if user_manager.verify_password(data['new_password'], user['password_hash']):
                return jsonify({
                    'success': False,
                    'error': 'New password must be different from current password'
                }), 400
                
            # Update password
            try:
                success = user_manager.update_user_password(user_id, data['new_password'])
                if success:
                    return jsonify({
                        'success': True,
                        'message': 'Password changed successfully'
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Failed to change password'
                    }), 500
            except ValueError as e:
                # Password validation error
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
                    
        except Exception as e:
            print(f"Password change error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Password change error. Please try again.'
            }), 500

    @app.route('/api/auth/profile', methods=['GET', 'OPTIONS'])
    @api_key_required
    def get_profile():
        """Get user profile"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401
                
            user = user_manager.get_user_by_id(user_id)
            if user:
                return jsonify({
                    'success': True,
                    'profile': {
                        'id': user['id'],
                        'email': user['email'],
                        'first_name': user['first_name'],
                        'last_name': user['last_name'],
                        'email_verified': user.get('email_verified', False),
                        'created_at': user['created_at'],
                        'last_login': user.get('last_login'),
                        'oauth_provider': user.get('oauth_provider')
                    }
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error retrieving profile: {str(e)}'
            }), 500

    @app.route('/api/auth/profile', methods=['PUT', 'OPTIONS'])
    @api_key_required
    def update_profile():
        """Update user profile - FIXED VERSION"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401
                
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
                
            user = user_manager.get_user_by_id(user_id)
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
                
            # Update allowed fields
            update_fields = ['first_name', 'last_name']
            updated = False
            
            for field in update_fields:
                if field in data and data[field] != user.get(field):
                    # Validate field value
                    if not data[field] or not isinstance(data[field], str):
                        return jsonify({
                            'success': False,
                            'error': f'Invalid value for {field}'
                        }), 400
                    
                    user[field] = data[field].strip()
                    updated = True
                        
            if updated:
                user['updated_at'] = datetime.utcnow().isoformat()
                # CRITICAL FIX: Save after modification
                if not user_manager._save_users():
                    return jsonify({
                        'success': False,
                        'error': 'Failed to update profile'
                    }), 500
                
                # Get fresh user data
                user = user_manager.get_user_by_id(user_id)
                
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully' if updated else 'No changes made',
                'profile': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'email_verified': user.get('email_verified', False),
                    'created_at': user['created_at'],
                    'last_login': user.get('last_login'),
                    'oauth_provider': user.get('oauth_provider')
                }
            }), 200
                    
        except Exception as e:
            print(f"Profile update error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'success': False,
                'error': 'Error updating profile. Please try again.'
            }), 500

    @app.route('/api/auth/logout', methods=['POST', 'OPTIONS'])
    def logout():
        """User logout endpoint"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = session.get('user_id')
            if user_id:
                # Clear user session data
                clear_user_session_data(user_id)
            
            # Clear Flask session
            session.clear()
            
            return jsonify({
                'success': True,
                'message': 'Logout successful',
                'clear_storage': True
            }), 200
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Logout error: {str(e)}'
            }), 500

    @app.route('/api/auth/me', methods=['GET', 'OPTIONS'])
    @api_key_required
    def get_current_user():
        """Get current user information"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401
                
            user = user_manager.get_user_by_id(user_id)
            if user:
                return jsonify({
                    'success': True,
                    'user': {
                        'id': user['id'],
                        'email': user['email'],
                        'first_name': user['first_name'],
                        'last_name': user['last_name'],
                        'created_at': user['created_at']
                    }
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 404
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error retrieving user: {str(e)}'
            }), 500

    @app.route('/api/auth/session-data', methods=['GET', 'OPTIONS'])
    @api_key_required
    def get_session_data():
        """Get user session data"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401
                
            session_data = get_user_session_data(user_id)
            
            return jsonify({
                'success': True,
                'session_data': session_data
            }), 200
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"Error retrieving session data: {str(e)}"
            }), 500

    @app.route('/api/auth/session-data', methods=['POST', 'OPTIONS'])
    @api_key_required
    def save_session_data():
        """Save user session data"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401
                
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
                
            success = save_user_session_data(user_id, data)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Session data saved successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to save session data'
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"Error saving session data: {str(e)}"
            }), 500

    @app.route('/api/auth/usage', methods=['GET', 'OPTIONS'])
    def get_usage_info_route():
        """Get current usage information for the client"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            # Check for API key first (authenticated users)
            api_key = request.headers.get('X-API-Key')
            user_id = None
            
            if api_key:
                payload = verify_api_key(api_key)
                if payload:
                    user_id = payload['user_id']
            
            # If no API key, check session (web login)
            if not user_id:
                user_id = session.get('user_id')
            
            usage_info = get_usage_info(user_id)
            
            # Debug logging
            identifier = f"user_{user_id}" if user_id else get_client_identifier()
            print(f"Usage info for {identifier}: {usage_info['request_count']}/{usage_info['max_requests']} requests, {usage_info['remaining_requests']} remaining, reset in {usage_info['minutes_until_reset']} minutes")
            
            return jsonify({
                'success': True,
                'usage': usage_info
            }), 200
            
        except Exception as e:
            print(f"Error retrieving usage info: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Error retrieving usage info: {str(e)}'
            }), 500

    # Updated generate endpoint with proper increment timing
    @app.route('/api/generate', methods=['POST', 'OPTIONS'])
    @limiter.limit("20 per minute")
    def generate_code():
        """Generate CI/CD code using AI models - increment ONLY after success"""
        if request.method == 'OPTIONS':
            return '', 200
            
        start_time = time.time()
        
        try:
            # Identify user - check API key first, then session
            user_id = None
            api_key = request.headers.get('X-API-Key')
            
            if api_key:
                payload = verify_api_key(api_key)
                if payload:
                    user_id = payload['user_id']
            
            # If no API key, check session
            if not user_id:
                user_id = session.get('user_id')
            
            # Check usage limits WITHOUT incrementing first
            allowed, minutes_until_reset = track_request_check_only(user_id)
            
            if not allowed:
                print(f"Usage limit exceeded for user {user_id}. Minutes until reset: {minutes_until_reset}")
                return jsonify({
                    'success': False,
                    'error': f'Usage limit exceeded. Please sign in to continue or wait {minutes_until_reset} minutes.',
                    'error_code': 'USAGE_LIMIT_EXCEEDED',
                    'minutes_until_reset': minutes_until_reset,
                    'requires_auth': True
                }), 429
            
            # Validate request data
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
                
            # Get conversation history if provided
            conversation_history = data.get('conversation_history', [])
            
            request_data = CodeGenerationRequest(**data)
            
            # Get the appropriate client based on model
            client = get_client_for_model(request_data.model.value)
            
            # Generate code using the appropriate client
            result = client.generate_code(
                prompt=request_data.prompt,
                model=request_data.model.value,
                action=request_data.action.value,
                conversation_history=conversation_history
            )
            
            # ONLY increment usage counter AFTER successful generation
            if result['success']:
                # Increment the counter
                track_request_increment(user_id)
                
                # Get updated usage info after successful generation
                updated_usage_info = get_usage_info(user_id)
                
                response_data = CodeGenerationResponse(
                    success=True,
                    content=result['content'],
                    model_used=result['model_used'],
                    processing_time=result['processing_time'],
                    tokens_used=result.get('tokens_used'),
                    needs_clarification=result.get('needs_clarification', False)
                )
                
                # Convert to dict and add updated usage
                response_dict = response_data.dict()
                response_dict['updated_usage'] = updated_usage_info
                
                # Debug logging
                identifier = f"user_{user_id}" if user_id else get_client_identifier()
                print(f"Request successful for {identifier}. Usage: {updated_usage_info['request_count']}/{updated_usage_info['max_requests']}, {updated_usage_info['remaining_requests']} remaining")
                
                return jsonify(response_dict), 200
            else:
                response_data = CodeGenerationResponse(
                    success=False,
                    content="",
                    model_used=request_data.model.value,
                    processing_time=result['processing_time'],
                    error=result['error']
                )
                return jsonify(response_data.dict()), 500
                
        except ValueError as e:
            # Handle validation errors
            return jsonify({
                'success': False,
                'error': f"Validation error: {str(e)}",
                'processing_time': time.time() - start_time
            }), 400
        except Exception as e:
            processing_time = time.time() - start_time
            return jsonify({
                'success': False,
                'error': f"Request processing error: {str(e)}",
                'processing_time': processing_time
            }), 500

    # User-specific conversation management endpoints
    @app.route('/api/conversations', methods=['GET', 'OPTIONS'])
    @api_key_required
    def get_user_conversations():
        """Get all conversations for the current user"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            conversations = user_manager.get_user_conversations(user_id)
            return jsonify({
                'success': True,
                'conversations': conversations
            }), 200
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"Error retrieving conversations: {str(e)}"
            }), 500

    @app.route('/api/conversations', methods=['POST', 'OPTIONS'])
    @api_key_required
    def save_user_conversations():
        """Save conversations for the current user"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            data = request.get_json()
            
            if not data or 'conversations' not in data:
                return jsonify({
                    'success': False,
                    'error': 'No conversations data provided'
                }), 400
                
            success = user_manager.save_user_conversations(user_id, data['conversations'])
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'Conversations saved successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to save conversations'
                }), 500
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"Error saving conversations: {str(e)}"
            }), 500

    # Static routes
    @app.route('/documentation')
    def documentation():
        """Serve the documentation library page"""
        return send_from_directory('templates', 'documentation.html')
    
    @app.route('/login')
    def login_page():
        """Serve the login page"""
        return send_from_directory('templates', 'login.html')
    
    @app.route('/signup')
    def signup_page():
        """Serve the signup page"""
        return send_from_directory('templates', 'signup.html')
    
    @app.route('/support')
    def support():
        """Serve the support page"""
        return send_from_directory('templates', 'support.html')
    
    @app.route('/')
    def serve_frontend():
        """Serve the frontend application"""
        return send_from_directory('templates', 'index.html')
    
    @app.route('/static/<path:path>')
    def serve_static(path):
        """Serve static files"""
        static_dir = os.path.join(app.root_path, 'static')
        return send_from_directory(static_dir, path)
    
    @app.route('/static/uploads/<file_type>/<path:path>')
    def serve_uploads(file_type, path):
        """Serve uploaded files with user-specific paths"""
        uploads_dir = os.path.join(app.root_path, 'static', 'uploads', file_type)
        return send_from_directory(uploads_dir, path)
    
    # Health check endpoint with multi-provider support
    @app.route('/api/health', methods=['GET', 'OPTIONS'])
    def health_check():
        """Health check endpoint"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            # Check both clients
            databricks_availability = databricks_client.check_model_availability()
            deepseek_availability = deepseek_client.check_model_availability()
            
            # Combine availability
            all_models_available = list(databricks_availability.keys()) + list(deepseek_availability.keys())
            
            response = HealthResponse(
                status="healthy",
                timestamp=datetime.utcnow().isoformat(),
                version="1.0.0",
                models_available=all_models_available
            )
            
            return jsonify(response.dict())
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    # File upload endpoint - FIXED VERSION
    @app.route('/api/upload', methods=['POST', 'OPTIONS'])
    @api_key_required
    @limiter.limit("10 per minute")
    def upload_file():
        """Upload CI/CD documents and licenses"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            if 'file' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No file provided'
                }), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected'
                }), 400
                
            # Get user ID from the request (set by api_key_required decorator)
            user_id = getattr(request, 'user_id', None)
            result = file_processor.process_uploaded_file(file, user_id)
            
            if result['success']:
                response_data = DocumentUploadResponse(
                    success=True,
                    filename=result['original_filename'],
                    file_url=result['file_url'],
                    file_size=result['file_size'],
                    message="File uploaded successfully"
                )
                return jsonify(response_data.dict()), 200
            else:
                return jsonify({
                    'success': False,
                    'error': result['error']
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"Upload error: {str(e)}"
            }), 500
    
    @app.route('/api/files', methods=['GET', 'OPTIONS'])
    @api_key_required
    def get_files():
        """Get list of uploaded files for the current user"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            files = file_processor.get_uploaded_files(user_id)
            return jsonify({
                'success': True,
                'files': files
            }), 200
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"Error retrieving files: {str(e)}"
            }), 500
    
    @app.route('/api/files/<file_type>/<filename>', methods=['DELETE', 'OPTIONS'])
    @api_key_required
    def delete_file(file_type, filename):
        """Delete uploaded file"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            result = file_processor.delete_file(filename, file_type, user_id)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message']
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': result['error']
                }), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"Error deleting file: {str(e)}"
            }), 500

    @app.route('/api/files/<file_type>/<filename>/download', methods=['GET', 'OPTIONS'])
    @api_key_required
    def download_file(file_type, filename):
        """Download uploaded file"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            if file_type not in ['documents', 'licenses']:
                return jsonify({
                    'success': False,
                    'error': 'Invalid file type'
                }), 400
            
            user_id = getattr(request, 'user_id', None)
            if user_id:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_type, user_id, sanitize_filename(filename))
            else:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_type, sanitize_filename(filename))
            
            if not os.path.exists(file_path):
                return jsonify({
                    'success': False,
                    'error': 'File not found'
                }), 404
            
            return send_file(file_path, as_attachment=True)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"File download error: {str(e)}"
            }), 500
    
    # API key management
    @app.route('/api/generate-api-key', methods=['POST', 'OPTIONS'])
    @api_key_required
    def generate_new_api_key():
        """Generate new API key for authenticated users"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            user_id = getattr(request, 'user_id', None)
            if not user_id:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401
            
            api_key = generate_api_key(user_id)
            
            # Update user's API key
            user_manager.update_user_api_key(user_id, api_key)
            
            return jsonify({
                'success': True,
                'api_key': api_key,
                'user_id': user_id,
                'message': 'Keep this API key secure. It will not be shown again.'
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"Error generating API key: {str(e)}"
            }), 500

    @app.route('/api/validate-api-key', methods=['POST', 'OPTIONS'])
    def validate_api_key():
        """Validate existing API key"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            api_key = request.headers.get('X-API-Key')
            if not api_key:
                return jsonify({
                    'success': False,
                    'valid': False,
                    'error': 'No API key provided'
                }), 401
            
            # Verify the API key
            payload = verify_api_key(api_key)
            if payload:
                return jsonify({
                    'success': True,
                    'valid': True,
                    'user_id': payload['user_id']
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'valid': False,
                    'error': 'Invalid or expired API key'
                }), 200
                
        except Exception as e:
            return jsonify({
                'success': False,
                'valid': False,
                'error': f"Validation error: {str(e)}"
            }), 500
    
    # Models endpoint with multi-provider support
    @app.route('/api/models', methods=['GET', 'OPTIONS'])
    @api_key_required
    def get_models():
        """Get available models and their status"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            databricks_availability = databricks_client.check_model_availability()
            deepseek_availability = deepseek_client.check_model_availability()
            
            # Combine availability
            all_availability = {**databricks_availability, **deepseek_availability}
            
            models_info = []
            
            for model_name, is_available in all_availability.items():
                model_config = app.config['MODEL_CONFIGS'].get(model_name, {})
                models_info.append({
                    'id': model_name,
                    'name': model_config.get('name', model_name),
                    'available': is_available,
                    'provider': model_config.get('provider', 'databricks'),
                    'max_tokens': model_config.get('max_tokens', 4096),
                    'temperature': model_config.get('temperature', 0.1)
                })
            
            return jsonify({
                'success': True,
                'models': models_info
            }), 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f"Error retrieving model information: {str(e)}"
            }), 500
    
    # Error handlers
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'success': False,
            'error': 'Rate limit exceeded. Please try again later.'
        }), 429
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'success': False,
            'error': 'File too large. Maximum size is 10MB.'
        }), 413
    
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'success': False,
            'error': 'Resource not found.'
        }), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error. Please try again later.'
        }), 500
    
    return app

if __name__ == '__main__':
    # Create app
    app = create_app('development' if os.environ.get('DEBUG', 'False').lower() == 'true' else 'production')
    
    # Get configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Flask app on port {port}...")
    print(f"Debug mode: {debug}")
    print(f"Session storage: data/sessions/")
    print(f"User data storage: data/users/")
    print(f"Access the application at: http://localhost:{port}")
    print(f"Documentation page at: http://localhost:{port}/documentation")
    print(f"Available models:")
    print(f"  - Databricks: Llama 3 70B, Llama 4 Maverick, Llama 3.1 405B")
    print(f"  - DeepSeek: DeepSeek Coder, DeepSeek Chat")
    print(f"Authentication features:")
    print(f"  - Email/Password with bcrypt hashing")
    print(f"  - OAuth 2.0 (Google, GitHub)")
    print(f"  - Password recovery with secure tokens")
    print(f"  - Email verification")
    print(f"  - Account lockout protection")
    print(f"  - Rate limiting on auth endpoints")
    print(f"Usage limits:")
    print(f"  - Authenticated users: 100 generations per hour")
    print(f"  - Anonymous users: 5 generations per hour")
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=debug)