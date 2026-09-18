"""DEMO ONLY — intentional vulnerabilities to showcase the CodeSecAudit PR bot.

Do not merge to main. Each function below should trigger one bot finding
covering all 7 engine rules (CWE-94, CWE-89, CWE-78, CWE-328, CWE-798,
CWE-22, CWE-918).
"""

import hashlib
import os
import sqlite3
import subprocess

import requests

HARDCODED_API_KEY = "sk-live-9f2c7a1b4d8e0f3a6c9e2b5d8f1a4c7e"  # CWE-798
db_password = "Sup3rSecret!"  # CWE-798


def get_user(user_id):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = " + user_id)  # CWE-89
    return cursor.fetchone()


def search_users(request):
    query = "SELECT * FROM users WHERE name = '" + request.params["q"] + "'"  # CWE-89
    return query


def run_command(cmd):
    os.system(cmd)  # CWE-78


def backup_database(cmd):
    subprocess.run(cmd, shell=True)  # CWE-78


def render_user_input(user_input):
    return eval(user_input)  # CWE-94


def run_plugin_action(action):
    exec("do_" + action)  # CWE-94


def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()  # CWE-328


def file_checksum(data):
    return hashlib.sha1(data).hexdigest()  # CWE-328


def read_upload(request):
    data = open(request.params["file"])  # CWE-22
    return data.read()


def fetch_avatar(request):
    return requests.get(request.params["url"])  # CWE-918
