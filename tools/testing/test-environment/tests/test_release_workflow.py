import pytest
import requests
import time
import json
import os
from typing import Dict, Any
import docker
from unittest.mock import Mock, patch

class TestReleaseWorkflow:
    """Test the complete release workflow simulation"""
    
    def test_full_release_pipeline(self, test_clients, db_cursor, db_connection, wait_for_services):
        """Test complete release pipeline from build to deployment"""
        # Step 1: Simulate build process
        build_results = {}
        
        for app_name in ['app1', 'app2', 'shopify_app']:
            client = test_clients[app_name]
            
            # Check initial health
            health_response = client.get('/health')
            assert health_response.status_code == 200
            
            build_results[app_name] = {
                'status': 'healthy',
                'version': health_response.json()['version']
            }
        
        # Step 2: Simulate deployment
        deployment_data = {
            'app_name': 'test-release-pipeline',
            'version': '1.0.0',
            'environment': 'test',
            'timestamp': '2024-01-01T00:00:00Z',
            'status': 'pending'
        }
        
        deployment_id = f"release_test_{int(time.time())}"
        
        # Insert deployment record
        db_cursor.execute("""
            INSERT INTO deployments (deployment_id, app_name, version, environment, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (deployment_id, deployment_data['app_name'], deployment_data['version'],
              deployment_data['environment'], deployment_data['status']))
        db_connection.commit()
        
        # Step 3: Simulate deployment process
        time.sleep(1)  # Simulate deployment time
        
        # Update deployment status
        db_cursor.execute("""
            UPDATE deployments 
            SET status = %s, completed_at = CURRENT_TIMESTAMP
            WHERE deployment_id = %s
        """, ('completed', deployment_id))
        db_connection.commit()
        
        # Step 4: Verify deployment
        db_cursor.execute("SELECT * FROM deployments WHERE deployment_id = %s", (deployment_id,))
        result = db_cursor.fetchone()
        
        assert result is not None
        assert result['status'] == 'completed'
        assert result['completed_at'] is not None
        
        # Step 5: Verify all services are still healthy
        for app_name in ['app1', 'app2', 'shopify_app']:
            client = test_clients[app_name]
            health_response = client.get('/health')
            assert health_response.status_code == 200
            
        # Cleanup
        db_cursor.execute("DELETE FROM deployments WHERE deployment_id = %s", (deployment_id,))
        db_connection.commit()
    
    def test_build_simulation(self, test_clients, wait_for_services):
        """Test build simulation for each application"""
        applications = ['app1', 'app2', 'shopify_app']
        
        for app_name in applications:
            client = test_clients[app_name]
            
            # Get application info
            if app_name == 'app1':
                info_response = client.get('/info')
            elif app_name == 'app2':
                info_response = client.get('/api/info')
            else:  # shopify_app
                info_response = client.get('/api/shopify/info')
            
            assert info_response.status_code == 200
            info_data = info_response.json()
            
            # Verify build information
            assert 'app_name' in info_data
            assert 'version' in info_data
            assert 'environment' in info_data
            assert info_data['environment'] == 'test'
    
    def test_deployment_simulation(self, test_clients, wait_for_services):
        """Test deployment simulation endpoints"""
        deployment_data = {
            'app_name': 'test-deployment',
            'version': '1.0.0',
            'environment': 'test',
            'timestamp': '2024-01-01T00:00:00Z',
            'status': 'pending'
        }
        
        # Test App1 deployment
        app1_client = test_clients['app1']
        app1_response = app1_client.post('/deploy', json=deployment_data)
        assert app1_response.status_code == 200
        app1_data = app1_response.json()
        assert app1_data['status'] == 'success'
        
        # Test App2 deployment
        app2_client = test_clients['app2']
        app2_response = app2_client.post('/api/deploy', json=deployment_data)
        assert app2_response.status_code == 200
        app2_data = app2_response.json()
        assert app2_data['status'] == 'success'
    
    def test_registry_functionality(self, test_clients, wait_for_services):
        """Test container registry functionality"""
        registry_client = test_clients['registry']
        
        # Test registry catalog
        response = registry_client.get('/v2/_catalog')
        assert response.status_code == 200
        
        # Test registry root
        response = registry_client.get('/v2/')
        assert response.status_code == 200
    
    def test_environment_isolation(self, test_clients, wait_for_services):
        """Test that test environment is properly isolated"""
        # Verify all services are running in test environment
        for app_name in ['app1', 'app2', 'shopify_app']:
            client = test_clients[app_name]
            health_response = client.get('/health')
            assert health_response.status_code == 200
            
            health_data = health_response.json()
            assert health_data['environment'] == 'test'
    
    def test_database_state_management(self, db_cursor, db_connection):
        """Test database state management during tests"""
        # Insert test data
        test_deployment_id = f"state_test_{int(time.time())}"
        db_cursor.execute("""
            INSERT INTO deployments (deployment_id, app_name, version, environment, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (test_deployment_id, 'state-test', '1.0.0', 'test', 'pending'))
        db_connection.commit()
        
        # Verify insertion
        db_cursor.execute("SELECT * FROM deployments WHERE deployment_id = %s", (test_deployment_id,))
        result = db_cursor.fetchone()
        assert result is not None
        assert result['deployment_id'] == test_deployment_id
        
        # Update state
        db_cursor.execute("""
            UPDATE deployments 
            SET status = %s, completed_at = CURRENT_TIMESTAMP
            WHERE deployment_id = %s
        """, ('completed', test_deployment_id))
        db_connection.commit()
        
        # Verify update
        db_cursor.execute("SELECT * FROM deployments WHERE deployment_id = %s", (test_deployment_id,))
        result = db_cursor.fetchone()
        assert result['status'] == 'completed'
        assert result['completed_at'] is not None
        
        # Cleanup
        db_cursor.execute("DELETE FROM deployments WHERE deployment_id = %s", (test_deployment_id,))
        db_connection.commit()
    
    def test_service_dependencies(self, test_clients, wait_for_services):
        """Test service dependencies and communication"""
        # Test that App1 can communicate with database
        app1_client = test_clients['app1']
        db_test_response = app1_client.get('/test-database')
        assert db_test_response.status_code == 200
        
        db_test_data = db_test_response.json()
        assert db_test_data['status'] == 'success'
        
        # Test that all services can be reached through Nginx
        nginx_client = test_clients['nginx']
        nginx_response = nginx_client.get('/health')
        assert nginx_response.status_code == 200
    
    def test_rollback_simulation(self, db_cursor, db_connection):
        """Test rollback simulation by reverting deployment status"""
        # Create a completed deployment
        deployment_id = f"rollback_test_{int(time.time())}"
        db_cursor.execute("""
            INSERT INTO deployments (deployment_id, app_name, version, environment, status, completed_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """, (deployment_id, 'rollback-test', '1.0.1', 'test', 'completed'))
        db_connection.commit()
        
        # Simulate rollback by updating status
        db_cursor.execute("""
            UPDATE deployments 
            SET status = %s, version = %s
            WHERE deployment_id = %s
        """, ('rolled_back', '1.0.0', deployment_id))
        db_connection.commit()
        
        # Verify rollback
        db_cursor.execute("SELECT * FROM deployments WHERE deployment_id = %s", (deployment_id,))
        result = db_cursor.fetchone()
        assert result['status'] == 'rolled_back'
        assert result['version'] == '1.0.0'
        
        # Cleanup
        db_cursor.execute("DELETE FROM deployments WHERE deployment_id = %s", (deployment_id,))
        db_connection.commit()

class TestErrorHandling:
    """Test error handling in release workflow"""
    
    def test_service_failure_simulation(self, test_clients, wait_for_services):
        """Test handling of service failures"""
        # Test invalid endpoint
        app1_client = test_clients['app1']
        response = app1_client.get('/invalid-endpoint')
        assert response.status_code == 404
    
    def test_database_connection_failure_handling(self, db_cursor, db_connection):
        """Test handling of database connection issues"""
        # Try to access non-existent table
        with pytest.raises(Exception):
            db_cursor.execute("SELECT * FROM non_existent_table")
    
    def test_deployment_failure_simulation(self, db_cursor, db_connection):
        """Test deployment failure scenarios"""
        # Create a failed deployment
        deployment_id = f"failed_deployment_{int(time.time())}"
        db_cursor.execute("""
            INSERT INTO deployments (deployment_id, app_name, version, environment, status, logs)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (deployment_id, 'failed-app', '1.0.0', 'test', 'failed', 'Deployment failed due to test error'))
        db_connection.commit()
        
        # Verify failure is recorded
        db_cursor.execute("SELECT * FROM deployments WHERE deployment_id = %s", (deployment_id,))
        result = db_cursor.fetchone()
        assert result['status'] == 'failed'
        assert 'test error' in result['logs']
        
        # Cleanup
        db_cursor.execute("DELETE FROM deployments WHERE deployment_id = %s", (deployment_id,))
        db_connection.commit()