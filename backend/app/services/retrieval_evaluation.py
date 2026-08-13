from dataclasses import dataclass


@dataclass(frozen=True)
class ExpectedChunk:
    document_id: int
    chunk_index: int | None = None
    page: int | None = None


@dataclass(frozen=True)
class RetrievalEvaluationCase:
    name: str
    question: str
    user_id: int
    document_ids: list[int]
    expected_chunks: list[ExpectedChunk]


def hit_matches_expected(hit: dict[str, object], expected: ExpectedChunk) -> bool:
    if int(hit["document_id"]) != expected.document_id:
        return False
    if expected.chunk_index is not None and int(hit["chunk_index"]) != expected.chunk_index:
        return False
    return expected.page is None or hit.get("page") == expected.page


def evaluate_retrieval_results(
    cases: list[RetrievalEvaluationCase],
    results: list[list[dict[str, object]]],
    k: int,
) -> dict[str, object]:
    if k <= 0:
        raise ValueError("k must be greater than zero")
    if len(cases) != len(results):
        raise ValueError("cases and results must have the same length")

    failures: list[str] = []
    reciprocal_ranks: list[float] = []
    for case, hits in zip(cases, results, strict=True):
        rank = next(
            (
                index
                for index, hit in enumerate(hits[:k], start=1)
                if any(hit_matches_expected(hit, expected) for expected in case.expected_chunks)
            ),
            None,
        )
        if rank is None:
            failures.append(case.name)
            reciprocal_ranks.append(0.0)
        else:
            reciprocal_ranks.append(1 / rank)

    total = len(cases)
    return {
        "case_count": total,
        "k": k,
        "recall_at_k": sum(rank > 0 for rank in reciprocal_ranks) / total if total else 0.0,
        "mrr_at_k": sum(reciprocal_ranks) / total if total else 0.0,
        "failed_cases": failures,
    }
