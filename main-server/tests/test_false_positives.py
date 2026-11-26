"""Unit tests verifying false-positive suppression for SQL Injection, Command Injection, and inline directives."""

from app.reviews.engine import scan_source_code


def test_parameterized_sql_dict_not_flagged():
    """Verify parameterized SQL query with dict parameter is not flagged as SQL injection."""
    code = 'db.execute("SELECT * FROM users WHERE id = :id", {"id": user_id})'
    findings = scan_source_code(code, file_path="app/db.py")
    assert len(findings) == 0, f"Expected 0 findings, got: {findings}"


def test_parameterized_sql_tuple_not_flagged():
    """Verify parameterized SQL query with tuple placeholder %s is not flagged."""
    code = 'cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))'
    findings = scan_source_code(code, file_path="app/db.py")
    assert len(findings) == 0, f"Expected 0 findings, got: {findings}"


def test_parameterized_sql_qmark_list_not_flagged():
    """Verify parameterized SQL query with list placeholder ? is not flagged."""
    code = 'cursor.execute("SELECT * FROM users WHERE id = ?", [user_id])'
    findings = scan_source_code(code, file_path="app/db.py")
    assert len(findings) == 0, f"Expected 0 findings, got: {findings}"


def test_parameterized_sql_methods_not_flagged():
    """Verify db.execute and cursor.execute with tuple/dict parameters are not flagged."""
    code_tuple = 'db.execute(sql, (param,))'
    assert len(scan_source_code(code_tuple, file_path="app/db.py")) == 0

    code_dict = 'db.execute(sql, {"param": param})'
    assert len(scan_source_code(code_dict, file_path="app/db.py")) == 0

    code_list = 'cursor.execute(sql, [param])'
    assert len(scan_source_code(code_list, file_path="app/db.py")) == 0


def test_sql_string_concat_with_params_not_flagged():
    """Verify multi-part SQL string concatenation with parameterized tuple argument is not flagged."""
    code = 'cursor.execute("SELECT id, name " + "FROM users WHERE id = %s", (user_id,))'
    findings = scan_source_code(code, file_path="app/db.py")
    assert len(findings) == 0, f"Expected 0 findings, got: {findings}"


def test_unparameterized_sql_injection_still_flagged():
    """Verify genuine SQL injection via string concatenation or f-strings is still flagged."""
    concat_code = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)'
    findings = scan_source_code(concat_code, file_path="app/db.py")
    assert len(findings) == 1
    assert findings[0]["cwe_id"] == "CWE-89"

    fstring_code = 'db.execute(f"SELECT * FROM users WHERE id = {user_id}")'
    findings2 = scan_source_code(fstring_code, file_path="app/db.py")
    assert len(findings2) == 1
    assert findings2[0]["cwe_id"] == "CWE-89"

    format_code = 'cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)'
    findings3 = scan_source_code(format_code, file_path="app/db.py")
    assert len(findings3) == 1
    assert findings3[0]["cwe_id"] == "CWE-89"


def test_command_injection_safe_arguments_not_flagged():
    """Verify shlex.quote and lists without shell=True are not flagged as command injection."""
    list_code = 'subprocess.run(["ls", "-la", user_input])'
    assert len(scan_source_code(list_code, file_path="app/cmd.py")) == 0

    shlex_subp = 'subprocess.run(f"echo {shlex.quote(user_input)}", shell=True)'
    assert len(scan_source_code(shlex_subp, file_path="app/cmd.py")) == 0

    shlex_os = 'os.system(f"cat {shlex.quote(file_path)}")'
    assert len(scan_source_code(shlex_os, file_path="app/cmd.py")) == 0


def test_command_injection_unsafe_still_flagged():
    """Verify unsafe command injection is still flagged."""
    unsafe_shell = 'subprocess.run(f"echo {user_input}", shell=True)'
    findings = scan_source_code(unsafe_shell, file_path="app/cmd.py")
    assert len(findings) == 1
    assert findings[0]["cwe_id"] == "CWE-78"

    unsafe_os = 'os.system("cat " + file_path)'
    findings2 = scan_source_code(unsafe_os, file_path="app/cmd.py")
    assert len(findings2) == 1
    assert findings2[0]["cwe_id"] == "CWE-78"


def test_developer_inline_suppression():
    """Verify # codesec-ignore and # codesec-ignore-next-line directives."""
    inline_code = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)  # codesec-ignore: CWE-89'
    assert len(scan_source_code(inline_code, file_path="app/db.py")) == 0

    nextline_code = """# codesec-ignore-next-line: CWE-89
cursor.execute("SELECT * FROM users WHERE id = " + user_id)"""
    assert len(scan_source_code(nextline_code, file_path="app/db.py")) == 0

    wildcard_inline = 'cursor.execute("SELECT * FROM users WHERE id = " + user_id)  # codesec-ignore: CWE-XXX'
    assert len(scan_source_code(wildcard_inline, file_path="app/db.py")) == 0

    wildcard_nextline = """# codesec-ignore-next-line: CWE-XXX
cursor.execute("SELECT * FROM users WHERE id = " + user_id)"""
    assert len(scan_source_code(wildcard_nextline, file_path="app/db.py")) == 0
