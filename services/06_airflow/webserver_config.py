#!/usr/bin/env python3
"""
Airflow Webserver Configuration for Google OAuth Authentication

This configuration enables Google OAuth2 authentication for Apache Airflow 3.0.
"""

import os
from flask_appbuilder.security.manager import AUTH_OAUTH
from airflow.providers.fab.auth_manager.security_manager.override import FabAirflowSecurityManagerOverride

# Authentication type - OAuth for Google authentication
AUTH_TYPE = AUTH_OAUTH

# Enable CSRF protection
CSRF_ENABLED = True

# User registration settings
AUTH_USER_REGISTRATION = True  # Allow new users to register via OAuth
AUTH_USER_REGISTRATION_ROLE = "Viewer"  # Default role for new users
AUTH_ROLES_SYNC_AT_LOGIN = True  # Sync roles on every login

# Admin role configuration
AUTH_ROLE_ADMIN = 'Admin'

# Role mapping - map OAuth user info to Airflow roles
AUTH_ROLES_MAPPING = {
    "Viewer": ["Viewer"],
    "User": ["User"], 
    "Op": ["Op"],
    "Admin": ["Admin"],
}

# OAuth provider configuration for Google
OAUTH_PROVIDERS = [
    {
        'name': 'google',
        'icon': 'fa-google',
        'token_key': 'access_token',
        'remote_app': {
            # Google OAuth2 client credentials - set via environment variables
            'client_id': os.getenv('GOOGLE_OAUTH_CLIENT_ID', ''),
            'client_secret': os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', ''),
            
            # Google OAuth2 API endpoints
            'api_base_url': 'https://www.googleapis.com/oauth2/v2/',
            'client_kwargs': {
                'scope': 'email profile'
            },
            'request_token_url': None,
            'access_token_url': 'https://accounts.google.com/o/oauth2/token',
            'authorize_url': 'https://accounts.google.com/o/oauth2/auth'
        },
        # Optional: Restrict to specific email domains
        'whitelist': os.getenv('GOOGLE_OAUTH_DOMAIN_WHITELIST', '').split(',') if os.getenv('GOOGLE_OAUTH_DOMAIN_WHITELIST') else []
    }
]

# Custom security manager class (if needed for additional customization)
class CustomAirflowSecurityManager(FabAirflowSecurityManagerOverride):
    """
    Custom security manager for additional OAuth customizations.
    Currently uses default behavior, but can be extended as needed.
    """
    pass

# Use custom security manager
SECURITY_MANAGER_CLASS = CustomAirflowSecurityManager

# Optional: Session configuration
PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes

# Optional: Additional Flask-AppBuilder configuration
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = None

# Logging level for security manager (for debugging OAuth issues)
import logging
logging.getLogger('airflow.providers.fab.auth_manager.security_manager').setLevel(logging.DEBUG)