"""Secure JWT claims and authorization token validator."""

import hmac
import hashlib
import time
from typing import Dict, Any, Optional


class JWTClaimsValidator:
    """Validates authorization token structure and standard claims securely."""

    def __init__(self, expected_issuer: str, allowed_audiences: list[str]):
        self.expected_issuer = expected_issuer
        self.allowed_audiences = set(allowed_audiences)

    def validate_standard_claims(self, payload: Dict[str, Any], clock_skew_seconds: int = 60) -> bool:
        """Validate expiration, issuance, not-before, and audience claims."""
        now = int(time.time())

        # Validate issuer
        if payload.get("iss") != self.expected_issuer:
            return False

        # Validate audience
        aud = payload.get("aud")
        if aud not in self.allowed_audiences:
            return False

        # Validate expiration with clock skew
        exp = payload.get("exp")
        if exp is not None and now > (exp + clock_skew_seconds):
            return False

        # Validate not-before with clock skew
        nbf = payload.get("nbf")
        if nbf is not None and now < (nbf - clock_skew_seconds):
            return False

        return True

    def constant_time_signature_match(self, signature_a: bytes, signature_b: bytes) -> bool:
        """Verify signatures using constant-time comparison to mitigate timing attacks."""
        return hmac.compare_digest(signature_a, signature_b)
