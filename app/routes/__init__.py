"""
Routes package initialization.
This file initializes all route blueprints for the application.
"""
from app.routes.main import main
from app.routes.auth import auth
from app.routes.admin import admin
from app.routes.api import api

# List of all blueprints for easy import in app factory
all_blueprints = [main, auth, admin, api]
