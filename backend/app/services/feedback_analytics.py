from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from ..models.conversation import ConversationMessageORM, ConversationORM
from ..models.document import DocumentORM


def get_knowledge_base_feedback_summary(*, knowledge_base_id: int, db: Session) -> dict[str, object]:
    scope = or_(
        ConversationORM.knowledge_base_id == knowledge_base_id,
        ConversationORM.document_id.in_(
            select(DocumentORM.id).where(DocumentORM.knowledge_base_id == knowledge_base_id)
        ),
    )
    counts = db.execute(
        select(
            func.count(ConversationMessageORM.id),
            func.coalesce(func.sum(case((ConversationMessageORM.feedback == "helpful", 1), else_=0)), 0),
            func.coalesce(func.sum(case((ConversationMessageORM.feedback == "unhelpful", 1), else_=0)), 0),
        )
        .join(ConversationORM, ConversationORM.id == ConversationMessageORM.conversation_id)
        .where(scope, ConversationMessageORM.role == "assistant", ConversationMessageORM.feedback.is_not(None))
    ).one()
    total, helpful, unhelpful = (int(value) for value in counts)
    recent_unhelpful = db.execute(
        select(ConversationMessageORM.id, ConversationMessageORM.content, ConversationMessageORM.feedback_comment)
        .join(ConversationORM, ConversationORM.id == ConversationMessageORM.conversation_id)
        .where(scope, ConversationMessageORM.role == "assistant", ConversationMessageORM.feedback == "unhelpful")
        .order_by(ConversationMessageORM.feedback_at.desc())
        .limit(10)
    ).all()
    return {
        "total_feedback": total,
        "helpful_count": helpful,
        "unhelpful_count": unhelpful,
        "helpful_rate": helpful / total if total else None,
        "recent_unhelpful": [
            {"message_id": message_id, "answer": content, "comment": comment}
            for message_id, content, comment in recent_unhelpful
        ],
    }
