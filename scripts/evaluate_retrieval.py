"""Run a labeled retrieval dataset against the configured Qdrant collection."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services.document_vectors import search_document_chunks
from backend.app.services.retrieval_evaluation import (
    ExpectedChunk,
    RetrievalEvaluationCase,
    evaluate_retrieval_results,
)


def load_cases(path: Path) -> list[RetrievalEvaluationCase]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("evaluation dataset must be a JSON array")

    cases = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("each evaluation case must be an object")
        expected = item.get("expected_chunks")
        if not isinstance(expected, list) or not expected:
            raise ValueError("each evaluation case needs expected_chunks")
        cases.append(
            RetrievalEvaluationCase(
                name=str(item["name"]),
                question=str(item["question"]),
                user_id=int(item["user_id"]),
                document_ids=[int(document_id) for document_id in item["document_ids"]],
                expected_chunks=[
                    ExpectedChunk(
                        document_id=int(chunk["document_id"]),
                        chunk_index=int(chunk["chunk_index"]) if chunk.get("chunk_index") is not None else None,
                        page=int(chunk["page"]) if chunk.get("page") is not None else None,
                    )
                    for chunk in expected
                ],
            )
        )
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    results = [
        search_document_chunks(
            question=case.question,
            user_id=case.user_id,
            document_ids=case.document_ids,
            limit=args.k,
        )
        for case in cases
    ]
    print(json.dumps(evaluate_retrieval_results(cases, results, args.k), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
