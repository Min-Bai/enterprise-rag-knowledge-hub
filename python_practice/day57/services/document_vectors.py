from uuid import NAMESPACE_URL, uuid5

from qdrant_client import models

from .vector_store import VECTOR_SIZE, get_embedding_model, get_qdrant_client


DOCUMENT_COLLECTION_NAME = "user_documents"


def ensure_document_collection() -> None:
    client = get_qdrant_client()

    if client.collection_exists(DOCUMENT_COLLECTION_NAME):
        return

    client.create_collection(
        collection_name=DOCUMENT_COLLECTION_NAME,
        vectors_config=models.VectorParams(
            size=VECTOR_SIZE,
            distance=models.Distance.COSINE,
        ),
    )


def index_document_chunks(
    document_id: int,
    user_id: int,
    chunks: list[str],
) -> None:
    if not chunks:
        raise ValueError("document has no text chunks")

    ensure_document_collection()

    client = get_qdrant_client()

    # 同一文档重试时，先清理旧向量，避免重复。
    client.delete(
        collection_name=DOCUMENT_COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    ),
                ],
            ),
        ),
        wait=True,
    )

    vectors = get_embedding_model().encode(
        chunks,
        normalize_embeddings=True,
    )

    points = [
        models.PointStruct(
            id=str(uuid5(NAMESPACE_URL, f"document:{document_id}:chunk:{index}")),
            vector=vector.tolist(),
            payload={
                "document_id": document_id,
                "user_id": user_id,
                "chunk_index": index,
                "text": chunk,
            },
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]

    client.upsert(
        collection_name=DOCUMENT_COLLECTION_NAME,
        points=points,
        wait=True,
    )

def delete_document_vectors(
    document_id: int,
    user_id: int,
) -> None:
    client = get_qdrant_client()

    if not client.collection_exists(DOCUMENT_COLLECTION_NAME):
        return

    client.delete(
        collection_name=DOCUMENT_COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    ),
                    models.FieldCondition(
                        key="document_id",
                        match=models.MatchValue(value=document_id),
                    ),
                ],
            ),
        ),
        wait=True,
    )

def search_document_chunks(
    question: str,
    user_id: int,
    document_ids: list[int],
    limit: int = 3,
) -> list[dict[str, object]]:
    if not document_ids:
        return []

    vector = get_embedding_model().encode(
        question,
        normalize_embeddings=True,
    ).tolist()

    response = get_qdrant_client().query_points(
        collection_name=DOCUMENT_COLLECTION_NAME,
        query=vector,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="user_id",
                    match=models.MatchValue(value=user_id),
                ),
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchAny(any=document_ids),
                ),
            ],
        ),
        limit=limit,
        with_payload=True,
    )

    return [
        {
            "document_id": point.payload["document_id"],
            "chunk_index": point.payload["chunk_index"],
            "text": point.payload["text"],
            "score": point.score,
        }
        for point in response.points
    ]