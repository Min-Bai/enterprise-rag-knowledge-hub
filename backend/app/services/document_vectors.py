from collections import Counter
from hashlib import blake2b
import re
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import models

from .document_parser import DocumentChunk
from .vector_store import VECTOR_SIZE, get_embedding_model, get_qdrant_client


DOCUMENT_COLLECTION_NAME = "user_documents"
DOCUMENT_LEXICAL_COLLECTION_NAME = "user_documents_lexical"
LEXICAL_VECTOR_NAME = "lexical"
BM25_K1 = 1.2
BM25_B = 0.75
BM25_AVERAGE_DOCUMENT_LENGTH = 180


def _lexical_terms(text: str) -> list[str]:
    """Tokenize CJK text as unigrams/bigrams and keep complete Latin words."""
    terms: list[str] = []
    for token in re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text.lower()):
        if token[0].isascii():
            terms.append(token)
        else:
            terms.extend(token)
            terms.extend(token[index : index + 2] for index in range(len(token) - 1))
    return terms


def _term_index(term: str) -> int:
    return int.from_bytes(blake2b(term.encode("utf-8"), digest_size=4).digest(), "big")


def build_document_lexical_vector(text: str, *, is_query: bool = False) -> models.SparseVector:
    terms = _lexical_terms(text)
    if not terms:
        return models.SparseVector(indices=[], values=[])
    frequencies = Counter(terms)
    document_length = max(len(terms), 1)
    values_by_index: dict[int, float] = {}
    for term, frequency in frequencies.items():
        value = 1.0 if is_query else (
            frequency * (BM25_K1 + 1) /
            (frequency + BM25_K1 * (1 - BM25_B + BM25_B * document_length / BM25_AVERAGE_DOCUMENT_LENGTH))
        )
        index = _term_index(term)
        values_by_index[index] = max(values_by_index.get(index, 0.0), value)
    indices = sorted(values_by_index)
    return models.SparseVector(indices=indices, values=[values_by_index[index] for index in indices])


def ensure_document_collection() -> None:
    client = get_qdrant_client()

    if not client.collection_exists(DOCUMENT_COLLECTION_NAME):
        client.create_collection(
            collection_name=DOCUMENT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )
    if not client.collection_exists(DOCUMENT_LEXICAL_COLLECTION_NAME):
        client.create_collection(
            collection_name=DOCUMENT_LEXICAL_COLLECTION_NAME,
            vectors_config={},
            sparse_vectors_config={
                LEXICAL_VECTOR_NAME: models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                ),
            },
        )


def index_document_chunks(
    document_id: int,
    user_id: int | None,
    knowledge_base_id: int,
    tags: list[str] | None,
    chunks: list[DocumentChunk],
) -> None:
    if not chunks:
        raise ValueError("document has no text chunks")

    ensure_document_collection()

    client = get_qdrant_client()

    # 同一文档重试时，先清理旧向量，避免重复。
    document_filter = models.Filter(
        must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id))],
    )
    for collection_name in (DOCUMENT_COLLECTION_NAME, DOCUMENT_LEXICAL_COLLECTION_NAME):
        client.delete(
            collection_name=collection_name,
            points_selector=models.FilterSelector(filter=document_filter),
            wait=True,
        )

    vectors = get_embedding_model().encode(
        [chunk.text for chunk in chunks],
        normalize_embeddings=True,
    )

    points = [
        models.PointStruct(
            id=str(uuid5(NAMESPACE_URL, f"document:{document_id}:chunk:{index}")),
            vector=vector.tolist(),
            payload={
                "document_id": document_id,
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id,
                "tags": tags or [],
                "chunk_index": index,
                "page": chunk.page,
                "text": chunk.text,
            },
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
    ]

    client.upsert(
        collection_name=DOCUMENT_COLLECTION_NAME,
        points=points,
        wait=True,
    )
    lexical_points = [
        models.PointStruct(
            id=str(uuid5(NAMESPACE_URL, f"document:{document_id}:chunk:{index}")),
            vector={LEXICAL_VECTOR_NAME: build_document_lexical_vector(chunk.text)},
            payload=point.payload,
        )
        for index, (chunk, point) in enumerate(zip(chunks, points, strict=True))
    ]
    client.upsert(
        collection_name=DOCUMENT_LEXICAL_COLLECTION_NAME,
        points=lexical_points,
        wait=True,
    )

def delete_document_vectors(
    document_id: int,
    user_id: int,
) -> None:
    client = get_qdrant_client()

    document_filter = models.Filter(
        must=[
            models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)),
            models.FieldCondition(key="document_id", match=models.MatchValue(value=document_id)),
        ],
    )
    for collection_name in (DOCUMENT_COLLECTION_NAME, DOCUMENT_LEXICAL_COLLECTION_NAME):
        if client.collection_exists(collection_name):
            client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(filter=document_filter),
                wait=True,
            )


def _point_to_hit(point) -> dict[str, object]:
    return {
        "document_id": point.payload["document_id"],
        "chunk_index": point.payload["chunk_index"],
        "page": point.payload.get("page"),
        "text": point.payload["text"],
        "score": point.score,
    }


def _rrf_fuse(*ranked_hits: list[dict[str, object]], limit: int) -> list[dict[str, object]]:
    fused: dict[tuple[int, int], dict[str, object]] = {}
    scores: dict[tuple[int, int], float] = {}
    for hits in ranked_hits:
        for rank, hit in enumerate(hits, start=1):
            key = (int(hit["document_id"]), int(hit["chunk_index"]))
            fused[key] = hit
            scores[key] = scores.get(key, 0.0) + 1 / (60 + rank)
    maximum_rrf_score = len(ranked_hits) / 61
    return [
        {**fused[key], "score": min(scores[key] / maximum_rrf_score, 1.0)}
        for key in sorted(scores, key=lambda item: scores[item], reverse=True)[:limit]
    ]

def search_document_chunks(
    question: str,
    user_id: int | None,
    document_ids: list[int],
    limit: int = 3,
    knowledge_base_id: int | None = None,
    tags: list[str] | None = None,
) -> list[dict[str, object]]:
    if not document_ids:
        return []

    ensure_document_collection()

    vector = get_embedding_model().encode(
        question,
        normalize_embeddings=True,
    ).tolist()

    conditions = [
        models.FieldCondition(
            key="document_id",
            match=models.MatchAny(any=document_ids),
        ),
    ]
    if user_id is not None:
        conditions.insert(0, models.FieldCondition(key="user_id", match=models.MatchValue(value=user_id)))
    if tags:
        conditions.append(models.FieldCondition(key="tags", match=models.MatchAny(any=tags)))
    candidate_limit = max(limit * 4, 20)
    query_filter = models.Filter(must=conditions)
    client = get_qdrant_client()
    dense_response = client.query_points(
        collection_name=DOCUMENT_COLLECTION_NAME,
        query=vector,
        query_filter=query_filter,
        limit=candidate_limit,
        with_payload=True,
    )
    dense_hits = [_point_to_hit(point) for point in dense_response.points]
    if not client.collection_exists(DOCUMENT_LEXICAL_COLLECTION_NAME):
        return dense_hits
    lexical_response = client.query_points(
        collection_name=DOCUMENT_LEXICAL_COLLECTION_NAME,
        query=build_document_lexical_vector(question, is_query=True),
        using=LEXICAL_VECTOR_NAME,
        query_filter=query_filter,
        limit=candidate_limit,
        with_payload=True,
    )
    lexical_hits = [_point_to_hit(point) for point in lexical_response.points]
    return _rrf_fuse(dense_hits, lexical_hits, limit=limit)
