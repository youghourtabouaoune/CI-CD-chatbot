import os
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from config import config
from models.request_models import (
    CodeGenerationRequest, CodeGenerationResponse, 
    DocumentUploadResponse, HealthResponse
)
from utils.databricks_client import DatabricksClient
from utils.file_processor import FileProcessor
from utils.security import api_key_required, generate_api_key, verify_api_key, sanitize_filename

# Load environment variables
load_dotenv()

def create_app(config_name='default'):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    CORS(app, origins=['*'], supports_credentials=True)  # Allow all origins for development
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=app.config['RATELIMIT_DEFAULT'].split(';')
    )
    
    # Initialize services
    databricks_client = DatabricksClient(model_configs=app.config['MODEL_CONFIGS'])
    file_processor = FileProcessor(
        upload_folder=app.config['UPLOAD_FOLDER'],
        allowed_extensions=app.config['ALLOWED_EXTENSIONS']
    )
    
    # Add this route to your existing app.py
    @app.route('/documentation')
    def documentation():
        """Serve the documentation library page"""
        return send_from_directory('templates', 'documentation.html')
    @app.route('/login')
    def login():
        """Serve the login page"""
        return send_from_directory('templates', 'login.html')
    
    @app.route('/signup')
    def signup():
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
    
    @app.route('/static/uploads/<path:path>')
    def serve_uploads(path):
        """Serve uploaded files"""
        uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
        return send_from_directory(uploads_dir, path)
    
    @app.route('/api/health', methods=['GET', 'OPTIONS'])
    def health_check():
        """Health check endpoint"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            model_availability = databricks_client.check_model_availability()
            
            response = HealthResponse(
                status="healthy",
                timestamp=datetime.utcnow().isoformat(),
                version="1.0.0",
                models_available=list(model_availability.keys())
            )
            
            return jsonify(response.dict())
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    @app.route('/api/generate', methods=['POST', 'OPTIONS'])
    @api_key_required
    @limiter.limit("20 per minute")
    def generate_code():
        """Generate CI/CD code using AI models"""
        if request.method == 'OPTIONS':
            return '', 200
            
        start_time = time.time()
        
        try:
            # Validate request data
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
                
            request_data = CodeGenerationRequest(**data)
            
            # Generate code using Databricks
            result = databricks_client.generate_code(
                prompt=request_data.prompt,
                model=request_data.model.value,
                action=request_data.action.value
            )
            
            # Prepare response
            if result['success']:
                response_data = CodeGenerationResponse(
                    success=True,
                    content=result['content'],
                    model_used=result['model_used'],
                    processing_time=result['processing_time'],
                    tokens_used=result.get('tokens_used')
                )
                return jsonify(response_data.dict()), 200
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
                
            result = file_processor.process_uploaded_file(file)
            
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
        """Get list of uploaded files"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            files = file_processor.get_uploaded_files()
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
            result = file_processor.delete_file(filename, file_type)
            
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
    
    @app.route('/api/generate-api-key', methods=['POST', 'OPTIONS'])
    def generate_new_api_key():
        """Generate new API key for authenticated users"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            data = request.get_json()
            user_id = data.get('user_id', 'default_user') if data else 'default_user'
            
            api_key = generate_api_key(user_id)
            
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
    
    @app.route('/api/models', methods=['GET', 'OPTIONS'])
    @api_key_required
    def get_models():
        """Get available models and their status"""
        if request.method == 'OPTIONS':
            return '', 200
            
        try:
            model_availability = databricks_client.check_model_availability()
            models_info = []
            
            for model_name, is_available in model_availability.items():
                model_config = app.config['MODEL_CONFIGS'].get(model_name, {})
                models_info.append({
                    'id': model_name,
                    'name': model_config.get('name', model_name),
                    'available': is_available,
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
    # Ensure all required directories exist
    os.makedirs('static/uploads/documents', exist_ok=True)
    os.makedirs('static/uploads/licenses', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    os.makedirs('utils', exist_ok=True)
    
    # Create app
    app = create_app('development' if os.environ.get('DEBUG', 'False').lower() == 'true' else 'production')
    
    # Get configuration
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    print(f"Starting Flask app on port {port}...")
    print(f"Debug mode: {debug}")
    print(f"Access the application at: http://localhost:{port}")
    print(f"Documentation page at: http://localhost:{port}/documentation")
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=debug)