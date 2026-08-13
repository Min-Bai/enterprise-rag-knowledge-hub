from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models.conversation import ConversationMessageORM, ConversationORM


MAX_HISTORY_MESSAGES = 6


class ConversationNotFoundError(Exception):
    pass


def get_conversation_service(
    *,
    conversation_id: int,
    user_id: int,
    document_id: int,
    db: Session,
) -> ConversationORM:
    conversation = db.scalar(
        select(ConversationORM).where(
            ConversationORM.id == conversation_id,
            ConversationORM.user_id == user_id,
            ConversationORM.document_id == document_id,
        )
    )
    if conversation is None:
        raise ConversationNotFoundError
    return conversation


def get_or_create_conversation_service(
    *,
    conversation_id: int | None,
    user_id: int,
    document_id: int,
    db: Session,
) -> ConversationORM:
    if conversation_id is not None:
        return get_conversation_service(
            conversation_id=conversation_id,
            user_id=user_id,
            document_id=document_id,
            db=db,
        )

    conversation = ConversationORM(user_id=user_id, document_id=document_id)
    db.add(conversation)
    db.flush()
    return conversation


def get_or_create_knowledge_base_conversation_service(
    *, conversation_id: int | None, user_id: int, knowledge_base_id: int, db: Session
) -> ConversationORM:
    if conversation_id is not None:
        conversation = db.scalar(select(ConversationORM).where(
            ConversationORM.id == conversation_id,
            ConversationORM.user_id == user_id,
            ConversationORM.knowledge_base_id == knowledge_base_id,
        ))
        if conversation is None:
            raise ConversationNotFoundError
        return conversation
    conversation = ConversationORM(user_id=user_id, knowledge_base_id=knowledge_base_id)
    db.add(conversation)
    db.flush()
    return conversation


def get_conversation_history(
    *,
    conversation_id: int,
    db: Session,
) -> list[dict[str, str]]:
    messages = db.scalars(
        select(ConversationMessageORM)
        .where(ConversationMessageORM.conversation_id == conversation_id)
        .order_by(ConversationMessageORM.id.desc())
        .limit(MAX_HISTORY_MESSAGES)
    ).all()
    return [
        {"role": message.role, "content": message.content}
        for message in reversed(messages)
    ]


def save_conversation_turn(
    *,
    conversation: ConversationORM,
    question: str,
    answer: str,
    sources: list[dict[str, object]],
    db: Session,
) -> None:
    conversation.updated_at = datetime.now(UTC)
    db.add_all(
        [
            ConversationMessageORM(
                conversation_id=conversation.id,
                role="user",
                content=question,
            ),
            ConversationMessageORM(
                conversation_id=conversation.id,
                role="assistant",
                content=answer,
                sources=sources,
            ),
        ]
    )
    db.commit()


def get_document_conversations_service(
    *,
    user_id: int,
    document_id: int,
    db: Session,
) -> list[ConversationORM]:
    return db.scalars(
        select(ConversationORM)
        .where(
            ConversationORM.user_id == user_id,
            ConversationORM.document_id == document_id,
        )
        .options(selectinload(ConversationORM.messages))
        .order_by(ConversationORM.updated_at.desc())
    ).all()


def get_knowledge_base_conversations_service(
    *, user_id: int, knowledge_base_id: int, db: Session
) -> list[ConversationORM]:
    return db.scalars(
        select(ConversationORM)
        .where(
            ConversationORM.user_id == user_id,
            ConversationORM.knowledge_base_id == knowledge_base_id,
        )
        .options(selectinload(ConversationORM.messages))
        .order_by(ConversationORM.updated_at.desc())
    ).all()
