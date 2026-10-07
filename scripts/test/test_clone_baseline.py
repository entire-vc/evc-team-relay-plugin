#!/usr/bin/env python3
"""Transport fault controls for the pinned legal baseline acquisition path."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location("clone_baseline", Path(__file__).resolve().parents[1] / "clone-baseline.py")
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

PIN = "12345678"
HEAD = PIN + "0" * 32


class BaselineControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dest = Path(self.tmp.name) / "baseline"
        self.calls = []

    def invoke(self, failures=(), checkout_ok=True, head=HEAD, **values):
        failures = iter(failures)
        env = {"BASELINE_REPO_URL": "https://example.invalid/baseline.git", "PINNED_COMMIT": PIN, **values}
        def git(args, environment):
            self.calls.append(args)
            self.assertEqual(environment["GIT_TERMINAL_PROMPT"], "0")
            if args[0] == "clone":
                self.assertFalse(self.dest.exists(), "each attempt must discard the partial clone")
                self.dest.mkdir()
                error = next(failures, None)
                if isinstance(error, Exception):
                    raise error
                return subprocess.CompletedProcess(args, 128 if error else 0, "", error or "")
            if "checkout" in args:
                self.assertEqual(args[-1], PIN)
                return subprocess.CompletedProcess(args, 0 if checkout_ok else 128, "", "private failure detail")
            return subprocess.CompletedProcess(args, 0, head + "\n", "")
        output = io.StringIO()
        with patch.dict(os.environ, env, clear=True), patch.object(baseline, "run_git", side_effect=git), patch.object(baseline.time, "sleep") as sleep, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result = baseline.checkout(self.dest)
        return result, output.getvalue(), sleep

    def test_transient_http_failure_recovers_at_original_pin(self):
        rc, output, sleep = self.invoke(["<= Recv header: HTTP/2 503\nfatal: could not read Username for 'private-url'"])
        self.assertEqual(rc, 0)
        self.assertEqual(len([a for a in self.calls if a[0] == "clone"]), 2)
        self.assertIn("category=http-transient http_status=503", output)
        self.assertNotIn("private-url", output)
        sleep.assert_called_once_with(1)

    def test_protocol_failure_without_status_recovers(self):
        rc, output, _ = self.invoke(["fatal: expected flush after ref listing"])
        self.assertEqual(rc, 0)
        self.assertIn("category=transport-or-protocol http_status=unknown", output)

    def test_exhaustion_is_failure_and_discards_partial_destination(self):
        rc, output, sleep = self.invoke(["<= Recv header: HTTP/2 502"] * 3)
        self.assertEqual(rc, 2)
        self.assertEqual(len(self.calls), 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [1, 2])
        self.assertFalse(self.dest.exists())
        self.assertIn("attempt=3/3", output)

    def test_timeout_has_same_bounded_retry(self):
        rc, output, _ = self.invoke([subprocess.TimeoutExpired("git", 90)])
        self.assertEqual(rc, 0)
        self.assertIn("category=timeout", output)

    def test_timeout_terminates_git_helper_process_group(self):
        process = MagicMock(pid=123)
        process.communicate.side_effect = [subprocess.TimeoutExpired("git", 90), ("", "")]
        with patch.object(baseline.subprocess, "Popen", return_value=process) as spawn, patch.object(baseline.os, "killpg") as kill:
            with self.assertRaises(subprocess.TimeoutExpired):
                baseline.run_git(["clone"], {})
        self.assertTrue(spawn.call_args.kwargs["start_new_session"])
        kill.assert_called_once_with(123, baseline.signal.SIGKILL)

    def test_auth_or_missing_repository_is_not_retried(self):
        for status in (401, 403, 404):
            with self.subTest(status=status):
                self.calls.clear()
                rc, output, sleep = self.invoke([f"<= Recv header: HTTP/2 {status}\nfatal: expected flush"])
                self.assertEqual(rc, 2)
                self.assertEqual(len(self.calls), 1)
                sleep.assert_not_called()
                self.assertIn("category=http-permanent", output)

    def test_unknown_auth_challenge_does_not_guess_http_status(self):
        rc, output, sleep = self.invoke(["fatal: could not read Username for 'private-url'"])
        self.assertEqual(rc, 2)
        sleep.assert_not_called()
        self.assertIn("category=authentication-or-repository http_status=unknown", output)
        self.assertNotIn("private-url", output)

    def test_missing_or_invalid_pin_fails_before_network(self):
        for pin in ("", "HEAD", "not-a-pin"):
            with self.subTest(pin=pin):
                rc, _, _ = self.invoke(PINNED_COMMIT=pin)
                self.assertEqual(rc, 2)
                self.assertEqual(self.calls, [])

    def test_invalid_url_is_private_and_fails_before_network(self):
        for url in ("", "ssh://example.invalid/tree", "https://user:credential@example.invalid/tree", "https://example.invalid/tree?auth=credential", "https://example.invalid/tree\n"):
            with self.subTest(url=url):
                rc, output, _ = self.invoke(BASELINE_REPO_URL=url)
                self.assertEqual(rc, 2)
                self.assertEqual(self.calls, [])
                self.assertNotIn("credential", output)
                self.assertNotIn("example.invalid", output)

    def test_missing_pin_never_falls_back_to_head(self):
        rc, _, sleep = self.invoke(checkout_ok=False)
        self.assertEqual(rc, 2)
        self.assertFalse(self.dest.exists())
        self.assertEqual(len(self.calls), 2)
        sleep.assert_not_called()

    def test_unexpected_checkout_is_failure(self):
        rc, _, _ = self.invoke(head="a" * 40)
        self.assertEqual(rc, 2)
        self.assertFalse(self.dest.exists())

    def test_existing_destination_is_not_overwritten(self):
        self.dest.mkdir()
        marker = self.dest / "retained"
        marker.write_text("keep")
        rc, _, _ = self.invoke()
        self.assertEqual(rc, 2)
        self.assertEqual(marker.read_text(), "keep")
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
