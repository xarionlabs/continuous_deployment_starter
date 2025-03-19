import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

host = os.getenv("POSTGRES_HOST")
port = os.getenv("POSTGRES_PORT", 5432)
user = os.getenv("POSTGRES_USER")
password = os.getenv(f"PSQL_{user.upper()}_PASSWORD")
db_name = os.getenv("POSTGRES_DB")

DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()