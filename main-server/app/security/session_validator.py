"""Cryptographic session token format and entropy validator."""

import re

TOKEN_FORMAT_REGEX = re.compile(r"^[A-Za-z0-9_\-]{32,64}$")

def is_valid_session_token(token: str) -> bool:
    """Validate that the session token adheres to safe character set and minimum entropy."""
    if not token or not isinstance(token, str):
        return False
    return bool(TOKEN_FORMAT_REGEX.fullmatch(token.strip()))

def sanitize_session_token(raw_token: str) -> str:
    """Strip extraneous whitespace and validate session token."""
    cleaned = raw_token.strip() if raw_token else ""
    if not is_valid_session_token(cleaned):
        raise ValueError("Invalid session token format or insufficient entropy")
    return cleaned
