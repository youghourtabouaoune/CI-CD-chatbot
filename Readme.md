# 🚀 CI/CD Helper - AI-Powered Pipeline Generator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **An intelligent AI-powered application that generates, optimizes, and explains CI/CD pipeline configurations using multiple LLM providers.**

CI/CD Helper streamlines DevOps workflows by leveraging advanced language models to create production-ready CI/CD configurations for GitHub Actions, GitLab CI, Jenkins, Azure DevOps, and more.

## ✨ Features

### 🤖 AI-Powered Generation
- **Multi-Provider Support**: Databricks (Llama models) and DeepSeek integration
- **Conversational Interface**: Natural language pipeline generation
- **Context-Aware**: Maintains conversation history for iterative refinement
- **Smart Clarification**: Asks intelligent questions to gather requirements

### 🔐 Robust Authentication
- **Email/Password**: Secure bcrypt hashing with salt
- **OAuth 2.0**: Google and GitHub authentication
- **Email Verification**: Code-based verification system
- **Password Recovery**: Secure token-based password reset
- **Account Protection**: Rate limiting and lockout after failed attempts

### 📊 Advanced Agent System (LangGraph)
- **Multi-Stage Pipeline**: Analysis → Planning → Generation → Validation
- **Web Search Integration**: Real-time best practices research
- **Quality Metrics**: Precision, recall, and F1 scoring
- **Performance Analysis**: Parallelization, caching, and security scoring
- **Cost Optimization**: Automated cost-saving recommendations

### 🛡️ Security Features
- **CSRF Protection**: Token-based protection for all state-changing operations
- **API Key Management**: JWT-based API keys with expiration
- **Rate Limiting**: Configurable limits per user/IP
- **File Upload Security**: Validation, sanitization, and size limits
- **Session Management**: Secure HTTP-only cookies with configurable expiration

### 📁 File Management
- **Multi-Format Support**: PDF, TXT, MD, YAML, JSON, XML
- **User-Specific Storage**: Isolated file storage per user
- **Document Processing**: Automatic categorization and metadata tracking

### 📧 Email Service
- **Transactional Emails**: Verification, password reset, welcome emails
- **HTML Templates**: Beautiful, responsive email templates
- **SMTP Support**: Flexible SMTP configuration (Gmail, AWS SES, etc.)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (HTML/JS)                   │
│  (index.html, login.html, signup.html, documentation)   │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTP/HTTPS
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Flask Application (app.py)                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Authentication Layer (security.py)               │  │
│  │  - JWT API Keys   - OAuth (oauth_client.py)      │  │
│  │  - CSRF Tokens    - Rate Limiting                 │  │
│  └──────────────────────────────────────────────────┘  │
└──────────┬────────────────────────────┬─────────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────┐    ┌──────────────────────────┐
│  LLM Providers        │    │  Data Layer              │
│  ┌─────────────────┐ │    │  ┌────────────────────┐ │
│  │ Databricks      │ │    │  │ UserManager        │ │
│  │ (databricks_    │ │    │  │ (user_model.py)    │ │
│  │  client.py)     │ │    │  │ - JSON Storage     │ │
│  ├─────────────────┤ │    │  │ - File Locking     │ │
│  │ DeepSeek        │ │    │  └────────────────────┘ │
│  │ (deepseek_      │ │    │  ┌────────────────────┐ │
│  │  client.py)     │ │    │  │ FileProcessor      │ │
│  └─────────────────┘ │    │  │ (file_processor.py)│ │
└──────────────────────┘    │  └────────────────────┘ │
           │                 └──────────────────────────┘
           ▼
┌──────────────────────────────────────────────────────────┐
│        LangGraph Agent (langgraph_agent.py)              │
│  ┌────────────────────────────────────────────────────┐ │
│  │  State Machine: Analysis → Clarification →          │ │
│  │  Planning → Generation → Validation → Finalization  │ │
│  ├────────────────────────────────────────────────────┤ │
│  │  Tools: Web Search, Code Analysis, Validation      │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│               External Services                           │
│  - SMTP (Email)  - OAuth Providers  - Web Search APIs   │
└──────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/cicd-helper.git
   cd cicd-helper
   ```

2. **Create and activate virtual environment**
   ```bash
   # Linux/macOS
   python -m venv venv
   source venv/bin/activate

   # Windows
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**
   ```bash
   # Development mode
   python app.py

   # Production mode (with Gunicorn)
   gunicorn --bind 0.0.0.0:5000 --workers 4 "app:create_app()"
   ```

