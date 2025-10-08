import os
import jwt
import bcrypt
import secrets
import hashlib
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session
from typing import Optional, Dict, Any
import hmac
import re

def generate_api_key(user_id: str) -> str:
    """Generate a secure API key using JWT"""
    secret = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=365),
        'iat': datetime.utcnow(),
        'type': 'api_key',
        'iss': 'cicd-helper',
        'jti': secrets.token_urlsafe(16)  # Unique JWT ID
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def verify_api_key(api_key: str) -> Optional[dict]:
    """Verify API key and return payload if valid"""
    try:
        secret = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')
        payload = jwt.decode(api_key, secret, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

def generate_csrf_token() -> str:
    """Generate CSRF token and store in session"""
    token = secrets.token_urlsafe(32)
    session['csrf_token'] = token
    session['csrf_token_created'] = datetime.utcnow().isoformat()
    return token

def verify_csrf_token(token: str) -> bool:
    """Verify CSRF token against session"""
    if 'csrf_token' not in session:
        return False
    
    # Check if token is too old (optional: you can set an expiration)
    token_created = session.get('csrf_token_created')
    if token_created:
        created_time = datetime.fromisoformat(token_created)
        if datetime.utcnow() - created_time > timedelta(hours=24):
            return False
    
    return secrets.compare_digest(session['csrf_token'], token)

def generate_secure_token(length=32) -> str:
    """Generate a secure random token for various purposes"""
    return secrets.token_urlsafe(length)

def hash_data(data: str) -> str:
    """Hash data for security using SHA-256"""
    return hashlib.sha256(data.encode()).hexdigest()

def hash_password(password: str) -> str:
    """Hash password using bcrypt with salt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash"""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def validate_password_strength(password: str) -> Dict[str, Any]:
    """
    Validate password strength with comprehensive rules
    
    Returns:
        Dict with 'valid' boolean and 'message' string
    """
    if len(password) < 8:
        return {
            'valid': False, 
            'message': 'Password must be at least 8 characters long',
            'score': 0
        }
    
    # Check for common passwords (basic check)
    common_passwords = [
        'password', '123456', '12345678', '123456789', '12345',
        'qwerty', 'abc123', 'password1', '1234567', 'admin'
    ]
    
    if password.lower() in common_passwords:
        return {
            'valid': False,
            'message': 'Password is too common. Please choose a more unique password.',
            'score': 0
        }
    
    # Calculate password strength score
    score = 0
    messages = []
    
    # Length check
    if len(password) >= 12:
        score += 2
    elif len(password) >= 8:
        score += 1
    
    # Character variety checks
    if any(c.isupper() for c in password):
        score += 1
    else:
        messages.append('uppercase letter')
    
    if any(c.islower() for c in password):
        score += 1
    else:
        messages.append('lowercase letter')
    
    if any(c.isdigit() for c in password):
        score += 1
    else:
        messages.append('number')
    
    special_chars = '!@#$%^&*(),.?":{}|<>'
    if any(c in special_chars for c in password):
        score += 1
    else:
        messages.append('special character')
    
    # Determine strength level
    if score >= 5:
        strength = 'strong'
        valid = True
    elif score >= 3:
        strength = 'medium'
        valid = True
    else:
        strength = 'weak'
        valid = False
    
    if messages:
        message = f'Password should include at least one {", ".join(messages)}'
    else:
        message = f'Password strength: {strength}'
    
    return {
        'valid': valid,
        'message': message,
        'score': score,
        'strength': strength
    }

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks"""
    import re
    # Remove any path components
    filename = os.path.basename(filename)
    # Remove non-alphanumeric characters (except dots, hyphens, underscores)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    # Limit filename length
    filename = filename[:255]
    return filename

def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """Validate file extension against allowed list"""
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    
    # Additional security: check for double extensions
    if '.' in ext:
        return False
    
    return ext in allowed_extensions

def validate_email(email: str) -> bool:
    """Validate email format"""
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None

def generate_secure_nonce(length=16) -> str:
    """Generate a secure nonce for CSP or other security headers"""
    return secrets.token_hex(length)

def rate_limit_key():
    """Key function for rate limiting based on user ID or IP"""
    # Try to get user ID from request
    user_id = getattr(request, 'user_id', None)
    if user_id:
        return f"user_{user_id}"
    
    # Fall back to IP address
    return get_remote_address()

def get_remote_address():
    """Get client IP address, handling proxies"""
    if request.headers.get('X-Forwarded-For'):
        # In case of multiple proxies, take the first one
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr or '127.0.0.1'

def generate_hmac_signature(data: str, secret: str) -> str:
    """Generate HMAC signature for data verification"""
    return hmac.new(
        secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def verify_hmac_signature(data: str, signature: str, secret: str) -> bool:
    """Verify HMAC signature"""
    expected_signature = generate_hmac_signature(data, secret)
    return hmac.compare_digest(expected_signature, signature)

def sanitize_input(input_string: str, max_length=1000) -> str:
    """Sanitize user input to prevent XSS and injection attacks"""
    if not input_string:
        return ""
    
    # Truncate to maximum length
    input_string = input_string[:max_length]
    
    # Remove or encode potentially dangerous characters
    sanitized = input_string.replace('<', '&lt;').replace('>', '&gt;')
    sanitized = sanitized.replace('"', '&quot;').replace("'", '&#x27;')
    sanitized = sanitized.replace('&', '&amp;')
    
    return sanitized

def validate_url(url: str) -> bool:
    """Validate URL format for security"""
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        
        # Basic URL validation
        if not all([result.scheme, result.netloc]):
            return False
        
        # Only allow HTTP and HTTPS
        if result.scheme not in ['http', 'https']:
            return False
        
        # Check for suspicious characters
        if 'javascript:' in url.lower() or 'data:' in url.lower():
            return False
            
        return True
    except Exception:
        return False

# Decorators for route protection

def api_key_required(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key required. Please generate an API key first.'
            }), 401
        
        payload = verify_api_key(api_key)
        if not payload:
            return jsonify({
                'success': False, 
                'error': 'Invalid or expired API key. Please generate a new one.'
            }), 401
            
        # Store user ID in request for easy access
        request.user_id = payload['user_id']
        return f(*args, **kwargs)
    return decorated_function

def csrf_protection(f):
    """Decorator for CSRF protection on state-changing requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            if not csrf_token or not verify_csrf_token(csrf_token):
                return jsonify({
                    'success': False,
                    'error': 'Invalid CSRF token'
                }), 403
        return f(*args, **kwargs)
    return decorated_function

def rate_limited(max_per_minute=10):
    """Decorator for custom rate limiting"""
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # This would typically be implemented with Flask-Limiter
            # For now, we'll use a simple approach
            limiter = Limiter(
                key_func=get_remote_address,
                default_limits=[f"{max_per_minute} per minute"]
            )
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_terms_accepted(f):
    """Decorator to require terms of service acceptance"""
    @wraps(f)
    @api_key_required
    def decorated_function(*args, **kwargs):
        # This would check if the user has accepted terms
        # Implementation depends on your user model
        user_id = getattr(request, 'user_id')
        
        # Example check - you'll need to implement getUserTermsStatus
        # if not getUserTermsStatus(user_id):
        #     return jsonify({
        #         'success': False,
        #         'error': 'Terms of service must be accepted to use this feature'
        #     }), 403
        
        return f(*args, **kwargs)
    return decorated_function

def require_email_verified(f):
    """Decorator to require email verification"""
    @wraps(f)
    @api_key_required
    def decorated_function(*args, **kwargs):
        # This would check if the user's email is verified
        # Implementation depends on your user model
        user_id = getattr(request, 'user_id')
        
        # Example check - you'll need to implement getUserEmailStatus
        # if not getUserEmailStatus(user_id):
        #     return jsonify({
        #         'success': False,
        #         'error': 'Email address must be verified to use this feature'
        #     }), 403
        
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    @api_key_required
    def decorated_function(*args, **kwargs):
        user_id = getattr(request, 'user_id')
        
        # Check if user has admin role
        # Implementation depends on your user model
        # if not isUserAdmin(user_id):
        #     return jsonify({
        #         'success': False,
        #         'error': 'Admin privileges required'
        #     }), 403
        
        return f(*args, **kwargs)
    return decorated_function

# Security headers middleware (conceptual - would be used in app configuration)

def security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy (adjust based on your needs)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers['Content-Security-Policy'] = csp
    
    return response

# Password reset token functions

def generate_password_reset_token(user_id: str, email: str) -> str:
    """Generate a secure password reset token"""
    secret = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=1),  # 1 hour expiration
        'iat': datetime.utcnow(),
        'type': 'password_reset',
        'jti': secrets.token_urlsafe(16)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def verify_password_reset_token(token: str) -> Optional[dict]:
    """Verify password reset token"""
    try:
        secret = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        
        # Check token type
        if payload.get('type') != 'password_reset':
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

