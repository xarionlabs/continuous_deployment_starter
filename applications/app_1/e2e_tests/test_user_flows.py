import requests
import time
import json

def test_user_crud_flow(api_client, api_url, cleanup_users):
    """Test complete user lifecycle"""
    # Create user
    email = f"test.user.{int(time.time())}@example.com"
    response = api_client.post(
        f"{api_url}/api/v1/users/",
        json={"email": email}
    )
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["email"] == email
    user_id = user_data["id"]
    cleanup_users.append(user_id)  # Add to cleanup list

    # Verify user exists in list
    response = api_client.get(f"{api_url}/api/v1/users/")
    assert response.status_code == 200
    users = response.json()
    assert any(user["id"] == user_id for user in users)

    # Get user by ID
    response = api_client.get(f"{api_url}/api/v1/users/{user_id}")
    assert response.status_code == 200
    user = response.json()
    assert user["id"] == user_id
    assert user["email"] == email

    # Update user
    new_email = f"updated.{email}"
    response = api_client.put(
        f"{api_url}/api/v1/users/{user_id}",
        json={"email": new_email}
    )
    assert response.status_code == 200
    updated_user = response.json()
    assert updated_user["email"] == new_email

    # Delete user
    response = api_client.delete(f"{api_url}/api/v1/users/{user_id}")
    assert response.status_code == 200

    # Verify user is deleted
    response = api_client.get(f"{api_url}/api/v1/users/{user_id}")
    assert response.status_code == 404

def test_concurrent_user_creation(api_client, api_url, cleanup_users):
    """Test creating multiple users concurrently"""
    # Create multiple users
    users = []
    for i in range(3):
        email = f"concurrent.user.{i}.{int(time.time())}@example.com"
        response = api_client.post(
            f"{api_url}/api/v1/users/",
            json={"email": email}
        )
        assert response.status_code == 200
        user_data = response.json()
        users.append(user_data)
        cleanup_users.append(user_data["id"])

    # Verify all users exist
    response = api_client.get(f"{api_url}/api/v1/users/")
    assert response.status_code == 200
    all_users = response.json()
    for user in users:
        assert any(u["id"] == user["id"] for u in all_users)

def test_pagination(api_client, api_url, cleanup_users):
    """Test user listing pagination"""
    # Create 5 users
    created_users = []
    for i in range(5):
        email = f"page.user.{i}.{int(time.time())}@example.com"
        response = api_client.post(
            f"{api_url}/api/v1/users/",
            json={"email": email}
        )
        assert response.status_code == 200
        user_data = response.json()
        created_users.append(user_data)
        cleanup_users.append(user_data["id"])

    # Test first page (2 users)
    response = api_client.get(f"{api_url}/api/v1/users/", params={"limit": 2, "skip": 0})
    assert response.status_code == 200
    page1 = response.json()
    assert len(page1) == 2

    # Test second page (2 users)
    response = api_client.get(f"{api_url}/api/v1/users/", params={"limit": 2, "skip": 2})
    assert response.status_code == 200
    page2 = response.json()
    assert len(page2) == 2

    # Verify no duplicate users between pages
    page1_ids = {user["id"] for user in page1}
    page2_ids = {user["id"] for user in page2}
    assert not page1_ids.intersection(page2_ids)

def test_api_key_validation(api_url):
    """Test API key security"""
    # Try without API key
    response = requests.get(f"{api_url}/api/v1/users/")
    assert response.status_code == 403

    # Try with invalid API key
    headers = {"X-API-Key": "invalid_key"}
    response = requests.get(f"{api_url}/api/v1/users/", headers=headers)
    assert response.status_code == 403

def test_error_handling(api_client, api_url):
    """Test API error handling"""
    # Test invalid user ID
    response = api_client.get(f"{api_url}/api/v1/users/999999")
    assert response.status_code == 404

    # Test invalid email format
    response = api_client.post(
        f"{api_url}/api/v1/users/",
        json={"email": "invalid_email"}
    )
    assert response.status_code in [400, 422]  # FastAPI validation error

    # Test missing required field
    response = api_client.post(
        f"{api_url}/api/v1/users/",
        json={}
    )
    assert response.status_code in [400, 422] 