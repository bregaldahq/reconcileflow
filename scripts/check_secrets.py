"""Reject common committed credential formats without reading ignored dependency trees."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "coverage",
    "dist",
    "node_modules",
    "playwright-report",
    "test-results",
}
TEXT_SUFFIXES = {
    ".cmd",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{30,}\b"),
    "OpenAI secret": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}


def _candidate_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and not EXCLUDED_PARTS.intersection(path.relative_to(ROOT).parts)
        and (path.suffix.lower() in TEXT_SUFFIXES or path.name in {"Dockerfile", "Makefile"})
    ]


def main() -> int:
    problems: list[str] = []
    committed_environment_files = [
        path.name
        for path in ROOT.glob(".env*")
        if path.is_file() and not path.name.endswith(".example")
    ]
    for name in committed_environment_files:
        problems.append(f"{name} must remain uncommitted; use an .example file")
    for path in _candidate_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                problems.append(f"{label} pattern in {path.relative_to(ROOT)}")
    if problems:
        print("Credential-pattern scan failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"Credential-pattern scan passed ({len(_candidate_files())} text files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
