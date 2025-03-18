from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# declarative base class
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime)

Base.registry.configure()