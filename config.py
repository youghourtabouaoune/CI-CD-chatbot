# config.py (updated)
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    SESSION_SECRET = os.environ.get('SESSION_SECRET', 'dev-session-secret-change-in-production')
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
    
    # API Keys
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
    
    # OAuth Configuration
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')
    GITHUB_OAUTH_CLIENT_ID = os.environ.get('GITHUB_OAUTH_CLIENT_ID', '')
    GITHUB_OAUTH_CLIENT_SECRET = os.environ.get('GITHUB_OAUTH_CLIENT_SECRET', '')
    
    # Email Configuration
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME', '')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@cicd-helper.com')
    APP_NAME = os.environ.get('APP_NAME', 'CI/CD Helper')
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    
    # Model Configuration
    MODEL_CONFIGS = {
        "meta-llama-3-3-70b-instruct": {
            "name": "Meta Llama 3 70B",
            "max_tokens": 4096,
            "temperature": 0.1,
            "provider": "databricks"
        },
        "llama-4-maverick": {
            "name": "Llama 4 Maverick", 
            "max_tokens": 4096,
            "temperature": 0.1,
            "provider": "databricks"
        },
        "meta-llama-3-1-405b-instruct": {
            "name": "Meta Llama 3.1 405B",
            "max_tokens": 4096,
            "temperature": 0.1,
            "provider": "databricks"
        },
        "deepseek-coder": {
            "name": "DeepSeek Coder",
            "max_tokens": 4096,
            "temperature": 0.1,
            "provider": "deepseek"
        },
        "deepseek-chat": {
            "name": "DeepSeek Chat",
            "max_tokens": 4096,
            "temperature": 0.1,
            "provider": "deepseek"
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