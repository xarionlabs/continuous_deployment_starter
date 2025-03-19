from functools import wraps
from fastapi import HTTPException, Request
from starlette.status import HTTP_403_FORBIDDEN
import os

API_KEY = os.getenv("API_KEY")

def require_api_key(func):
    @wraps(func)
    async def wrapper(*args, request: Request, **kwargs):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != API_KEY:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail="Could not validate API key"
            )
        return await func(*args, request=request, **kwargs)
    return wrapper 