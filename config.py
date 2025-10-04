import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Security
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000').split(',')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URI = 'memory://'
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_DEFAULT = '200 per day;50 per hour'
    
    # File Upload
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB max file size
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'txt', 'md', 'yaml', 'yml', 'json', 'xml'}
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Model Configuration
    MODEL_CONFIGS = {
        "meta-llama-3-3-70b-instruct": {
            "name": "Meta Llama 3 70B",
            "max_tokens": 4096,
            "temperature": 0.1
        },
        "llama-4-maverick": {
            "name": "Llama 4 Maverick", 
            "max_tokens": 4096,
            "temperature": 0.1
        },
        "meta-llama-3-1-405b-instruct": {
            "name": "Meta Llama 3.1 405B",
            "max_tokens": 4096,
            "temperature": 0.1
        }
    }

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = True

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}