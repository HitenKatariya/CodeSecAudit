"""Package the RAG service for Hugging Face Space deployment."""

import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist" / "huggingface-rag-space"
RAG_SRC = ROOT / "rag-service"

INCLUDE_TOP_FILES = [
    "Dockerfile",
    "requirements.txt",
]

INCLUDE_RAG_SERVICE = [
    "__init__.py",
    "main.py",
    "index.py",
    "schemas.py",
]

SPACE_FRONTMATTER = """---
title: CodeSecAudit RAG Service
emoji: \U0001f6e1\ufe0f
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

"""

FORBIDDEN_PATTERNS = [".env", "data/", "notebooks/", "release/", ".git"]


def clean_dist():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)


def copy_top_files():
    for fname in INCLUDE_TOP_FILES:
        src = RAG_SRC / fname
        dst = DIST / fname
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  copied {fname}")
        else:
            print(f"  WARNING: rag-service/{fname} not found")


def copy_readme():
    src = RAG_SRC / "README.md"
    body = src.read_text(encoding="utf-8") if src.exists() else "# CodeSecAudit RAG Service\n"
    (DIST / "README.md").write_text(SPACE_FRONTMATTER + body, encoding="utf-8")
    print("  wrote README.md (with Space front-matter)")


def copy_rag_service():
    rag_dst = DIST / "rag_service"
    rag_dst.mkdir(exist_ok=True)
    for fname in INCLUDE_RAG_SERVICE:
        src = RAG_SRC / "rag_service" / fname
        dst = rag_dst / fname
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  copied rag_service/{fname}")
        else:
            print(f"  WARNING: rag-service/rag_service/{fname} not found")


def verify():
    print()
    print("Verifying dist contents:")
    all_files = []
    for root, dirs, files in os.walk(str(DIST)):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, str(DIST)).replace(os.sep, "/")
            all_files.append(rel)

    expected = {
        "Dockerfile",
        "requirements.txt",
        "README.md",
        "rag_service/__init__.py",
        "rag_service/main.py",
        "rag_service/index.py",
        "rag_service/schemas.py",
    }

    missing = expected - set(all_files)
    extra = set(all_files) - expected

    if missing:
        print(f"  MISSING: {sorted(missing)}")
    if extra:
        print(f"  EXTRA: {sorted(extra)}")
    if not missing:
        print(f"  All {len(all_files)} files present, no missing files")

    # Tree output
    print()
    print("Dist tree:")
    for root, dirs, files in os.walk(str(DIST)):
        rel_root = os.path.relpath(root, str(DIST))
        indent = "  " if rel_root == "." else "  " + "  " * (rel_root.count(os.sep) + 1)
        if rel_root != ".":
            print(f"{indent}{os.path.basename(root)}/")
        for f in sorted(files):
            f_indent = "    " if rel_root == "." else "  " + "  " * (rel_root.count(os.sep) + 2)
            print(f"{f_indent}{f}")

    # Check forbidden files
    forbidden_found = False
    for f in all_files:
        for pattern in FORBIDDEN_PATTERNS:
            if f.startswith(pattern):
                print(f"  ERROR: forbidden file included: {f}")
                forbidden_found = True

    if forbidden_found:
        print("  ERROR: Forbidden files found in dist package!")
        return False

    return not missing


def main():
    print("Preparing Hugging Face Space package in dist/huggingface-rag-space/")
    print()
    clean_dist()
    copy_top_files()
    copy_readme()
    copy_rag_service()
    ok = verify()
    print()
    print("Done — package ready at dist/huggingface-rag-space/")
    if not ok:
        print("ERROR: Package verification failed!")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
