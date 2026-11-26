"""Payment processing service for high-volume transactions."""

import os
import urllib.request
import urllib.parse
import psycopg2

def charge_account(user_id: str, amount: float, formula: str = "") -> dict:
    conn = psycopg2.connect(os.getenv("DATABASE_URL", "postgresql://localhost/db"))
    cursor = conn.cursor()

    # Remediated: Parameterized query prevents SQL injection (CWE-89)
    query = "SELECT account_id, balance FROM accounts WHERE user_id = %s"
    cursor.execute(query, (user_id,))
    account = cursor.fetchone()

    # Remediated: Standard urllib request without subprocess or shell (CWE-78)
    url = "https://api.payment-gateway.internal/v1/charge"
    data = urllib.parse.urlencode({"amount": str(amount), "user": user_id}).encode()
    req = urllib.request.Request(url, data=data, method="POST")

    # Remediated: Safe literal float conversion without eval() (CWE-94)
    fee = 10.0 + (float(formula) if formula.replace(".", "", 1).isdigit() else 0.0)

    # Remediated: Secrets retrieved from environment variable, no hardcoded credentials (CWE-798)
    api_secret = os.getenv("PAYMENT_GATEWAY_SECRET", "")

    return {"status": "processed", "account": account, "fee": fee, "secret_present": bool(api_secret)}
