from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.conversation import ConversationMessageORM, ConversationORM


class AnswerFeedbackNotFoundError(Exception):
    pass


def save_answer_feedback(
    *, message_id: int, user_id: int, feedback: str, comment: str | None, db: Session
) -> ConversationMessageORM:
    message = db.scalar(
        select(ConversationMessageORM)
        .join(ConversationORM, ConversationORM.id == ConversationMessageORM.conversation_id)
        .where(
            ConversationMessageORM.id == message_id,
            ConversationMessageORM.role == "assistant",
            ConversationORM.user_id == user_id,
        )
    )
    if message is None:
        raise AnswerFeedbackNotFoundError
    message.feedback = feedback
    message.feedback_comment = comment.strip() if comment else None
    message.feedback_at = datetime.now(UTC)
    db.commit()
    db.refresh(message)
    return message
