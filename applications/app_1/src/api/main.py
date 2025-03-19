from typing import Union

from fastapi import FastAPI
from api.routers import users

app = FastAPI()

app.include_router(users.router, prefix="/api/v1", tags=["users"])

@app.get("/")
def read_root():
    return {"Hello": "Worldxxyxssx"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
