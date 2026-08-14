import json

from scripts.evaluate_retrieval import build_report, check_thresholds, write_report


def test_report_records_the_dataset_identity_and_can_be_saved(tmp_path):
    dataset = tmp_path / "cases.json"
    dataset.write_text("[]\n", encoding="utf-8")

    report = build_report(
        dataset=dataset,
        report={"case_count": 1, "k": 3, "recall_at_k": 1.0, "mrr_at_k": 1.0},
    )
    output = tmp_path / "reports" / "baseline.json"
    write_report(output=output, report=report)

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["dataset"] == "cases.json"
    assert len(saved["dataset_sha256"]) == 64
    assert saved["generated_at"]


def test_quality_gate_reports_each_metric_below_its_threshold():
    failures = check_thresholds(
        report={"recall_at_k": 0.5, "mrr_at_k": 0.25},
        min_recall_at_k=0.8,
        min_mrr_at_k=0.3,
    )

    assert failures == [
        "recall_at_k 0.5000 is below 0.8000",
        "mrr_at_k 0.2500 is below 0.3000",
    ]


def test_quality_gate_accepts_results_that_meet_the_thresholds():
    assert check_thresholds(
        report={"recall_at_k": 0.8, "mrr_at_k": 0.3},
        min_recall_at_k=0.8,
        min_mrr_at_k=0.3,
    ) == []
