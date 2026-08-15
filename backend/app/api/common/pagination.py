import base64
import json
from datetime import datetime

from fastapi import HTTPException


def encode_cursor(*, created_at: datetime, item_id: int) -> str:
    payload = json.dumps({"created_at": created_at.isoformat(), "id": item_id}, separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
        created_at = datetime.fromisoformat(payload["created_at"])
        item_id = payload["id"]
        if not isinstance(item_id, int):
            raise ValueError
        return created_at, item_id
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail="invalid cursor") from exc
