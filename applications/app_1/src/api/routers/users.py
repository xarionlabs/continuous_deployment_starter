from datetime import datetime, UTC
from typing import List
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from data.db.connections import get_db
from data.db.models.User import User
from api.auth.decorators import require_api_key

router = APIRouter()

class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="User's email address")

@router.post("/users/", response_model=dict)
@require_api_key
async def create_user(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    db_user = User(email=user.email, created_at=datetime.now(UTC))
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "email": db_user.email, "created_at": db_user.created_at}

@router.get("/users/", response_model=List[dict])
@require_api_key
async def read_users(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = db.query(User).offset(skip).limit(limit).all()
    return [{"id": user.id, "email": user.email, "created_at": user.created_at} for user in users]

@router.get("/users/{user_id}", response_model=dict)
@require_api_key
async def read_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"id": db_user.id, "email": db_user.email, "created_at": db_user.created_at}

@router.put("/users/{user_id}", response_model=dict)
@require_api_key
async def update_user(user_id: int, user: UserCreate, request: Request, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.email = user.email
    db.commit()
    db.refresh(db_user)
    return {"id": db_user.id, "email": db_user.email, "created_at": db_user.created_at}

@router.delete("/users/{user_id}")
@require_api_key
async def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"} 