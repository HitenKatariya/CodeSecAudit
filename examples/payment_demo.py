"""DEMO ONLY — fresh vulnerability batch for bot retest (do not merge)."""

import hashlib
import sqlite3
import subprocess

import requests

db_password = "Ch4ng3m3!"  # CWE-798


def get_order(order_id):
    conn = sqlite3.connect("shop.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders WHERE id = " + order_id)  # CWE-89
    return cursor.fetchone()


def ping_host(host):
    subprocess.Popen("ping " + host, shell=True)  # CWE-78


def load_plugin(request):
    exec(open(request.params["plugin"]).read())  # CWE-94 + CWE-22


def fetch_target(request):
    return requests.post(request.form["hook"])  # CWE-918
