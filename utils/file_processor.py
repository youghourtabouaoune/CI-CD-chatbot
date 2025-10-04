import os
import uuid
from datetime import datetime
from typing import Dict, Any
from .security import sanitize_filename, validate_file_extension

class FileProcessor:
    def __init__(self, upload_folder, allowed_extensions):
        self.upload_folder = upload_folder
        self.allowed_extensions = allowed_extensions
        
        # Create upload directories if they don't exist
        os.makedirs(os.path.join(self.upload_folder, 'documents'), exist_ok=True)
        os.makedirs(os.path.join(self.upload_folder, 'licenses'), exist_ok=True)

    def process_uploaded_file(self, file) -> Dict[str, Any]:
        """Process uploaded file and save to appropriate location"""
        try:
            if not file or file.filename == '':
                return {
                    'success': False,
                    'error': 'No file selected'
                }

            filename = sanitize_filename(file.filename)
            
            if not validate_file_extension(filename, self.allowed_extensions):
                return {
                    'success': False,
                    'error': f'File type not allowed. Allowed types: {", ".join(self.allowed_extensions)}'
                }

            # Generate unique filename to prevent collisions
            file_extension = filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Determine upload path based on file type
            if file_extension in ['pdf', 'txt', 'md']:
                upload_path = os.path.join(self.upload_folder, 'documents', unique_filename)
                file_type = 'documents'
            else:
                upload_path = os.path.join(self.upload_folder, 'licenses', unique_filename)
                file_type = 'licenses'

            # Save file
            file.save(upload_path)
            file_size = os.path.getsize(upload_path)

            return {
                'success': True,
                'filename': unique_filename,
                'original_filename': filename,
                'file_path': upload_path,
                'file_size': file_size,
                'file_url': f'/static/uploads/{file_type}/{unique_filename}',
                'file_type': file_type,
                'upload_time': datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'File processing error: {str(e)}'
            }

    def get_uploaded_files(self) -> Dict[str, list]:
        """Get list of all uploaded files"""
        documents_dir = os.path.join(self.upload_folder, 'documents')
        licenses_dir = os.path.join(self.upload_folder, 'licenses')
        
        documents = []
        licenses = []
        
        # Scan documents directory
        if os.path.exists(documents_dir):
            for filename in os.listdir(documents_dir):
                file_path = os.path.join(documents_dir, filename)
                if os.path.isfile(file_path):
                    documents.append({
                        'filename': filename,
                        'file_url': f'/static/uploads/documents/{filename}',
                        'file_size': os.path.getsize(file_path),
                        'file_type': 'documents',
                        'upload_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                    })
        
        # Scan licenses directory
        if os.path.exists(licenses_dir):
            for filename in os.listdir(licenses_dir):
                file_path = os.path.join(licenses_dir, filename)
                if os.path.isfile(file_path):
                    licenses.append({
                        'filename': filename,
                        'file_url': f'/static/uploads/licenses/{filename}',
                        'file_size': os.path.getsize(file_path),
                        'file_type': 'licenses',
                        'upload_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat()
                    })
        
        return {
            'documents': documents,
            'licenses': licenses
        }

    def delete_file(self, filename: str, file_type: str) -> Dict[str, Any]:
        """Delete uploaded file"""
        try:
            if file_type not in ['documents', 'licenses']:
                return {
                    'success': False,
                    'error': 'Invalid file type'
                }
            
            file_path = os.path.join(self.upload_folder, file_type, sanitize_filename(filename))
            
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'error': 'File not found'
                }
            
            os.remove(file_path)
            
            return {
                'success': True,
                'message': 'File deleted successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'File deletion error: {str(e)}'
            }