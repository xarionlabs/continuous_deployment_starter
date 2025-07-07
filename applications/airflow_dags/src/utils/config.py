"""
Configuration utilities for Airflow DAGs.

Provides centralized configuration management for:
- Environment variables
- Airflow Variables
- Connection parameters
- Default values
"""

import os
from typing import Optional, Dict, Any
from pydantic import Field
from pydantic_settings import BaseSettings


class AirflowConfig(BaseSettings):
    """Configuration class for Airflow DAGs."""
    
    # Shopify Configuration
    shopify_shop_name: str = Field(..., env='SHOPIFY_SHOP_NAME')
    shopify_access_token: str = Field(..., env='SHOPIFY_ACCESS_TOKEN')
    
    # Database Configuration
    postgres_user: str = Field('postgres', env='POSTGRES_USER')
    postgres_password: str = Field(..., env='POSTGRES_PASSWORD')
    postgres_db: str = Field('airflow_db', env='POSTGRES_DB')
    postgres_host: str = Field('localhost', env='POSTGRES_HOST')
    postgres_port: int = Field(5432, env='POSTGRES_PORT')
    
    # PXY6 Application Database Configuration
    pxy6_postgres_user: str = Field('postgres', env='PXY6_POSTGRES_USER')
    pxy6_postgres_password: str = Field(..., env='PXY6_POSTGRES_PASSWORD')
    pxy6_postgres_db: str = Field('pxy6_db', env='PXY6_POSTGRES_DB')
    pxy6_postgres_host: str = Field('localhost', env='PXY6_POSTGRES_HOST')
    pxy6_postgres_port: int = Field(5432, env='PXY6_POSTGRES_PORT')
    
    # Application Settings
    development: bool = Field(False, env='DEVELOPMENT')
    log_level: str = Field('INFO', env='LOG_LEVEL')
    
    # Optional Email Configuration
    smtp_host: Optional[str] = Field(None, env='SMTP_HOST')
    smtp_port: int = Field(587, env='SMTP_PORT')
    smtp_user: Optional[str] = Field(None, env='SMTP_USER')
    smtp_password: Optional[str] = Field(None, env='SMTP_PASSWORD')
    smtp_from_email: Optional[str] = Field(None, env='SMTP_FROM_EMAIL')
    
    # Optional Slack Configuration
    slack_webhook_url: Optional[str] = Field(None, env='SLACK_WEBHOOK_URL')
    slack_channel: Optional[str] = Field(None, env='SLACK_CHANNEL')
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


def get_config() -> AirflowConfig:
    """Get the configuration instance."""
    return AirflowConfig()


def get_shopify_config() -> Dict[str, str]:
    """Get Shopify-specific configuration."""
    config = get_config()
    return {
        'shop_name': config.shopify_shop_name,
        'access_token': config.shopify_access_token,
    }


def get_database_config() -> Dict[str, Any]:
    """Get database configuration for Airflow metadata."""
    config = get_config()
    return {
        'user': config.postgres_user,
        'password': config.postgres_password,
        'host': config.postgres_host,
        'port': config.postgres_port,
        'database': config.postgres_db,
    }


def get_pxy6_database_config() -> Dict[str, Any]:
    """Get PXY6 application database configuration."""
    config = get_config()
    return {
        'user': config.pxy6_postgres_user,
        'password': config.pxy6_postgres_password,
        'host': config.pxy6_postgres_host,
        'port': config.pxy6_postgres_port,
        'database': config.pxy6_postgres_db,
    }