#!/usr/bin/env python3

import os
import shutil
from pathlib import Path

def create_project_structure(base_dir: Path, package_name: str) -> None:
    """Create the project directory structure."""
    dirs = [
        base_dir / "src" / package_name,
        base_dir / "src" / package_name / "static",
        base_dir / "src" / package_name / "templates",
        base_dir / "tests",
        base_dir / "logs",
    ]
    
    for directory in dirs:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "__init__.py").touch(exist_ok=True)
    
    # Create empty files
    (base_dir / "src" / package_name / "__init__.py").touch()
    (base_dir / "tests" / "__init__.py").touch()

def create_dockerfile(base_dir: Path) -> None:
    """Create Dockerfile."""
    content = """# Use Python 3.12 slim as the base image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Expose port 50001
EXPOSE 50001

# Command to run the application
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:50001"]
"""
    (base_dir / "Dockerfile").write_text(content)

def create_gunicorn_conf(base_dir: Path) -> None:
    """Create gunicorn configuration file."""
    content = """import os
import logging
from pathlib import Path

# Logging configuration
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Log file settings
max_size = 100 * 1024 * 1024  # 100MB
backup_count = 5
log_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

# Set up log files
access_log = log_dir / "access.log"
error_log = log_dir / "error.log"

# Ensure log files exist
for log_file in [access_log, error_log]:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if not log_file.exists():
        log_file.touch()

# Common logging configuration
logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {'format': log_format},
        'access': {'format': '%(message)s'}
    },
    'handlers': {
        'error_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(error_log),
            'maxBytes': max_size,
            'backupCount': backup_count,
            'formatter': 'standard'
        },
        'access_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': str(access_log),
            'maxBytes': max_size,
            'backupCount': backup_count,
            'formatter': 'access'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        }
    },
    'loggers': {
        'gunicorn.error': {
            'handlers': ['error_file', 'console'],
            'level': 'DEBUG' if os.environ.get("ENVIRONMENT") != "PRODUCTION" else 'INFO',
            'propagate': False
        },
        'gunicorn.access': {
            'handlers': ['access_file'],
            'level': 'INFO',
            'propagate': False
        }
    },
    'root': {
        'handlers': ['error_file', 'console'],
        'level': 'DEBUG' if os.environ.get("ENVIRONMENT") != "PRODUCTION" else 'INFO'
    }
}

# Common settings
loglevel = "debug" if os.environ.get("ENVIRONMENT") != "PRODUCTION" else "info"
accesslog = str(access_log)
errorlog = str(error_log)
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(M)sms'

# Development settings
if os.environ.get("ENVIRONMENT") != "PRODUCTION":
    reload = True
    logconfig_dict['loggers']['gunicorn.error']['handlers'].append('console')
else:
    worker_class = "gthread"
    workers = 2 * os.cpu_count() + 1
    threads = 2
    max_requests = 1000
    max_requests_jitter = 50
"""
    (base_dir / "gunicorn.conf.py").write_text(content)

def create_pyproject_toml(base_dir: Path, app_name: str, package_name: str) -> None:
    """Create pyproject.toml file."""
    content = f"""[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{package_name}"
version = "0.1.0"
description = "A Flask application with Gunicorn"
requires-python = ">=3.12"
dependencies = [
    "flask>=3.0.0",
    "gunicorn>=21.0.0",
    "python-dotenv>=1.0.0"
]

[tool.setuptools]
include-package-data = true

[tool.setuptools.packages.find]
where = ["src"]
include = ["{package_name}"]

[project.optional-dependencies]
dev = [
    "pytest",
    "black",
    "flake8",
]
"""
    (base_dir / "pyproject.toml").write_text(content)

def create_flask_app(base_dir: Path, package_name: str) -> None:
    """Create a basic Flask application."""
    app_content = """from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_prefixed_env()
    
    # Initialize extensions here
    # db.init_app(app)
    
    # Register blueprints
    from . import routes
    app.register_blueprint(routes.bp)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=50001)
"""
    routes_content = """from flask import Blueprint, jsonify

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return jsonify({"status": "ok", "message": "Service is running"})

@bp.route('/health')
def health():
    return jsonify({"status": "healthy"})
"""
    
    (base_dir / "src" / package_name / "app.py").write_text(app_content)
    (base_dir / "src" / package_name / "routes.py").write_text(routes_content)

def create_gitignore(base_dir: Path) -> None:
    """Create .gitignore file."""
    content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# Environment variables
.env

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
Dockerfile
.dockerignore

# OS
.DS_Store
Thumbs.db
"""
    (base_dir / ".gitignore").write_text(content)

def create_env_example(base_dir: Path) -> None:
    """Create .env.example file."""
    content = """# Flask configuration
FLASK_APP=src/your_package_name/app.py
FLASK_ENV=development

# Application
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Gunicorn
# WORKERS=4
# THREADS=2
# MAX_REQUESTS=1000
# MAX_REQUESTS_JITTER=50
"""
    (base_dir / ".env.example").write_text(content)

def create_readme(base_dir: Path, app_name: str) -> None:
    """Create README.md file."""
    content = f"""# {app_name}

A Flask application with Gunicorn and Docker.

## Development Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\\venv\\Scripts\\activate
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Copy and configure environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. Run the development server:
   ```bash
   flask run --host=0.0.0.0 --port=50001
   ```

## Production

Build and run with Docker:

```bash
docker build -t {app_name} .
docker run -p 50001:50001 --env-file .env {app_name}
```
"""
    (base_dir / "README.md").write_text(content)

def main():
    print("Flask Project Generator")
    print("=====================")
    
    # Get user input
    app_name = input("Enter application name (e.g., myapp): ").strip()
    package_name = input("Enter Python package name (e.g., mypackage): ").strip()
    
    # Create base directory
    base_dir = Path.cwd() / app_name
    if base_dir.exists():
        print(f"Error: Directory '{app_name}' already exists.")
        return
    
    try:
        # Create project structure
        print(f"Creating project structure in {base_dir}...")
        create_project_structure(base_dir, package_name)
        
        # Create configuration files
        print("Generating configuration files...")
        create_dockerfile(base_dir)
        create_gunicorn_conf(base_dir)
        create_pyproject_toml(base_dir, app_name, package_name)
        create_flask_app(base_dir, package_name)
        create_gitignore(base_dir)
        create_env_example(base_dir)
        create_readme(base_dir, app_name)
        
        print(f"\n✅ Project '{app_name}' created successfully!")
        print(f"\nNext steps:")
        print(f"1. cd {app_name}")
        print("2. Set up a virtual environment and install dependencies")
        print("3. Configure your .env file")
        print("4. Start developing!")
        
    except Exception as e:
        print(f"\n❌ Error creating project: {e}")
        if base_dir.exists():
            print("Cleaning up...")
            shutil.rmtree(base_dir)

if __name__ == "__main__":
    main()
