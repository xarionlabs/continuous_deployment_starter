"""
Tests for Airflow DAGs.

This module contains tests for DAG structure, syntax, and basic functionality.
"""

import pytest
from datetime import datetime, timedelta
from airflow.models import DagBag
from airflow.utils.dag_cycle import check_cycle


class TestDAGStructure:
    """Test DAG structure and configuration."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.dagbag = DagBag(dag_folder='src/dags/', include_examples=False)
    
    def test_dag_loading(self):
        """Test that all DAGs load without errors."""
        assert len(self.dagbag.dags) > 0
        assert len(self.dagbag.import_errors) == 0
    
    def test_dag_ids(self):
        """Test that expected DAGs are present."""
        expected_dags = [
            'shopify_customer_data',
            'shopify_order_data',
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
            assert dag.schedule_interval is not None
            
            # Test DAG has tasks
            assert len(dag.tasks) > 0
            
            # Test no cycles in DAG
            check_cycle(dag)
    
    def test_dag_default_args(self):
        """Test DAG default arguments."""
        for dag_id, dag in self.dagbag.dags.items():
            default_args = dag.default_args
            
            # Test required default args
            assert 'owner' in default_args
            assert 'start_date' in default_args
            assert 'retries' in default_args
            assert 'retry_delay' in default_args
            
            # Test start_date is not in the future
            assert default_args['start_date'] <= datetime.now()
            
            # Test retry_delay is a timedelta
            assert isinstance(default_args['retry_delay'], timedelta)


class TestShopifyCustomerDataDAG:
    """Test Shopify Customer Data DAG."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.dagbag = DagBag(dag_folder='src/dags/', include_examples=False)
        self.dag = self.dagbag.get_dag('shopify_customer_data')
    
    def test_dag_exists(self):
        """Test that the DAG exists."""
        assert self.dag is not None
    
    def test_dag_tasks(self):
        """Test DAG tasks."""
        expected_tasks = [
            'extract_customer_data',
            'store_customer_data',
            'validate_customer_data',
            'health_check',
        ]
        
        actual_tasks = [task.task_id for task in self.dag.tasks]
        
        for task_id in expected_tasks:
            assert task_id in actual_tasks
    
    def test_dag_schedule(self):
        """Test DAG schedule."""
        # Daily at 2:00 AM UTC
        assert self.dag.schedule_interval == '0 2 * * *'
    
    def test_dag_dependencies(self):
        """Test task dependencies."""
        extract_task = self.dag.get_task('extract_customer_data')
        store_task = self.dag.get_task('store_customer_data')
        validate_task = self.dag.get_task('validate_customer_data')
        health_check_task = self.dag.get_task('health_check')
        
        # Test upstream dependencies
        assert extract_task.upstream_task_ids == set()
        assert store_task.upstream_task_ids == {'extract_customer_data'}
        assert validate_task.upstream_task_ids == {'store_customer_data'}
        assert health_check_task.upstream_task_ids == {'validate_customer_data'}


class TestShopifyOrderDataDAG:
    """Test Shopify Order Data DAG."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.dagbag = DagBag(dag_folder='src/dags/', include_examples=False)
        self.dag = self.dagbag.get_dag('shopify_order_data')
    
    def test_dag_exists(self):
        """Test that the DAG exists."""
        assert self.dag is not None
    
    def test_dag_tasks(self):
        """Test DAG tasks."""
        expected_tasks = [
            'extract_order_data',
            'store_order_data',
            'calculate_order_metrics',
            'health_check',
        ]
        
        actual_tasks = [task.task_id for task in self.dag.tasks]
        
        for task_id in expected_tasks:
            assert task_id in actual_tasks
    
    def test_dag_schedule(self):
        """Test DAG schedule."""
        # Every 4 hours
        assert self.dag.schedule_interval == '0 */4 * * *'
    
    def test_dag_dependencies(self):
        """Test task dependencies."""
        extract_task = self.dag.get_task('extract_order_data')
        store_task = self.dag.get_task('store_order_data')
        metrics_task = self.dag.get_task('calculate_order_metrics')
        health_check_task = self.dag.get_task('health_check')
        
        # Test upstream dependencies
        assert extract_task.upstream_task_ids == set()
        assert store_task.upstream_task_ids == {'extract_order_data'}
        assert metrics_task.upstream_task_ids == {'store_order_data'}
        assert health_check_task.upstream_task_ids == {'calculate_order_metrics'}


if __name__ == '__main__':
    pytest.main([__file__])