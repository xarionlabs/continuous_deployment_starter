"""
Tests for Shopify DAG operators and functions.

This test suite validates the actual DAG operators to ensure they
process Shopify data correctly with the current codebase.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
from typing import Dict, Any

# Import the actual operators from current codebase
from pxy6.operators.shopify_operator import (
    ShopifyToPostgresOperator,
    ShopifyDataValidationOperator,
    ShopifyIncrementalSyncOperator,
    ShopifyDataQualityOperator,
    ShopifyChangeDetectionOperator,
    ShopifyMonitoringOperator
)
from pxy6.hooks.shopify_hook import ShopifyHook
from pxy6.utils.shopify_graphql import ShopifyGraphQLClient
from pxy6.utils.database import DatabaseManager


class TestShopifyToPostgresOperator:
    """Test ShopifyToPostgresOperator with different data types."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Airflow context."""
        return {
            'task_instance': Mock(),
            'ds': '2025-01-01',
            'execution_date': datetime(2025, 1, 1)
        }
    
    @pytest.fixture
    def sample_products_data(self):
        """Sample products data for testing."""
        return [
            {
                'id': 'gid://shopify/Product/1',
                'title': 'Test Product',
                'handle': 'test-product',
                'vendor': 'Test Vendor',
                'status': 'ACTIVE',
                'createdAt': '2025-01-01T00:00:00Z',
                'updatedAt': '2025-01-01T00:00:00Z'
            }
        ]
    
    @patch('pxy6.operators.shopify_operator.ShopifyHook')
    @patch('pxy6.operators.shopify_operator.DatabaseManager')
    @patch('pxy6.operators.shopify_operator.asyncio.run')
    def test_products_sync_operator(self, mock_asyncio, mock_db_manager, mock_hook_class, mock_context, sample_products_data):
        """Test product sync operator execution."""
        # Setup mocks
        mock_hook = Mock()
        mock_hook.test_connection.return_value = True
        mock_hook.get_paginated_data.return_value = sample_products_data
        mock_hook_class.return_value = mock_hook
        
        # Mock async result
        mock_asyncio.return_value = {
            'data_type': 'products',
            'extracted_count': 1,
            'loaded_count': 1,
            'error_count': 0,
            'success_rate': 1.0
        }
        
        # Create and execute operator
        operator = ShopifyToPostgresOperator(
            task_id='sync_products',
            data_type='products',
            batch_size=50
        )
        
        result = operator.execute(mock_context)
        
        # Assertions
        assert result['data_type'] == 'products'
        assert result['success_rate'] == 1.0
        mock_hook.test_connection.assert_called_once()
        mock_asyncio.assert_called_once()
    
    @patch('pxy6.operators.shopify_operator.ShopifyHook')
    @patch('pxy6.operators.shopify_operator.asyncio.run')
    def test_customers_sync_operator(self, mock_asyncio, mock_hook_class, mock_context):
        """Test customer sync operator execution."""
        # Setup mocks
        mock_hook = Mock()
        mock_hook.test_connection.return_value = True
        mock_hook_class.return_value = mock_hook
        
        mock_asyncio.return_value = {
            'data_type': 'customers',
            'extracted_count': 5,
            'loaded_count': 5,
            'error_count': 0,
            'success_rate': 1.0
        }
        
        # Create and execute operator
        operator = ShopifyToPostgresOperator(
            task_id='sync_customers',
            data_type='customers',
            batch_size=25
        )
        
        result = operator.execute(mock_context)
        
        # Assertions
        assert result['data_type'] == 'customers'
        assert result['extracted_count'] == 5
        mock_hook.test_connection.assert_called_once()
    
    def test_invalid_data_type_raises_error(self):
        """Test that invalid data type raises AirflowException."""
        from airflow.exceptions import AirflowException
        
        with pytest.raises(AirflowException, match="Invalid data_type"):
            ShopifyToPostgresOperator(
                task_id='invalid_sync',
                data_type='invalid_type'
            )


class TestShopifyDataValidationOperator:
    """Test ShopifyDataValidationOperator."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Airflow context."""
        return {
            'task_instance': Mock(),
            'ds': '2025-01-01'
        }
    
    @pytest.fixture
    def sample_validation_rules(self):
        """Sample validation rules for testing."""
        return [
            {
                'name': 'products_count_check',
                'query': 'SELECT COUNT(*) as count FROM shopify_products',
                'expected': 100
            },
            {
                'name': 'customers_email_check',
                'query': 'SELECT COUNT(*) as count FROM shopify_customers WHERE email IS NOT NULL'
            }
        ]
    
    @patch('pxy6.operators.shopify_operator.asyncio.run')
    def test_validation_operator_execution(self, mock_asyncio, mock_context, sample_validation_rules):
        """Test validation operator execution."""
        mock_asyncio.return_value = {
            'data_type': 'products',
            'total_records': 100,
            'validation_checks': [
                {
                    'rule_name': 'products_count_check',
                    'status': 'PASSED',
                    'actual': 100,
                    'expected': 100
                }
            ],
            'passed_checks': 1,
            'failed_checks': 0,
            'overall_status': 'PASSED'
        }
        
        operator = ShopifyDataValidationOperator(
            task_id='validate_products',
            data_type='products',
            validation_rules=sample_validation_rules
        )
        
        result = operator.execute(mock_context)
        
        assert result['overall_status'] == 'PASSED'
        assert result['passed_checks'] == 1
        assert result['failed_checks'] == 0


