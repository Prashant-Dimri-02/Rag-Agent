# app/services/vector_search.py

from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam
from pgvector.sqlalchemy import Vector


def search_similar_chunks(db: Session, query_embedding, top_k: int = 5):
    sql = (
        text("""
            SELECT text_content
            FROM file_embeddings
            ORDER BY embedding <=> :embedding
            LIMIT :k
        """)
        .bindparams(
            bindparam("embedding", type_=Vector(1536)),  # ✅ only this matters
        )
    )

    result = db.execute(
        sql,
        {
            "embedding": query_embedding,
            "k": top_k,  # plain int is fine
        }
    )

    return [row[0] for row in result.fetchall()]
