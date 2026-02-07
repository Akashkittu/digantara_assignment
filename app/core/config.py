import os

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Create a .env file with DATABASE_URL=...")

# For SQLAlchemy/Alembic: convert psycopg URL format
if DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
else:
    SQLALCHEMY_DATABASE_URL = DATABASE_URL
