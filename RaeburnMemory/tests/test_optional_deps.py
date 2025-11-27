import pytest

pytestmark = pytest.mark.requires("sentence_transformers", "qdrant_client")


def test_sentence_transformers_importable():
    from sentence_transformers import SentenceTransformer

    assert SentenceTransformer is not None


def test_qdrant_client_importable():
    from qdrant_client import QdrantClient

    assert QdrantClient is not None
