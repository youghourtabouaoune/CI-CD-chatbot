# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create necessary directories
RUN mkdir -p static/uploads/documents static/uploads/licenses data/sessions data/users templates

# Expose port
EXPOSE 8000

# Run the application with gunicorn
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 app:app