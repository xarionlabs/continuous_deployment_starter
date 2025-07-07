"""
Airflow DAGs package for Shopify data integration.

This package contains DAGs and utilities for orchestrating Shopify data workflows
using Apache Airflow. It includes:

- DAGs for extracting Shopify data (customers, orders, products, etc.)
- Utilities for Shopify GraphQL API interactions
- Database connection and data storage utilities
- Plugins for custom Airflow operators and hooks

The package is designed to be deployed to the Airflow service defined in
services/06_airflow/ and integrates with the main application database
for storing processed Shopify data.
"""

__version__ = "1.0.0"
__author__ = "PXY6 Team"
__email__ = "tech@pxy6.com"