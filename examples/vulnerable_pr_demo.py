"""DEMO ONLY — intentional vulnerabilities to showcase the CodeSecAudit PR bot.

Do not merge to main. Each function below should trigger one bot finding.
"""

import hashlib
import os
import sqlite3

HARDCODED_API_KEY = "sk-live-9f2c7a1b4d8e0f3a6c9e2b5d8f1a4c7e"  # CWE-798


def get_user(user_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)  # CWE-89
    return cursor.fetchone()


def run_command(cmd):
    os.system(cmd)  # CWE-78


def render_user_input(user_input):
    return eval(user_input)  # CWE-94


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()  # CWE-328
