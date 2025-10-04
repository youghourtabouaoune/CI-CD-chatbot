import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from typing import Optional

def generate_api_key(user_id: str) -> str:
    """Generate a secure API key"""
    secret = os.environ.get('SECRET_KEY', 'default-secret')
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=365),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def verify_api_key(api_key: str) -> Optional[dict]:
    """Verify API key and return payload if valid"""
    try:
        secret = os.environ.get('SECRET_KEY', 'default-secret')
        payload = jwt.decode(api_key, secret, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

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
            
        request.user_id = payload['user_id']
        return f(*args, **kwargs)
    return decorated_function

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks"""
    import re
    # Remove any path components
    filename = os.path.basename(filename)
    # Remove non-alphanumeric characters (except dots, hyphens, underscores)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    return filename

def validate_file_extension(filename: str, allowed_extensions: set) -> bool:
    """Validate file extension"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions