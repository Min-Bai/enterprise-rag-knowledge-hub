from unittest.mock import Mock

from backend.app.services.feedback_analytics import get_knowledge_base_feedback_summary


def test_feedback_summary_calculates_rate_and_recent_negative_examples():
    db = Mock()
    db.execute.side_effect = [
        Mock(one=lambda: (4, 3, 1)),
        Mock(all=lambda: [(9, "Leave policy answer", "Missing carry-over rules")]),
    ]

    summary = get_knowledge_base_feedback_summary(knowledge_base_id=3, db=db)

    assert summary["total_feedback"] == 4
    assert summary["helpful_count"] == 3
    assert summary["unhelpful_count"] == 1
    assert summary["helpful_rate"] == 0.75
    assert summary["recent_unhelpful"] == [{"message_id": 9, "answer": "Leave policy answer", "comment": "Missing carry-over rules"}]


def test_feedback_summary_handles_no_feedback():
    db = Mock()
    db.execute.side_effect = [Mock(one=lambda: (0, 0, 0)), Mock(all=lambda: [])]

    summary = get_knowledge_base_feedback_summary(knowledge_base_id=3, db=db)

    assert summary["helpful_rate"] is None
    assert summary["recent_unhelpful"] == []
