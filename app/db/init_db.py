# app/db/init_db.py
import logging
from sqlalchemy import text
from app.db.session import engine
from app.db.base import Base
from pgvector.psycopg2 import register_vector

def init_extensions():
    # Register pgvector adapter (VERY IMPORTANT)
    conn = engine.raw_connection()
    try:
        register_vector(conn.connection)
    finally:
        conn.close()

    logging.info("pgvector adapter registered.")

    # Ensure pgvector extension exists
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    logging.info("pgvector extension ensured.")

    # Import models AFTER extension + adapter
    from app import models

    Base.metadata.create_all(bind=engine)
    logging.info("Database initialized (tables created if not exist).")
