#!/bin/bash

# Create necessary directories
mkdir -p static/uploads/documents static/uploads/licenses data/sessions data/users templates

# Start the application
exec gunicorn --bind 0.0.0.0:${PORT:-8000} --workers 2 --threads 4 --timeout 120 app:app