#!/usr/bin/env python3
"""Safe version bumper: exact-token replacement only, syntax-checked.

Usage: python3 scripts/bump-version.py OLD NEW
Example: python3 scripts/bump-version.py 0.3.7b 0.3.8b

Rules enforced:
- replaces the bare token (never eats surrounding quotes/prefixes),
- refuses to run if any replacement breaks Python syntax,
- reports every touched file.
"""
import ast
import re
import sys

FILES = [
    "backend/__init__.py",
    "pyproject.toml",
    "packaging/rpm/athan-five-times.spec",
    "packaging/arch/PKGBUILD",
    "backend/location.py",
    "README.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
]


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: bump-version.py OLD NEW")
        return 2
    old, new = sys.argv[1], sys.argv[2]
    # bare token bounded by non-version chars (never touches quotes/prefix)
    pat = re.compile(r"(?<![\d.])" + re.escape(old) + r"(?![\db.])")
    touched = []
    for f in FILES:
        try:
            s = open(f, encoding="utf-8").read()
        except OSError:
            continue
        if not pat.search(s):
            continue
        s2 = pat.sub(new, s)
        if f.endswith(".py"):
            ast.parse(s2)  # refuse to write broken syntax
        open(f, "w", encoding="utf-8").write(s2)
        touched.append(f)
    if not touched:
        print("no occurrences — nothing changed")
        return 1
    print("bumped", old, "->", new, "in:", ", ".join(touched))
    return 0


if __name__ == "__main__":
    sys.exit(main())
