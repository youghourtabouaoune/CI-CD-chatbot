import os
import uuid
from datetime import datetime
from typing import Dict, Any, List
from .security import sanitize_filename, validate_file_extension

class FileProcessor:
    def __init__(self, upload_folder, allowed_extensions):
        self.upload_folder = upload_folder
        self.allowed_extensions = allowed_extensions
        
        # Create main upload directories if they don't exist
        os.makedirs(os.path.join(self.upload_folder, 'documents'), exist_ok=True)
        os.makedirs(os.path.join(self.upload_folder, 'licenses'), exist_ok=True)

    def process_uploaded_file(self, file, user_id: str = None) -> Dict[str, Any]:
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
            
            # Determine upload path based on file type and user
            if file_extension in ['pdf', 'txt', 'md']:
                if user_id:
                    user_doc_dir = os.path.join(self.upload_folder, 'documents', user_id)
                    os.makedirs(user_doc_dir, exist_ok=True)
                    upload_path = os.path.join(user_doc_dir, unique_filename)
                else:
                    upload_path = os.path.join(self.upload_folder, 'documents', unique_filename)
                file_type = 'documents'
            else:
                if user_id:
                    user_license_dir = os.path.join(self.upload_folder, 'licenses', user_id)
                    os.makedirs(user_license_dir, exist_ok=True)
                    upload_path = os.path.join(user_license_dir, unique_filename)
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
                'file_url': f'/static/uploads/{file_type}/{user_id + "/" if user_id else ""}{unique_filename}',
                'file_type': file_type,
                'upload_time': datetime.utcnow().isoformat(),
                'user_id': user_id
            }

        except Exception as e:
            return {
                'success': False,
                'error': f'File processing error: {str(e)}'
            }

    def get_uploaded_files(self, user_id: str = None) -> Dict[str, list]:
        """Get list of uploaded files for a specific user or all files if no user specified"""
        documents = []
        licenses = []
        
        if user_id:
            # Get user-specific files
            user_doc_dir = os.path.join(self.upload_folder, 'documents', user_id)
            user_license_dir = os.path.join(self.upload_folder, 'licenses', user_id)
            
            # Scan user documents directory
            if os.path.exists(user_doc_dir):
                for filename in os.listdir(user_doc_dir):
                    file_path = os.path.join(user_doc_dir, filename)
                    if os.path.isfile(file_path):
                        documents.append({
                            'filename': filename,
                            'file_url': f'/static/uploads/documents/{user_id}/{filename}',
                            'file_size': os.path.getsize(file_path),
                            'file_type': 'documents',
                            'upload_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                            'user_id': user_id
                        })
            
            # Scan user licenses directory
            if os.path.exists(user_license_dir):
                for filename in os.listdir(user_license_dir):
                    file_path = os.path.join(user_license_dir, filename)
                    if os.path.isfile(file_path):
                        licenses.append({
                            'filename': filename,
                            'file_url': f'/static/uploads/licenses/{user_id}/{filename}',
                            'file_size': os.path.getsize(file_path),
                            'file_type': 'licenses',
                            'upload_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                            'user_id': user_id
                        })
        else:
            # Get all files (for admin or unauthenticated users)
            documents_dir = os.path.join(self.upload_folder, 'documents')
            licenses_dir = os.path.join(self.upload_folder, 'licenses')
            
            # Scan documents directory (including user subdirectories)
            if os.path.exists(documents_dir):
                for item in os.listdir(documents_dir):
                    item_path = os.path.join(documents_dir, item)
                    if os.path.isdir(item_path):
                        # User directory
                        user_id = item
                        for filename in os.listdir(item_path):
                            file_path = os.path.join(item_path, filename)
                            if os.path.isfile(file_path):
                                documents.append({
                                    'filename': filename,
                                    'file_url': f'/static/uploads/documents/{user_id}/{filename}',
                                    'file_size': os.path.getsize(file_path),
                                    'file_type': 'documents',
                                    'upload_time': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                                    'user_id': user_id
                                })
                    elif os.path.isfile(item_path):
                        # Root level file
                        documents.append({
                            'filename': item,
                            'file_url': f'/static/uploads/documents/{item}',
                            'file_size': os.path.getsize(item_path),
                            'file_type': 'documents',
                            'upload_time': datetime.fromtimestamp(os.path.getctime(item_path)).isoformat(),
                            'user_id': None
                        })
            
            # Similar logic for licenses...
        
        return {
            'documents': documents,
            'licenses': licenses
        }

    def delete_file(self, filename: str, file_type: str, user_id: str = None) -> Dict[str, Any]:
        """Delete uploaded file"""
        try:
            if file_type not in ['documents', 'licenses']:
                return {
                    'success': False,
                    'error': 'Invalid file type'
                }
            
            if user_id:
                file_path = os.path.join(self.upload_folder, file_type, user_id, sanitize_filename(filename))
            else:
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