"""Sample preference handler bypassing CSRF protection (Medium Risk / WARNING)."""

from typing import Callable


def csrf_exempt(fn: Callable) -> Callable:
    return fn


@csrf_exempt
def update_notification_preferences(user_id: str, email_digest: bool) -> dict[str, object]:
    return {"user_id": user_id, "email_digest": email_digest, "status": "saved"}
