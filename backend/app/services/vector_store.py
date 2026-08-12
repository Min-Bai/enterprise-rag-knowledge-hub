from functools import lru_cache
from os import getenv
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from .knowledge import KnowledgeChunk, split_markdown_document


KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "knowledge"
COLLECTION_NAME = "project_knowledge"
EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
VECTOR_SIZE = 512


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=getenv("QDRANT_URL", "http://qdrant:6333"))


def load_knowledge_chunks() -> list[KnowledgeChunk]:
    chunks: list[KnowledgeChunk] = []
    for document in sorted(KNOWLEDGE_DIR.glob("*.md")):
        chunks.extend(split_markdown_document(document))
    return chunks


def rebuild_knowledge_index() -> int:
    client = get_qdrant_client()
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    )

    chunks = load_knowledge_chunks()
    if not chunks:
        return 0

    vectors = get_embedding_model().encode(
        [chunk.text for chunk in chunks],
        normalize_embeddings=True,
    )
    points = [
        models.PointStruct(
            id=str(
                uuid5(
                    NAMESPACE_URL,
                    f"{chunk.source}:{chunk.section}:{index}",
                )
            ),
            vector=vector.tolist(),
            payload={
                "text": chunk.text,
                "source": chunk.source,
                "section": chunk.section,
            },
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]
    client.upsert(collection_name=COLLECTION_NAME, points=points, wait=True)
    return len(points)


def search_knowledge(question: str, limit: int = 3) -> list[dict[str, object]]:
    vector = get_embedding_model().encode(
        question,
        normalize_embeddings=True,
    ).tolist()
    response = get_qdrant_client().query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        limit=limit,
        with_payload=True,
    )
    return [
        {
            "text": point.payload["text"],
            "source": point.payload["source"],
            "section": point.payload["section"],
            "score": point.score,
        }
        for point in response.points
    ]
