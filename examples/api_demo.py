"""DEMO ONLY — small batch to retest the PR bot (do not merge)."""

import hashlib

import requests

api_token = "ghp_9f2c7a1b4d8e0f3a6c9e2b5d8f1a4c7e0f3a6"  # CWE-798


def run_transform(name):
    exec("transform_" + name)  # CWE-94


def legacy_checksum(data):
    return hashlib.sha1(data).hexdigest()  # CWE-328


def load_template(request):
    with open(request.params["template"]) as f:  # CWE-22
        return f.read()


def fetch_feed(request):
    return requests.post(request.params["feed"])  # CWE-918
