from backend.app.request_context import get_request_id, reset_request_id, set_request_id


def test_request_id_context_is_scoped_and_resettable():
    token = set_request_id("request-123")

    assert get_request_id() == "request-123"

    reset_request_id(token)
    assert get_request_id() == "-"
