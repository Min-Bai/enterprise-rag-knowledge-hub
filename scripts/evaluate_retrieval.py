"""Run a labeled retrieval dataset against the configured Qdrant collection."""

import argparse
from datetime import UTC, datetime
from hashlib import sha256
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


def build_report(
    *, dataset: Path, report: dict[str, object]
) -> dict[str, object]:
    return {
        **report,
        "dataset": dataset.name,
        "dataset_sha256": sha256(dataset.read_bytes()).hexdigest(),
        "generated_at": datetime.now(UTC).isoformat(),
    }


def check_thresholds(
    *,
    report: dict[str, object],
    min_recall_at_k: float | None,
    min_mrr_at_k: float | None,
) -> list[str]:
    failures: list[str] = []
    if min_recall_at_k is not None and float(report["recall_at_k"]) < min_recall_at_k:
        failures.append(
            f"recall_at_k {float(report['recall_at_k']):.4f} is below {min_recall_at_k:.4f}"
        )
    if min_mrr_at_k is not None and float(report["mrr_at_k"]) < min_mrr_at_k:
        failures.append(
            f"mrr_at_k {float(report['mrr_at_k']):.4f} is below {min_mrr_at_k:.4f}"
        )
    return failures


def write_report(*, output: Path, report: dict[str, object]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-recall-at-k", type=float)
    parser.add_argument("--min-mrr-at-k", type=float)
    args = parser.parse_args()

    for name, threshold in {
        "--min-recall-at-k": args.min_recall_at_k,
        "--min-mrr-at-k": args.min_mrr_at_k,
    }.items():
        if threshold is not None and not 0 <= threshold <= 1:
            parser.error(f"{name} must be between 0 and 1")

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
    report = build_report(
        dataset=args.dataset,
        report=evaluate_retrieval_results(cases, results, args.k),
    )
    if args.output:
        write_report(output=args.output, report=report)
    print(json.dumps(report, indent=2))

    failures = check_thresholds(
        report=report,
        min_recall_at_k=args.min_recall_at_k,
        min_mrr_at_k=args.min_mrr_at_k,
    )
    if failures:
        print("Retrieval quality gate failed: " + "; ".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
