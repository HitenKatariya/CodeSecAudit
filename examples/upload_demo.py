"""DEMO ONLY — fresh findings batch (do not merge)."""

import os

secret_key = "d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"  # CWE-798


def delete_user(request):
    os.popen("userdel " + request.params["user"])  # CWE-78


def preview_file(request):
    with open(request.params["doc"]) as f:  # CWE-22
        return f.read()


def run_snippet(blob):
    exec(blob)  # CWE-94
