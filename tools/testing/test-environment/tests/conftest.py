import pytest
import requests
import time
import os
from typing import Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor

# Test environment URLs
SERVICES = {
    'postgres': {
        'url': 'postgresql://test_user:test_password@test-postgres:5432/test_db',
        'health_check': None
    },
    'app1': {
        'url': os.getenv('APP1_URL', 'http://test-app1:8000'),
        'health_check': '/health'
    },
    'app2': {
        'url': os.getenv('APP2_URL', 'http://test-app2:3000'),
        'health_check': '/health'
    },
    'shopify_app': {
        'url': os.getenv('SHOPIFY_APP_URL', 'http://test-shopify-app:3000'),
        'health_check': '/health'
    },
    'nginx': {
        'url': os.getenv('NGINX_URL', 'http://test-nginx:80'),
        'health_check': '/health'
    },
    'airflow': {
        'url': os.getenv('AIRFLOW_URL', 'http://test-airflow:8080'),
        'health_check': '/health'
    },
    'registry': {
        'url': os.getenv('REGISTRY_URL', 'http://test-registry:5000'),
        'health_check': '/v2/'
    }
}

@pytest.fixture(scope="session")
def wait_for_services():
    """Wait for all services to be healthy before running tests"""
    max_retries = 30
    retry_delay = 5
    
    for service_name, config in SERVICES.items():
        if config['health_check'] is None:
            continue
            
        print(f"Waiting for {service_name} to be healthy...")
        
        for attempt in range(max_retries):
            try:
                url = config['url'] + config['health_check']
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    print(f"✅ {service_name} is healthy")
                    break
                else:
                    print(f"❌ {service_name} returned status {response.status_code}")
                    
            except Exception as e:
                print(f"❌ {service_name} health check failed: {e}")
                
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                pytest.fail(f"Service {service_name} failed to become healthy after {max_retries} attempts")
    
    print("All services are healthy!")
    return True

@pytest.fixture
def db_connection():
    """Provide database connection for tests"""
    conn = psycopg2.connect(
        host='test-postgres',
        port=5432,
        user='test_user',
        password='test_password',
        database='test_db'
    )
    yield conn
    conn.close()

@pytest.fixture
def db_cursor(db_connection):
    """Provide database cursor for tests"""
    cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    yield cursor
    cursor.close()

@pytest.fixture
def service_urls():
    """Provide service URLs for tests"""
    return SERVICES

@pytest.fixture
def test_deployment_data():
    """Provide test deployment data"""
    return {
        'app_name': 'test-app',
        'version': '1.0.0',
        'environment': 'test',
        'timestamp': '2024-01-01T00:00:00Z',
        'status': 'pending'
    }

@pytest.fixture
def cleanup_deployments(db_cursor, db_connection):
    """Clean up test deployments after each test"""
    yield
    # Clean up any test deployments
    db_cursor.execute("DELETE FROM deployments WHERE deployment_id LIKE 'test_%'")
    db_connection.commit()

class TestClient:
    """Test client for making HTTP requests with retries"""
    
    def __init__(self, base_url: str, max_retries: int = 3):
        self.base_url = base_url
        self.max_retries = max_retries
    
    def get(self, path: str, **kwargs) -> requests.Response:
        return self._request('GET', path, **kwargs)
    
    def post(self, path: str, **kwargs) -> requests.Response:
        return self._request('POST', path, **kwargs)
    
    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = self.base_url + path
        
        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, timeout=10, **kwargs)
                return response
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(1)

@pytest.fixture
def test_clients(service_urls):
    """Provide test clients for all services"""
    clients = {}
    for service_name, config in service_urls.items():
        if config['health_check'] is not None:
            clients[service_name] = TestClient(config['url'])
    return clients