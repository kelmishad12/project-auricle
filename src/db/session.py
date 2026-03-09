"""
Database session management.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Expect DATABASE_URL like: postgresql://user:password@localhost:5432/auricle
DATABASE_URL = os.environ.get("DATABASE_URL",
                              "postgresql://user:password@localhost/auricle")

engine = create_engine(DATABASE_URL)
# pylint: disable=invalid-name
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency to yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
