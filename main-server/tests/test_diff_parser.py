"""Test diff splitting and added-line extraction used by the pr_agent integration."""

from app.reviews.diff_parser import extract_added_lines, split_diff_by_file

MULTI_FILE_DIFF = """diff --git a/app.py b/app.py
index e69de29..d95f3ad 100644
--- a/app.py
+++ b/app.py
@@ -1,3 +1,5 @@
 def handle_auth(token):
+    if not token:
+        raise ValueError("Token missing")
     return True
diff --git a/db.py b/db.py
index 1111111..2222222 100644
--- a/db.py
+++ b/db.py
@@ -10,2 +10,3 @@
 def run_query(user_id):
+    cursor.execute("SELECT * FROM users WHERE id = " + user_id)
     return cursor.fetchall()
"""


def test_split_diff_by_file():
    files = split_diff_by_file(MULTI_FILE_DIFF)
    assert set(files.keys()) == {"app.py", "db.py"}
    assert "handle_auth" in files["app.py"]
    assert "run_query" in files["db.py"]


def test_extract_added_lines():
    files = split_diff_by_file(MULTI_FILE_DIFF)
    added = extract_added_lines(files["app.py"])
    assert (2, '    if not token:') in added
    assert (3, '        raise ValueError("Token missing")') in added
    assert len(added) == 2
