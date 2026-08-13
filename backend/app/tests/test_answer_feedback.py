from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.services.answer_feedback import AnswerFeedbackNotFoundError, save_answer_feedback


def test_save_answer_feedback_updates_owned_assistant_message():
    message = SimpleNamespace(feedback=None, feedback_comment=None, feedback_at=None)
    db = Mock()
    db.scalar.return_value = message

    result = save_answer_feedback(
        message_id=9,
        user_id=1,
        feedback="helpful",
        comment="  Clear answer.  ",
        db=db,
    )

    assert result is message
    assert message.feedback == "helpful"
    assert message.feedback_comment == "Clear answer."
    assert message.feedback_at is not None
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(message)


def test_save_answer_feedback_rejects_non_owned_or_non_assistant_message():
    db = Mock()
    db.scalar.return_value = None

    with pytest.raises(AnswerFeedbackNotFoundError):
        save_answer_feedback(message_id=9, user_id=1, feedback="unhelpful", comment=None, db=db)
