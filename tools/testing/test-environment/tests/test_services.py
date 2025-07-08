import pytest
import requests
import json
import time
from typing import Dict, Any

class TestServiceHealth:
    """Test that all services are healthy and responding"""
    
    def test_postgres_connection(self, db_cursor, wait_for_services):
        """Test PostgreSQL database connection"""
        db_cursor.execute("SELECT version()")
        result = db_cursor.fetchone()
        assert result is not None
        assert "PostgreSQL" in result[0]
    
    def test_app1_health(self, test_clients, wait_for_services):
        """Test App1 (FastAPI/Streamlit) health"""
        client = test_clients['app1']
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['version'] == '1.0.0'
        assert data['environment'] == 'test'
    
    def test_app2_health(self, test_clients, wait_for_services):
        """Test App2 (React/Vite) health"""
        client = test_clients['app2']
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['version'] == '1.0.0'
        assert data['environment'] == 'test'
    
    def test_shopify_app_health(self, test_clients, wait_for_services):
        """Test Shopify App health"""
        client = test_clients['shopify_app']
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['version'] == '1.0.0'
        assert data['environment'] == 'test'
    
    def test_nginx_health(self, test_clients, wait_for_services):
        """Test Nginx proxy health"""
        client = test_clients['nginx']
        response = client.get('/health')
        
        assert response.status_code == 200
        assert b'OK' in response.content
    
    def test_airflow_health(self, test_clients, wait_for_services):
        """Test Airflow health"""
        client = test_clients['airflow']
        response = client.get('/health')
        
        assert response.status_code == 200
    
    def test_registry_health(self, test_clients, wait_for_services):
        """Test container registry health"""
        client = test_clients['registry']
        response = client.get('/v2/')
        
        assert response.status_code == 200

class TestServiceIntegration:
    """Test integration between services"""
    
    def test_database_connectivity(self, test_clients, wait_for_services):
        """Test that applications can connect to database"""
        client = test_clients['app1']
        response = client.get('/test-database')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
    
    def test_app1_info_endpoint(self, test_clients, wait_for_services):
        """Test App1 info endpoint"""
        client = test_clients['app1']
        response = client.get('/info')
        
        assert response.status_code == 200
        data = response.json()
        assert data['app_name'] == 'test-app1'
        assert data['version'] == '1.0.0'
        assert data['environment'] == 'test'
        assert 'database_url' in data
        assert 'ports' in data
    
    def test_app2_info_endpoint(self, test_clients, wait_for_services):
        """Test App2 info endpoint"""
        client = test_clients['app2']
        response = client.get('/api/info')
        
        assert response.status_code == 200
        data = response.json()
        assert data['app_name'] == 'test-app2'
        assert data['version'] == '1.0.0'
        assert data['environment'] == 'test'
    
    def test_shopify_app_info_endpoint(self, test_clients, wait_for_services):
        """Test Shopify App info endpoint"""
        client = test_clients['shopify_app']
        response = client.get('/api/shopify/info')
        
        assert response.status_code == 200
        data = response.json()
        assert data['app_name'] == 'test-shopify-app'
        assert data['version'] == '1.0.0'
        assert data['environment'] == 'test'
    
    def test_shopify_orders_endpoint(self, test_clients, wait_for_services):
        """Test Shopify orders mock endpoint"""
        client = test_clients['shopify_app']
        response = client.get('/api/shopify/orders')
        
        assert response.status_code == 200
        data = response.json()
        assert 'orders' in data
        assert 'total_count' in data
        assert len(data['orders']) > 0
    
    def test_shopify_webhook_endpoint(self, test_clients, wait_for_services):
        """Test Shopify webhook endpoint"""
        client = test_clients['shopify_app']
        webhook_data = {
            'test': 'webhook',
            'timestamp': '2024-01-01T00:00:00Z'
        }
        
        response = client.post('/api/shopify/webhook', json=webhook_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['message'] == 'Webhook received'

class TestDeploymentSimulation:
    """Test deployment simulation endpoints"""
    
    def test_app1_deployment_simulation(self, test_clients, test_deployment_data, wait_for_services):
        """Test App1 deployment simulation"""
        client = test_clients['app1']
        response = client.post('/deploy', json=test_deployment_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Deployment simulated successfully'
        assert 'deployment_id' in data
        assert data['status'] == 'success'
    
    def test_app2_deployment_simulation(self, test_clients, test_deployment_data, wait_for_services):
        """Test App2 deployment simulation"""
        client = test_clients['app2']
        response = client.post('/api/deploy', json=test_deployment_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Frontend deployment simulated successfully'
        assert 'deployment_id' in data
        assert data['status'] == 'success'
    
    def test_deployment_tracking(self, db_cursor, db_connection, test_deployment_data, cleanup_deployments):
        """Test deployment tracking in database"""
        # Insert test deployment
        deployment_id = f"test_{int(time.time())}"
        db_cursor.execute("""
            INSERT INTO deployments (deployment_id, app_name, version, environment, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (deployment_id, test_deployment_data['app_name'], test_deployment_data['version'], 
              test_deployment_data['environment'], test_deployment_data['status']))
        db_connection.commit()
        
        # Verify deployment was inserted
        db_cursor.execute("SELECT * FROM deployments WHERE deployment_id = %s", (deployment_id,))
        result = db_cursor.fetchone()
        
        assert result is not None
        assert result['deployment_id'] == deployment_id
        assert result['app_name'] == test_deployment_data['app_name']
        assert result['version'] == test_deployment_data['version']
        assert result['environment'] == test_deployment_data['environment']
        assert result['status'] == test_deployment_data['status']

class TestNginxProxyRouting:
    """Test Nginx proxy routing (requires host header manipulation)"""
    
    def test_nginx_default_response(self, test_clients, wait_for_services):
        """Test Nginx default server response"""
        client = test_clients['nginx']
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'Test Nginx Server Running' in response.content
    
    def test_nginx_health_endpoint(self, test_clients, wait_for_services):
        """Test Nginx health endpoint"""
        client = test_clients['nginx']
        response = client.get('/health')
        
        assert response.status_code == 200
        assert b'OK' in response.content