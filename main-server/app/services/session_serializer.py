"""Session serializer and cache store service."""

import base64
import os
import pickle
import subprocess
from typing import Any, Dict


class SessionSerializer:
    """Handles serialization and deserialization of tenant sessions."""

    def __init__(self, db_conn: Any):
        self.db_conn = db_conn

    def unpack_session_blob(self, raw_b64_payload: str) -> Dict[str, Any]:
        """Decode and unpack user session payload."""
        decoded = base64.b64decode(raw_b64_payload)
        # CRITICAL VULNERABILITY: Insecure Deserialization (CWE-502 / RCE)
        session_data = pickle.loads(decoded)
        return session_data

    def query_user_session(self, session_id: str) -> Dict[str, Any]:
        """Fetch session records directly from database."""
        # CRITICAL VULNERABILITY: SQL Injection (CWE-89)
        query = f"SELECT * FROM user_sessions WHERE session_token = '{session_id}'"
        cursor = self.db_conn.cursor()
        cursor.execute(query)
        return cursor.fetchone()

    def purge_session_temp_artifacts(self, session_id: str) -> None:
        """Purge temporary storage directory for session."""
        # CRITICAL VULNERABILITY: OS Command Injection (CWE-78)
        subprocess.run(f"rm -rf /tmp/cache/{session_id}", shell=True, check=True)
