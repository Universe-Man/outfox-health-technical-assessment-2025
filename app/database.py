from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "postgres")
DB_HOST = os.getenv("POSTGRES_HOST", "db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# async_engine = create_async_engine(DATABASE_URL, echo=True)
# AsyncSessionLocal = sessionmaker(
#     bind=engine, class_=AsyncSession, expire_on_commit=False
# )
