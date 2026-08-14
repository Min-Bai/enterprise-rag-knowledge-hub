import pytest

from backend.app.services.retrieval_evaluation import (
    ExpectedChunk,
    RetrievalEvaluationCase,
    evaluate_retrieval_results,
)


def make_case() -> RetrievalEvaluationCase:
    return RetrievalEvaluationCase(
        name="leave-policy",
        question="How many leave days are available?",
        user_id=1,
        document_ids=[8],
        expected_chunks=[ExpectedChunk(document_id=8, page=4)],
    )


def test_evaluation_reports_recall_and_mrr_at_k():
    report = evaluate_retrieval_results(
        [make_case(), make_case()],
        [
            [{"document_id": 8, "chunk_index": 1, "page": 2}, {"document_id": 8, "chunk_index": 2, "page": 4}],
            [{"document_id": 9, "chunk_index": 1, "page": 4}],
        ],
        k=3,
    )

    assert report["recall_at_k"] == 0.5
    assert report["mrr_at_k"] == 0.25
    assert report["failed_cases"] == ["leave-policy"]


def test_evaluation_can_match_an_exact_chunk():
    case = RetrievalEvaluationCase(
        name="policy",
        question="Question",
        user_id=1,
        document_ids=[8],
        expected_chunks=[ExpectedChunk(document_id=8, chunk_index=3)],
    )

    report = evaluate_retrieval_results(
        [case],
        [[{"document_id": 8, "chunk_index": 3, "page": 1}]],
        k=1,
    )

    assert report["recall_at_k"] == 1.0
    assert report["mrr_at_k"] == 1.0


def test_evaluation_rejects_invalid_k():
    with pytest.raises(ValueError, match="k must be greater than zero"):
        evaluate_retrieval_results([], [], k=0)
