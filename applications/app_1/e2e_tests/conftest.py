import os
import pytest
import requests
from typing import Generator
import time

def pytest_addoption(parser):
    parser.addoption(
        "--api-url",
        action="store",
        default=os.getenv("API_URL", "http://staging-api.example.com"),
        help="URL of the staging API"
    )
    parser.addoption(
        "--api-key",
        action="store",
        default=os.getenv("STAGING_API_KEY"),
        help="API key for staging environment"
    )

@pytest.fixture(scope="session")
def api_url(request) -> str:
    return request.config.getoption("--api-url")

@pytest.fixture(scope="session")
def api_key(request) -> str:
    api_key = request.config.getoption("--api-key")
    if not api_key:
        raise ValueError("API key is required for e2e tests. Set STAGING_API_KEY environment variable or use --api-key option")
    return api_key

@pytest.fixture(scope="session")
def api_client(api_url: str, api_key: str):
    """Create a session for making API requests"""
    session = requests.Session()
    session.headers.update({"X-API-Key": api_key})
    
    # Wait for API to be available
    max_retries = 5
    retry_delay = 2
    for i in range(max_retries):
        try:
            response = session.get(f"{api_url}/api/v1/users/")
            response.raise_for_status()
            break
        except requests.RequestException as e:
            if i == max_retries - 1:
                raise Exception(f"API not available after {max_retries} retries: {e}")
            time.sleep(retry_delay)
    
    return session

@pytest.fixture(scope="function")
def cleanup_users(api_client, api_url):
    """Cleanup fixture to remove test users after each test"""
    test_users = []
    
    yield test_users
    
    # Cleanup after test
    for user_id in test_users:
        try:
            api_client.delete(f"{api_url}/api/v1/users/{user_id}")
        except requests.RequestException:
            pass  # Ignore cleanup errors 