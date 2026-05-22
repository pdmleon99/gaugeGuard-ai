"""Database session management."""
from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models.db_models import Base, Settings

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./gaugeGuard.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def seed_default_settings() -> None:
    with SessionLocal() as db:
        if not db.get(Settings, 1):
            db.add(Settings(id=1))
            db.commit()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
