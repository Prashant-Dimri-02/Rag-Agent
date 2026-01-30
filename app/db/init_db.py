# app/db/init_db.py
import logging
from sqlalchemy import text
from app.db.session import engine
from app.db.base import Base
from pgvector.psycopg2 import register_vector


def init_extensions():
    # 1️⃣ Ensure pgvector extension exists FIRST
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()

    logging.info("pgvector extension ensured.")

    # 2️⃣ Register pgvector adapter AFTER extension exists
    raw_conn = engine.raw_connection()
    try:
        register_vector(raw_conn.connection)
    finally:
        raw_conn.close()

    logging.info("pgvector adapter registered.")

    # 3️⃣ Import models AFTER extension ready
    from app import models

    logging.info("Database initialized (tables created if not exist).")
