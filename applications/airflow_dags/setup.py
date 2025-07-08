"""
Setup configuration for Shopify Airflow Package
"""
from setuptools import setup, find_packages

setup(
    name="pxy6",
    version="1.0.0",
    description="Shopify data integration package for Apache Airflow",
    author="PXY6 Team",
    author_email="team@pxy6.com",
    packages=["pxy6", "pxy6.operators", "pxy6.hooks", "pxy6.utils"],
    package_dir={
        "pxy6": "src",
        "pxy6.operators": "src/operators", 
        "pxy6.hooks": "src/hooks",
        "pxy6.utils": "src/utils"
    },
    python_requires=">=3.9",
    install_requires=[
        # Core GraphQL client for Shopify API
        "gql>=3.4.0,<4.0.0",
        "requests>=2.31.0,<3.0.0",
        # PostgreSQL async driver
        "asyncpg>=0.29.0,<1.0.0",
        # Configuration and validation
        "pydantic>=2.5.0,<3.0.0",
        "pydantic-settings>=2.0.0,<3.0.0",
        # Retry and backoff utilities
        "backoff>=2.2.1,<3.0.0",
        # Date and time handling
        "python-dateutil>=2.8.2,<3.0.0",
        # Logging and structured logging
        "structlog>=25.2.0,<26.0.0",
        # Environment variable handling
        "python-dotenv>=1.0.0,<2.0.0",
        # Airflow dependencies
        "apache-airflow>=3.0.0,<3.1.0",
        "apache-airflow-providers-postgres>=5.10.0,<6.0.0",
        # Rich console output for better debugging
        "rich>=13.7.0,<14.0.0",
        # Progress bars for long-running operations
        "tqdm>=4.66.0,<5.0.0",
        # Performance monitoring
        "psutil>=6.1.0,<7.0.0",
        # Data processing utilities
        "pandas>=2.1.0,<3.0.0",
        "numpy>=1.24.0,<2.0.0",
        # Security and validation
        "cryptography>=41.0.0,<42.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0,<8.0.0",
            "pytest-asyncio>=0.21.0,<1.0.0",
            "pytest-cov>=4.1.0,<5.0.0",
            "pytest-mock>=3.12.0,<4.0.0",
            "mypy>=1.7.0,<2.0.0",
            "types-python-dateutil>=2.8.19,<3.0.0",
            "types-requests>=2.31.0,<3.0.0",
            "black>=23.12.0,<24.0.0",
            "isort>=5.13.0,<6.0.0",
            "flake8>=6.1.0,<7.0.0",
            "ipython>=8.18.0,<9.0.0",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
    ],
)