# Email verification token functions

def generate_email_verification_token(user_id: str, email: str) -> str:
    """Generate a secure email verification token"""
    secret = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')
    payload = {
        'user_id': user_id,
        'email': email,
        'exp': datetime.utcnow() + timedelta(days=1),  # 24 hours expiration
        'iat': datetime.utcnow(),
        'type': 'email_verification',
        'jti': secrets.token_urlsafe(16)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def verify_email_verification_token(token: str) -> Optional[dict]:
    """Verify email verification token"""
    try:
        secret = os.environ.get('SECRET_KEY', 'default-secret-key-change-in-production')
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        
        # Check token type
        if payload.get('type') != 'email_verification':
            return None
            
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

# Session security

def validate_session_security():
    """Validate session security measures"""
    # Check if session has necessary security attributes
    required_attrs = ['user_id', 'csrf_token']
    for attr in required_attrs:
        if attr not in session:
            return False
    
    # Check session age (optional)
    login_time = session.get('login_time')
    if login_time:
        login_dt = datetime.fromisoformat(login_time)
        if datetime.utcnow() - login_dt > timedelta(days=7):  # 7 days max session
            return False
    
    return True

def rotate_session():
    """Rotate session ID to prevent session fixation"""
    # This would typically clear the session and create a new one
    # In Flask, you can use session.regenerate()
    pass

# Input validation helpers

def validate_integer(value, min_val=None, max_val=None):
    """Validate and sanitize integer input"""
    try:
        num = int(value)
        if min_val is not None and num < min_val:
            return None
        if max_val is not None and num > max_val:
            return None
        return num
    except (ValueError, TypeError):
        return None

def validate_string(value, max_length=255, allowed_chars=None):
    """Validate and sanitize string input"""
    if not value or not isinstance(value, str):
        return None
    
    value = value.strip()
    if len(value) > max_length:
        return None
    
    if allowed_chars:
        if not all(c in allowed_chars for c in value):
            return None
    
    return sanitize_input(value)

# Audit logging helper

def log_security_event(event_type: str, user_id: str = None, details: Dict = None):
    """Log security events for audit purposes"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'event_type': event_type,
        'user_id': user_id,
        'ip_address': get_remote_address(),
        'user_agent': request.headers.get('User-Agent', 'Unknown')[:500],
        'details': details or {}
    }
    
    # In production, you would write this to a secure log file or database
    print(f"SECURITY EVENT: {log_entry}")

# Security configuration

class SecurityConfig:
    """Security configuration settings"""
    
    # Password policies
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SYMBOLS = True
    PASSWORD_HISTORY_SIZE = 5  # Remember last 5 passwords
    
    # Session settings
    SESSION_TIMEOUT = timedelta(hours=24)
    SESSION_REFRESH_ENABLED = True
    
    # Rate limiting
    RATE_LIMIT_LOGIN_ATTEMPTS = 5
    RATE_LIMIT_PASSWORD_RESET = 3
    RATE_LIMIT_EMAIL_VERIFICATION = 3
    
    # Token expiration
    PASSWORD_RESET_TOKEN_EXPIRY = timedelta(hours=1)
    EMAIL_VERIFICATION_TOKEN_EXPIRY = timedelta(days=1)
    API_KEY_EXPIRY = timedelta(days=365)
    
    # Security headers
    HSTS_MAX_AGE = 31536000  # 1 year
    CSP_ENABLED = True
    
    @classmethod
    def get_password_policy_description(cls):
        """Get human-readable password policy description"""
        requirements = [f"at least {cls.PASSWORD_MIN_LENGTH} characters"]
        
        if cls.PASSWORD_REQUIRE_UPPERCASE:
            requirements.append("one uppercase letter")
        if cls.PASSWORD_REQUIRE_LOWERCASE:
            requirements.append("one lowercase letter")
        if cls.PASSWORD_REQUIRE_NUMBERS:
            requirements.append("one number")
        if cls.PASSWORD_REQUIRE_SYMBOLS:
            requirements.append("one special character")
            
        return f"Password must contain {', '.join(requirements)}."

# Utility function to check if request is from a secure context

def is_secure_request():
    """Check if request is made over HTTPS or secure connection"""
    return request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https'

# Export security configuration instance
security_config = SecurityConfig()