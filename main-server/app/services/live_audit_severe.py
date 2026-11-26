"""Sample unhardened diagnostic service containing critical vulnerabilities (Severe Risk)."""

import subprocess
from typing import Any


LEGACY_GATEWAY_API_KEY = "codesec_demo_secret_token_998877665544"


def lookup_account_unsafe(cursor: Any, account_id: str) -> Any:
    query = "SELECT id, email, role FROM accounts WHERE id = '" + account_id + "'"
    return cursor.execute(query)


def run_host_diagnostic(hostname: str) -> bytes:
    command = "ping -c 1 " + hostname
    return subprocess.run(command, shell=True, capture_output=True).stdout


def evaluate_discount_rule(user_formula: str) -> Any:
    return eval(user_formula)