6. **Access the application**
   ```
   Open your browser to: http://localhost:5000
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory:

```bash
# Application Settings
DEBUG=True
SECRET_KEY=your-super-secret-key-minimum-32-characters-long
SESSION_SECRET=your-session-secret-key-minimum-32-characters
PORT=5000
BASE_URL=http://localhost:5000

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Database (Future: PostgreSQL recommended for production)
# DATABASE_URL=postgresql://user:pass@localhost:5432/cicd_helper

# Redis (Recommended for production)
# REDIS_URL=redis://localhost:6379/0

# LLM Providers
DATABRICKS_ACCESS_TOKEN=your-databricks-access-token
DEEPSEEK_API_KEY=your-deepseek-api-key

# OAuth Providers
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
GITHUB_OAUTH_CLIENT_ID=your-github-client-id
GITHUB_OAUTH_CLIENT_SECRET=your-github-client-secret

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@yourdomain.com
APP_NAME=CI/CD Helper

# File Upload Settings
MAX_CONTENT_LENGTH=10485760  # 10MB
UPLOAD_FOLDER=static/uploads

# Rate Limiting
RATELIMIT_STORAGE_URI=memory://  # Use redis:// for production

# Monitoring (Optional)
# SENTRY_DSN=your-sentry-dsn
# LOG_LEVEL=INFO
```

### OAuth Setup

#### Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Configure OAuth consent screen
5. Create OAuth 2.0 credentials
6. Add authorized redirect URIs: `http://localhost:5000/api/auth/google/callback`
7. Copy Client ID and Client Secret to `.env`

#### GitHub OAuth
1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set Homepage URL: `http://localhost:5000`
4. Set Authorization callback URL: `http://localhost:5000/api/auth/github/callback`
5. Copy Client ID and Client Secret to `.env`

### Email Configuration

