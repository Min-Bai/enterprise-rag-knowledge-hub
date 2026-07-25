import pytest
from pydantic import ValidationError

from python_practice.day57.schemas.ai import AssistantRequest, ListMyOpenTasksArgs


def test_assistant_request_strips_message():
    request = AssistantRequest(message="  List my tasks  ")

    assert request.message == "List my tasks"


def test_assistant_request_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        AssistantRequest(message="List my tasks", user_id=99)


def test_list_my_open_tasks_args_limits_result_size():
    assert ListMyOpenTasksArgs().limit == 5

    with pytest.raises(ValidationError):
        ListMyOpenTasksArgs(limit=11)
