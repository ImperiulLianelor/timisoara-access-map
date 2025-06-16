import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # General Config
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    FLASK_APP = os.environ.get('FLASK_APP') or 'run.py'
    FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
    
    # Database Config
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "app.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Map Boundaries (Timisoara)
    MAP_BOUNDS = {
        'north': 45.80,
        'south': 45.70,
        'east': 21.35,
        'west': 21.10,
        'center': [45.7557, 21.2300],
        'zoom': 13
    }
    
    # Upload settings
    UPLOAD_FOLDER = os.path.join(basedir, 'app/static/uploads')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB max upload size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Rate limiting
    RATELIMIT_DEFAULT = "100/hour"
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Languages
    LANGUAGES = ['en', 'ro']
    BABEL_DEFAULT_LOCALE = 'ro'


class DevelopmentConfig(Config):
    DEBUG = True
    WTF_CSRF_ENABLED=False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    # Use stronger secret key in production
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'production-hard-to-guess-string'
    
    # Configure a production-ready database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "production.db")}'
    
    # Set strict security headers
    REMEMBER_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Rate limiting for production
    RATELIMIT_DEFAULT = "50/hour"
