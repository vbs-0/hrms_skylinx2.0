"""Report HTMX startup/reload patterns that can cause partial-page reload loops."""

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TAG_RE = re.compile(r"<[^>]*\bhx-trigger\s*=\s*([\"'])(?P<trigger>.*?)\1[^>]*>", re.I | re.S)
GET_RE = re.compile(r"\bhx-get\s*=\s*([\"'])(?P<target>.*?)\1", re.I | re.S)
URL_RE = re.compile(r"{%\s*url\s+['\"](?P<name>[^'\"]+)['\"]")
SKIP_PARTS = {
    ".git",
    ".venv",
    "venv",
    "build",
    "dist",
    "media",
    "node_modules",
    "staticfiles",
    "referance code",
    "referance hrms",
    "flutter-backups",
    "claude-session-backup",
}
SKIP_FILES = {"nav_response.html", "page_output.html", "response.html", "response_debug.html"}


def line_number(text, offset):
    return text.count("\n", 0, offset) + 1


def tracked_templates():
    result = subprocess.run(
        ["git", "ls-files", "--", "*.html"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for name in result.stdout.splitlines():
        path = Path(name)
        if path.name not in SKIP_FILES and not SKIP_PARTS.intersection(part.lower() for part in path.parts):
            yield ROOT / path


def endpoint(tag):
    match = URL_RE.search(tag)
    if match:
        return f"url:{match.group('name')}"
    match = GET_RE.search(tag)
    return match.group("target").strip() if match else "(no hx-get)"


def main():
    findings = []
    templates = sorted(tracked_templates())
    for path in templates:
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(ROOT)
        for match in TAG_RE.finditer(text):
            if "load" not in re.split(r"[\s,]+", match.group("trigger").lower()):
                continue
            tag = match.group(0)
            target = endpoint(tag)
            findings.append(("AUTO_LOAD", target, relative, line_number(text, match.start())))

        if "setTimeout" in text and re.search(r"(?:applyFilter.{0,300}\.click\s*\(|\.submit\s*\()", text, re.I | re.S):
            findings.append(("SCRIPTED_SUBMIT", "(template-local)", relative, 1))
        if "window.location.reload()" in text and any(
            event in text for event in ("htmx:afterSettle", "htmx:historyRestore", "pageshow")
        ):
            findings.append(("RELOAD_SELF_HEAL", "(global listener)", relative, text[: text.index("window.location.reload()")].count("\n") + 1))

    for kind, target, path, line in findings:
        print(f"{kind:18} {target:42} {path}:{line}")
    counts = {kind: sum(1 for finding in findings if finding[0] == kind) for kind in sorted({finding[0] for finding in findings})}
    print(f"\n{len(findings)} HTMX startup/reload patterns found across {len(templates)} tracked templates.")
    for kind, count in counts.items():
        print(f"{kind}: {count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
