from types import SimpleNamespace
from unittest.mock import Mock

from backend.app.services import document_vectors


def test_lexical_vector_supports_chinese_terms_and_is_stably_ordered():
    vector = document_vectors.build_document_lexical_vector("员工 年假 leave policy")

    assert vector.indices == sorted(vector.indices)
    assert len(vector.indices) >= 5
    assert all(value > 0 for value in vector.values)


def test_query_lexical_vector_uses_binary_query_weights():
    vector = document_vectors.build_document_lexical_vector("年假 年假", is_query=True)

    assert set(vector.values) == {1.0}


def test_document_search_fuses_dense_and_lexical_candidates(monkeypatch):
    point = SimpleNamespace(
        payload={"document_id": 9, "chunk_index": 2, "page": 4, "text": "员工每年享有年假。"},
        score=0.91,
    )
    client = Mock()
    client.collection_exists.return_value = True
    client.query_points.side_effect = [SimpleNamespace(points=[point]), SimpleNamespace(points=[point])]
    embedding = Mock()
    embedding.encode.return_value = SimpleNamespace(tolist=lambda: [0.1, 0.2])
    monkeypatch.setattr(document_vectors, "get_qdrant_client", lambda: client)
    monkeypatch.setattr(document_vectors, "get_embedding_model", lambda: embedding)

    hits = document_vectors.search_document_chunks(
        question="年假有几天",
        user_id=None,
        document_ids=[9],
        limit=3,
        tags=["人事"],
    )

    assert hits[0] | {"score": 0.0} == {"document_id": 9, "chunk_index": 2, "page": 4, "text": "员工每年享有年假。", "score": 0.0}
    assert hits[0]["score"] == 1.0
    assert client.query_points.call_count == 2
    assert client.query_points.call_args_list[0].kwargs["limit"] == 20
    assert client.query_points.call_args.kwargs["collection_name"] == document_vectors.DOCUMENT_LEXICAL_COLLECTION_NAME
    assert client.query_points.call_args.kwargs["using"] == document_vectors.LEXICAL_VECTOR_NAME


def test_rrf_fusion_promotes_chunks_returned_by_both_retrievers():
    dense = [
        {"document_id": 1, "chunk_index": 0, "page": None, "text": "semantic", "score": 0.9},
        {"document_id": 2, "chunk_index": 0, "page": None, "text": "dense only", "score": 0.8},
    ]
    lexical = [
        {"document_id": 3, "chunk_index": 0, "page": None, "text": "lexical only", "score": 4.2},
        {"document_id": 1, "chunk_index": 0, "page": None, "text": "semantic", "score": 3.7},
    ]

    fused = document_vectors._rrf_fuse(dense, lexical, limit=3)

    assert fused[0]["document_id"] == 1
