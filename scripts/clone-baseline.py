#!/usr/bin/env python3
"""Fresh pinned baseline checkout with bounded, private transport diagnostics."""
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit

ATTEMPTS = 3
TIMEOUT = 90


def classify(text):
    statuses = re.findall(r"<= Recv header: HTTP/\S+ (\d{3})", text)
    status = int(statuses[-1]) if statuses else None
    if status in (408, 429) or (status is not None and 500 <= status <= 599):
        return "http-transient", status, True
    if status is not None and status >= 400:
        return "http-permanent", status, False
    low = text.lower()
    if any(s in low for s in ("authentication failed", "could not read username", "repository not found")):
        return "authentication-or-repository", status, False
    if any(s in low for s in ("timed out", "could not resolve host", "failed to connect", "connection reset", "empty reply", "expected flush", "early eof", "rpc failed")):
        return "transport-or-protocol", status, True
    return "git-error", status, False


def run_git(args, env):
    command = ["git", *args]
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, errors="replace",
                               start_new_session=True)
    try:
        stdout, stderr = process.communicate(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        # Git's HTTP helper inherits the pipes; killing only Git can leave
        # communicate() waiting forever on that helper after the timeout.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.communicate()
        raise
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def checkout(destination):
    url = os.environ.get("BASELINE_REPO_URL", "")
    pin = os.environ.get("PINNED_COMMIT", "")
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", pin):
        print("FATAL: missing or invalid baseline commit pin", file=sys.stderr)
        return 2
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme == "https" and parsed.hostname and parsed.path not in ("", "/")
                 and not parsed.username and not parsed.password and not parsed.query
                 and not parsed.fragment and not any(c.isspace() or ord(c) < 32 for c in url))
        parsed.port
    except ValueError:
        valid = False
    if not valid:
        print("FATAL: invalid baseline URL", file=sys.stderr)
        return 2
    if destination.exists() or destination.is_symlink():
        print("FATAL: baseline destination already exists", file=sys.stderr)
        return 2
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_TRACE_CURL="1",
               GIT_TRACE_CURL_NO_DATA="1", GIT_TRACE_REDACT="1")
    for attempt in range(1, ATTEMPTS + 1):
        try:
            result = run_git(["clone", "--quiet", "--", url, str(destination)], env)
            if result.returncode == 0:
                break
            category, status, retry = classify(result.stderr)
        except subprocess.TimeoutExpired:
            category, status, retry = "timeout", None, True
        except OSError:
            category, status, retry = "git-unavailable", None, False
        # Never emit Git's text: URLs, credentials, headers and repository names
        # can appear even in nominally quiet failures. Only fixed categories escape.
        print(f"baseline clone attempt={attempt}/{ATTEMPTS} category={category} "
              f"http_status={status if status is not None else 'unknown'}", file=sys.stderr)
        if destination.exists():
            shutil.rmtree(destination)
        if not retry or attempt == ATTEMPTS:
            print("FATAL: baseline clone failed", file=sys.stderr)
            return 2
        time.sleep(attempt)
    try:
        result = run_git(["-C", str(destination), "checkout", "--quiet", "--detach", pin], env)
        if result.returncode != 0:
            raise ValueError("pin unavailable")
        head = run_git(["-C", str(destination), "rev-parse", "HEAD"], env)
        if head.returncode != 0 or not re.fullmatch(r"[0-9a-fA-F]{40}", head.stdout.strip()):
            raise ValueError("invalid checkout")
        if not head.stdout.strip().lower().startswith(pin.lower()):
            raise ValueError("wrong checkout")
    except (ValueError, OSError, subprocess.TimeoutExpired):
        shutil.rmtree(destination)
        print("FATAL: pinned baseline commit unavailable", file=sys.stderr)
        return 2
    print(f"baseline pinned checkout verified: {pin}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: clone-baseline.py DESTINATION", file=sys.stderr)
        sys.exit(2)
    sys.exit(checkout(Path(sys.argv[1])))
