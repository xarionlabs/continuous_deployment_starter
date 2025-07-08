"""
Tests for Airflow DAGs.

This module contains tests for DAG structure, syntax, and basic functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from airflow.models import DagBag


class TestDAGStructure:
    """Test DAG structure and configuration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.dagbag = DagBag(dag_folder='dags/', include_examples=False)
    
    def test_dag_loading(self):
        """Test that all DAGs load without errors."""
        assert len(self.dagbag.dags) > 0
        assert len(self.dagbag.import_errors) == 0
    
    def test_dag_ids(self):
        """Test that expected DAGs are present."""
        expected_dags = [
            'shopify_sync',
            'shopify_analytics',
        ]
        
        for dag_id in expected_dags:
            assert dag_id in self.dagbag.dags.keys()
    
    def test_dag_structure(self):
        """Test DAG structure and configuration."""
        for dag_id, dag in self.dagbag.dags.items():
            # Test DAG has required attributes
            assert dag.dag_id == dag_id
            assert dag.description is not None
            assert dag.owner is not None
            assert dag.start_date is not None
            # Airflow 3.x uses 'schedule' instead of 'schedule_interval'
            # Schedule can be None for manually triggered DAGs
            assert hasattr(dag, 'schedule')
            
            # Test DAG has tasks
            assert len(dag.tasks) > 0
    
    def test_dag_default_args(self):
        """Test DAG default arguments."""
        for dag_id, dag in self.dagbag.dags.items():
            default_args = dag.default_args
            
            # Test required default args
            assert 'owner' in default_args
            assert 'depends_on_past' in default_args
            assert 'email_on_failure' in default_args
            assert 'email_on_retry' in default_args
            assert 'retries' in default_args
            assert 'retry_delay' in default_args
            
            # Test retry_delay is a timedelta
            assert isinstance(default_args['retry_delay'], timedelta)


class TestShopifySyncDAG:
    """Test Shopify Sync DAG."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.dagbag = DagBag(dag_folder='dags/', include_examples=False)
        self.dag = self.dagbag.get_dag('shopify_sync')
    
    def test_dag_exists(self):
        """Test that the DAG exists."""
        assert self.dag is not None
    
    def test_dag_tasks(self):
        """Test DAG tasks."""
        expected_tasks = [
            'sync_customers',
            'sync_orders',
            'sync_products',
            'generate_sync_summary',
        ]
        
        actual_tasks = [task.task_id for task in self.dag.tasks]
        
        for task_id in expected_tasks:
            assert task_id in actual_tasks
    
    def test_dag_schedule(self):
        """Test DAG schedule."""
        # Triggered manually via app.pxy6.com API
        # Airflow 3.x uses 'schedule' instead of 'schedule_interval'
        assert self.dag.schedule is None
    
    def test_dag_dependencies(self):
        """Test task dependencies."""
        summary_task = self.dag.get_task('generate_sync_summary')
        
        # Test that summary task has all sync tasks as upstreams
        expected_upstreams = {'sync_customers', 'sync_orders', 'sync_products'}
        assert summary_task.upstream_task_ids == expected_upstreams


class TestShopifyAnalyticsDAG:
    """Test Shopify Analytics DAG."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.dagbag = DagBag(dag_folder='dags/', include_examples=False)
        self.dag = self.dagbag.get_dag('shopify_analytics')
    
    def test_dag_exists(self):
        """Test that the DAG exists."""
        assert self.dag is not None
    
    def test_dag_tasks(self):
        """Test DAG tasks."""
        expected_tasks = [
            'wait_for_sync',
            'calculate_customer_metrics',
            'calculate_order_metrics',
            'calculate_product_metrics',
            'generate_analytics_report',
        ]
        
        actual_tasks = [task.task_id for task in self.dag.tasks]
        
        for task_id in expected_tasks:
            assert task_id in actual_tasks
    
    def test_dag_schedule(self):
        """Test DAG schedule."""
        # Triggered manually or by external task sensor
        # Airflow 3.x uses 'schedule' instead of 'schedule_interval'
        assert self.dag.schedule is None
    
    def test_dag_dependencies(self):
        """Test task dependencies."""
        wait_task = self.dag.get_task('wait_for_sync')
        report_task = self.dag.get_task('generate_analytics_report')
        
        # Test that wait_for_sync has no upstreams
        assert wait_task.upstream_task_ids == set()
        
        # Test that report task has all metrics tasks as upstreams
        expected_upstreams = {'calculate_customer_metrics', 'calculate_order_metrics', 'calculate_product_metrics'}
        assert report_task.upstream_task_ids == expected_upstreams


if __name__ == '__main__':
    pytest.main([__file__])