#### Gmail Setup
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password: [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Use the generated password in `SMTP_PASSWORD`

## 📚 API Documentation

### Authentication

#### Register New User
```http
POST /api/auth/signup
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "accept_terms": true
}
```

#### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}

Response:
{
  "success": true,
  "api_key": "eyJhbGc...",
  "user": {
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

### Code Generation

#### Generate CI/CD Pipeline
```http
POST /api/generate
Content-Type: application/json
X-API-Key: your-api-key

{
  "prompt": "Create a GitHub Actions workflow for a Node.js application with testing and deployment to AWS",
  "model": "meta-llama-3-3-70b-instruct",
  "action": "generate",
  "conversation_history": []
}

Response:
{
  "success": true,
  "content": "# Generated CI/CD configuration...",
  "model_used": "meta-llama-3-3-70b-instruct",
  "processing_time": 2.34,
  "tokens_used": 1234,
  "needs_clarification": false
}
```

### File Management

#### Upload File
```http
POST /api/files/upload
Content-Type: multipart/form-data
X-API-Key: your-api-key

file: [binary file data]
```

#### List Files
```http
GET /api/files/list
X-API-Key: your-api-key
```

#### Download File
```http
GET /api/files/{file_type}/{filename}/download
X-API-Key: your-api-key
```

### Available Models

#### Get Available Models
```http
GET /api/models
X-API-Key: your-api-key

Response:
{
  "success": true,
  "models": [
    {
      "id": "meta-llama-3-3-70b-instruct",
      "name": "Meta Llama 3 70B",
      "available": true,
      "provider": "databricks",
      "max_tokens": 4096
    },
    // ... more models
  ]
}
```

## 🐳 Docker Deployment

### Development

```bash
# Build image
docker build -t cicd-helper:dev .

# Run container
docker run -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  cicd-helper:dev
```

### Production

```bash
# Build production image
docker build -f Dockerfile.prod -t cicd-helper:latest .

# Run with docker-compose
docker-compose up -d
```

### Docker Compose

```yaml
version: '3.8'

services:
  app:
    image: cicd-helper:latest
    ports:
      - "5000:5000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://user:pass@db:5432/cicd_helper
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./data:/app/data
      - ./static/uploads:/app/static/uploads

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=cicd_helper
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-mock

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Test Structure

```
tests/
├── test_auth.py              # Authentication tests
├── test_api.py               # API endpoint tests
├── test_models.py            # Data model tests
├── test_security.py          # Security function tests
├── test_file_processor.py    # File handling tests
└── conftest.py               # Pytest fixtures
```

## 📊 Monitoring & Observability

### Health Checks

```bash
# Liveness probe
curl http://localhost:5000/health

# Detailed health
curl http://localhost:5000/api/health
```

### Metrics

The application exposes metrics at `/metrics` (when Prometheus integration is enabled):

- Request count and duration
- Active users
- Code generation counts
- Model usage statistics
- Error rates

### Logging

```bash
# View logs
tail -f logs/app.log

# In Docker
docker logs -f cicd-helper
```

## 🔒 Security Considerations

### Production Security Checklist

- ✅ Use strong, unique `SECRET_KEY` and `SESSION_SECRET`
- ✅ Enable HTTPS in production (`SESSION_COOKIE_SECURE=True`)
- ✅ Configure proper CORS origins (no wildcards)
- ✅ Use environment variables for all secrets
- ✅ Enable rate limiting with Redis backend
- ✅ Regular security updates for dependencies
- ✅ Implement proper logging and monitoring
- ✅ Use database instead of JSON files
- ✅ Configure CSP headers
- ✅ Enable HSTS headers

### Password Policy

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
- Protection against common passwords

## 📈 Performance Optimization

### Recommendations

1. **Use Redis for sessions and caching**
   ```python
   RATELIMIT_STORAGE_URI = 'redis://localhost:6379/1'
   SESSION_TYPE = 'redis'
   ```

2. **Enable caching for model availability**
   ```python
   @cache.cached(timeout=600)
   def get_models():
       # ...
   ```

3. **Use connection pooling**
   ```python
   # For PostgreSQL
   SQLALCHEMY_POOL_SIZE = 10
   SQLALCHEMY_MAX_OVERFLOW = 20
   ```

4. **Implement CDN for static assets**

5. **Use async workers for long-running tasks**

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style

This project uses:
- **Black** for code formatting
- **Flake8** for linting
- **MyPy** for type checking

```bash
# Format code
black .

# Lint
flake8 .

# Type check
mypy . --ignore-missing-imports
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **LangGraph** - For the powerful graph-based agent framework
- **Flask** - For the excellent web framework
- **Databricks** - For providing access to Llama models
- **DeepSeek** - For their coding-specialized models
- **Anthropic Claude** - For AI assistance in development

## 📞 Support

- **Documentation**: [Link to docs]
- **Issues**: [GitHub Issues](https://github.com/yourusername/cicd-helper/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/cicd-helper/discussions)
- **Email**: support@yourdomain.com

## 🗺️ Roadmap

### Version 1.1 (Q1 2025)
- [ ] PostgreSQL database migration
- [ ] Redis integration for sessions/caching
- [ ] Comprehensive test suite (80%+ coverage)
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Performance benchmarking

### Version 1.2 (Q2 2025)
- [ ] Additional LLM providers (OpenAI, Anthropic)
- [ ] Batch processing for multiple pipelines
- [ ] Pipeline templates library
- [ ] Team collaboration features
- [ ] Advanced analytics dashboard

### Version 2.0 (Q3 2025)
- [ ] GitOps integration (ArgoCD, Flux)
- [ ] Infrastructure as Code generation (Terraform, Pulumi)
- [ ] Policy enforcement engine
- [ ] Multi-cloud deployment support
- [ ] Enterprise SSO integration

## 📊 Project Statistics

- **Lines of Code**: ~5,000+
- **API Endpoints**: 30+
- **Supported CI/CD Platforms**: 8+
- **LLM Providers**: 2
- **Authentication Methods**: 3 (Email, Google, GitHub)

## 💡 Use Cases

1. **DevOps Engineers**: Quickly generate standardized CI/CD pipelines
2. **Development Teams**: Bootstrap new projects with production-ready CI/CD
3. **Learning**: Understand CI/CD best practices through AI-generated examples
4. **Migration**: Convert between different CI/CD platforms
5. **Optimization**: Get recommendations for improving existing pipelines

## 🎯 Key Differentiators

- **Multi-Provider LLM**: Not locked to a single AI provider
- **Conversational Interface**: Natural language pipeline generation
- **Production-Ready**: Security, authentication, and rate limiting built-in
- **Advanced Agent**: LangGraph-powered multi-stage processing
- **Quality Metrics**: Precision scoring and validation
- **Cost-Aware**: Automatic cost optimization recommendations

---

<div align="center">
  
**Made with ❤️ by the DevOps Community**

[⭐ Star this repo](https://github.com/yourusername/cicd-helper) | [🐛 Report Bug](https://github.com/yourusername/cicd-helper/issues) | [✨ Request Feature](https://github.com/yourusername/cicd-helper/issues)

</div>