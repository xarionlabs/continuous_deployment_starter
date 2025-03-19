from datetime import datetime, UTC
import pytest
from sqlalchemy.exc import IntegrityError

from data.db.models.User import User

def test_create_user(test_db):
    # Create a user
    user = User(email="test@example.com", created_at=datetime.now(UTC))
    test_db.add(user)
    test_db.commit()
    
    # Verify user was created
    db_user = test_db.query(User).first()
    assert db_user.email == "test@example.com"
    assert isinstance(db_user.created_at, datetime)
    assert db_user.id is not None

def test_create_user_without_email(test_db):
    # Attempt to create user without email
    user = User(created_at=datetime.now(UTC))
    test_db.add(user)
    
    # Should raise an error
    with pytest.raises(IntegrityError):
        test_db.commit()
    test_db.rollback()

def test_update_user(test_db):
    # Create a user
    user = User(email="old@example.com", created_at=datetime.now(UTC))
    test_db.add(user)
    test_db.commit()
    
    # Update email
    user.email = "new@example.com"
    test_db.commit()
    
    # Verify update
    updated_user = test_db.query(User).first()
    assert updated_user.email == "new@example.com"

def test_delete_user(test_db):
    # Create a user
    user = User(email="delete@example.com", created_at=datetime.now(UTC))
    test_db.add(user)
    test_db.commit()
    
    # Delete user
    test_db.delete(user)
    test_db.commit()
    
    # Verify deletion
    assert test_db.query(User).count() == 0 