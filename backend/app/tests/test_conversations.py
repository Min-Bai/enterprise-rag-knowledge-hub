from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from backend.app.services import conversations


def test_get_or_create_conversation_creates_for_current_document():
    db = Mock()

    conversation = conversations.get_or_create_conversation_service(
        conversation_id=None,
        user_id=1,
        document_id=8,
        db=db,
    )

    assert conversation.user_id == 1
    assert conversation.document_id == 8
    db.add.assert_called_once_with(conversation)
    db.flush.assert_called_once()


def test_get_or_create_conversation_reuses_owned_document_conversation(monkeypatch):
    conversation = SimpleNamespace(id=4)
    get_conversation = Mock(return_value=conversation)
    monkeypatch.setattr(
        conversations,
        "get_conversation_service",
        get_conversation,
    )

    result = conversations.get_or_create_conversation_service(
        conversation_id=4,
        user_id=1,
        document_id=8,
        db=Mock(),
    )

    assert result is conversation
    get_conversation.assert_called_once()


def test_delete_conversation_removes_only_the_current_users_conversation():
    db = Mock()
    conversation = SimpleNamespace(id=4, user_id=1)
    db.scalar.return_value = conversation

    conversations.delete_conversation_service(
        conversation_id=4,
        user_id=1,
        db=db,
    )

    db.delete.assert_called_once_with(conversation)
    db.commit.assert_called_once()


def test_delete_conversation_rejects_a_missing_or_other_users_conversation():
    db = Mock()
    db.scalar.return_value = None

    with pytest.raises(conversations.ConversationNotFoundError):
        conversations.delete_conversation_service(
            conversation_id=4,
            user_id=1,
            db=db,
        )

    db.delete.assert_not_called()
    db.commit.assert_not_called()


def test_get_conversation_history_limits_messages_to_six():
    db = Mock()
    messages = [
        SimpleNamespace(role="user", content=f"message {index}")
        for index in range(6, 0, -1)
    ]
    db.scalars.return_value.all.return_value = messages

    history = conversations.get_conversation_history(
        conversation_id=4,
        db=db,
    )

    assert history == [
        {"role": "user", "content": "message 1"},
        {"role": "user", "content": "message 2"},
        {"role": "user", "content": "message 3"},
        {"role": "user", "content": "message 4"},
        {"role": "user", "content": "message 5"},
        {"role": "user", "content": "message 6"},
    ]


def test_get_or_create_conversation_does_not_bypass_not_found_error(monkeypatch):
    monkeypatch.setattr(
        conversations,
        "get_conversation_service",
        Mock(side_effect=conversations.ConversationNotFoundError),
    )

    with pytest.raises(conversations.ConversationNotFoundError):
        conversations.get_or_create_conversation_service(
            conversation_id=4,
            user_id=1,
            document_id=8,
            db=Mock(),
        )


def test_get_or_create_knowledge_base_conversation_creates_scoped_conversation():
    db = Mock()

    conversation = conversations.get_or_create_knowledge_base_conversation_service(
        conversation_id=None,
        user_id=1,
        knowledge_base_id=3,
        db=db,
    )

    assert conversation.user_id == 1
    assert conversation.knowledge_base_id == 3
    assert conversation.document_id is None
    db.add.assert_called_once_with(conversation)
