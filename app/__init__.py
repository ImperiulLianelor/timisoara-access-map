import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_babel import Babel
from datetime import datetime

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
babel = Babel()

def create_app(config_class='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    babel.init_app(app)

    # Configure login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # Register blueprints
    from app.routes.main import main as main_bp
    app.register_blueprint(main_bp)

    from app.routes.auth import auth as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.admin import admin as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.routes.api import api as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # Create db tables if they don't exist
    with app.app_context():
        db.create_all()
        
    @babel.localeselector
    def get_locale():
        # Default to Romanian, but respect user preference if set
        from flask import request, session
        if 'language' in session:
            return session['language']
        return request.accept_languages.best_match(['ro', 'en'])
    
    # Register context processors
    @app.context_processor
    def inject_global_variables():
        return {
            'current_year': datetime.now().year
        }

    # Register CLI commands
    from commands import register_commands
    register_commands(app)

    return app
