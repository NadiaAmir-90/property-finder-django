from functools import lru_cache

from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(
        "sentence-transformers/all-MiniLM-L6-v2"
    )


def embed_text(text):
    """Convert text into a normalized 384-dimensional vector."""
    text = (text or "").strip()

    if not text:
        raise ValueError("Text cannot be empty.")

    model = get_embedding_model()

    vector = model.encode(
        text,
        normalize_embeddings=True,
    )

    return vector.tolist()