class TestShopifyIncrementalSyncOperator:
    """Test ShopifyIncrementalSyncOperator."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Airflow context."""
        return {
            'task_instance': Mock(),
            'ds': '2025-01-01'
        }
    
    @patch('pxy6.operators.shopify_operator.asyncio.run')
    def test_incremental_sync_execution(self, mock_asyncio, mock_context):
        """Test incremental sync operator execution."""
        mock_asyncio.return_value = {
            'data_type': 'products',
            'extracted_count': 10,
            'loaded_count': 10,
            'error_count': 0,
            'success_rate': 1.0,
            'sync_type': 'incremental'
        }
        
        operator = ShopifyIncrementalSyncOperator(
            task_id='incremental_sync_products',
            data_type='products',
            lookback_hours=24
        )
        
        result = operator.execute(mock_context)
        
        assert result['data_type'] == 'products'
        assert result['success_rate'] == 1.0


class TestShopifyDataQualityOperator:
    """Test ShopifyDataQualityOperator."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Airflow context."""
        return {
            'task_instance': Mock(),
            'ds': '2025-01-01'
        }
    
    @patch('pxy6.operators.shopify_operator.asyncio.run')
    def test_data_quality_operator_execution(self, mock_asyncio, mock_context):
        """Test data quality operator execution."""
        mock_asyncio.return_value = {
            'validation_timestamp': '2025-01-01T00:00:00',
            'data_types_validated': ['products', 'customers', 'orders'],
            'quality_checks': {
                'products': [
                    {'check_name': 'products_title_completeness', 'score': 0.95},
                    {'check_name': 'products_vendor_completeness', 'score': 0.90}
                ]
            },
            'overall_quality_score': 0.92,
            'validation_status': 'PASSED'
        }
        
        operator = ShopifyDataQualityOperator(
            task_id='quality_check',
            data_types=['products', 'customers', 'orders'],
            quality_threshold=0.9
        )
        
        result = operator.execute(mock_context)
        
        assert result['overall_quality_score'] == 0.92
        assert result['validation_status'] == 'PASSED'
    
    @patch('pxy6.operators.shopify_operator.asyncio.run')
    def test_data_quality_fails_below_threshold(self, mock_asyncio, mock_context):
        """Test data quality operator fails when below threshold."""
        from airflow.exceptions import AirflowException
        
        mock_asyncio.return_value = {
            'overall_quality_score': 0.85,
            'validation_status': 'FAILED'
        }
        
        operator = ShopifyDataQualityOperator(
            task_id='quality_check',
            quality_threshold=0.9
        )
        
        with pytest.raises(AirflowException, match="Data quality score"):
            operator.execute(mock_context)


class TestShopifyChangeDetectionOperator:
    """Test ShopifyChangeDetectionOperator."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Airflow context."""
        return {
            'task_instance': Mock(),
            'ds': '2025-01-01'
        }
    
    @patch('pxy6.operators.shopify_operator.asyncio.run')
    def test_change_detection_execution(self, mock_asyncio, mock_context):
        """Test change detection operator execution."""
        mock_asyncio.return_value = {
            'detection_timestamp': '2025-01-01T00:00:00',
            'data_types_analyzed': ['products', 'customers', 'orders'],
            'changes_detected': {
                'products': [
                    {'id': '1', 'title': 'Updated Product', 'sync_delay_seconds': 300}
                ],
                'customers': [],
                'orders': []
            },
            'total_changes': 1,
            'change_summary': {
                'products': {'recent_changes': 1, 'avg_sync_delay_seconds': 300}
            }
        }
        
        operator = ShopifyChangeDetectionOperator(
            task_id='detect_changes',
            data_types=['products', 'customers', 'orders']
        )
        
        result = operator.execute(mock_context)
        
        assert result['total_changes'] == 1
        assert len(result['changes_detected']['products']) == 1


class TestShopifyMonitoringOperator:
    """Test ShopifyMonitoringOperator."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock Airflow context."""
        return {
            'task_instance': Mock(),
            'ds': '2025-01-01'
        }
    
    @patch('pxy6.operators.shopify_operator.asyncio.run')
    def test_monitoring_operator_execution(self, mock_asyncio, mock_context):
        """Test monitoring operator execution."""
        mock_asyncio.return_value = {
            'monitoring_timestamp': '2025-01-01T00:00:00',
            'system_health': {
                'database_connectivity': True,
                'table_accessibility': True,
                'index_performance': True,
                'connection_pool_status': True
            },
            'data_quality': {
                'products_completeness': 0.95,
                'customers_completeness': 0.92,
                'orders_completeness': 0.98
            },
            'sync_performance': {
                'avg_sync_time': 120.0,
                'sync_success_rate': 1.0,
                'throughput_per_hour': 100.0
            },
            'data_freshness': {
                'products_freshness_hours': 2.0,
                'customers_freshness_hours': 3.0,
                'orders_freshness_hours': 1.5
            },
            'overall_status': 'HEALTHY'
        }
        
        operator = ShopifyMonitoringOperator(
            task_id='monitor_system',
            alert_thresholds={
                'data_quality_score': 0.9,
                'sync_delay_hours': 6
            }
        )
        
        # Mock the _process_alerts method to return no alerts
        with patch.object(operator, '_process_alerts', return_value=[]):
            result = operator.execute(mock_context)
        
        assert result['overall_status'] == 'HEALTHY'
        assert result['system_health']['database_connectivity'] is True
        assert 'alerts' in result