"""ChromaDB persistent store with Chroma's built-in local ONNX MiniLM embeddings (no API quota)."""
from __future__ import annotations

import threading
from functools import lru_cache

from ..config import STATE_DIR

CHROMA_DIR = STATE_DIR / "chroma"
RULEBOOK = "rulebook"
COMMODITIES = "commodities"


_lock = threading.Lock()
_client = None


def client():
    """One Chroma client per process. Locked: two threads creating clients at once race inside Chroma."""
    global _client
    with _lock:
        if _client is None:
            import chromadb

            CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        return _client


@lru_cache(maxsize=1)
def embedder():
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

    return DefaultEmbeddingFunction()


def collection(name: str):
    return client().get_or_create_collection(name=name, embedding_function=embedder(),
                                             metadata={"hnsw:space": "cosine"})


def reset_collection(name: str):
    try:
        client().delete_collection(name)
    except Exception:  # noqa: BLE001
        pass
    return collection(name)
