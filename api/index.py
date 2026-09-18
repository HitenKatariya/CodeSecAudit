"""Vercel serverless entrypoint for the Flask website.

Vercel invokes this file for every route (see vercel.json).
It re-exports the Flask app from website/app.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from website.app import app  # noqa: E402  (Flask app, Vercel serves `app`)
