#!/usr/bin/env python3
"""
Unit tests for the concurrent runner added to scripts/run_screen.py:
  - call_with_backoff / is_rate_limit_error (429/529 retry-then-give-up logic)
  - build_call_specs (interleaved design preserved, order_index unique 0..N-1)
  - an end-to-end mock run: --concurrency speedup, identical call-tuple sets,
    and --resume (kill mid-run, resume, no duplicates, complete set)

Usage:
    python3 -m unittest tests/test_concurrency.py -v
    python3 -m pytest tests/test_concurrency.py -v   # if pytest is installed
"""
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_screen import (  # noqa: E402
    RateLimitExhausted,
    build_call_specs,
    call_with_backoff,
    is_rate_limit_error,
    load_config,
    load_jds,
)

JDS = "synth-001,synth-002,synth-003"


class FakeStatusError(Exception):
    def __init__(self, msg, status_code):
        super().__init__(msg)
        self.status_code = status_code


class TestIsRateLimitError(unittest.TestCase):
    def test_status_code_429(self):
        self.assertTrue(is_rate_limit_error(FakeStatusError("nope", 429)))

    def test_status_code_529_overloaded(self):
        self.assertTrue(is_rate_limit_error(FakeStatusError("nope", 529)))

    def test_status_code_500_not_rate_limit(self):
        self.assertFalse(is_rate_limit_error(FakeStatusError("server error", 500)))

    def test_message_text_fallback(self):
        self.assertTrue(is_rate_limit_error(Exception("Error: rate limit exceeded, please slow down")))
        self.assertTrue(is_rate_limit_error(Exception("model overloaded, try again")))

    def test_unrelated_exception(self):
        self.assertFalse(is_rate_limit_error(Exception("invalid api key")))


class TestCallWithBackoff(unittest.TestCase):
    def test_succeeds_first_try_no_sleep(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            return "ok"

        start = time.monotonic()
        result = call_with_backoff(fn, max_tries=5, delays=(0, 0, 0, 0))
        elapsed = time.monotonic() - start
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 1)
        self.assertLess(elapsed, 0.1)

    def test_retries_then_succeeds(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise FakeStatusError("rate limited", 429)
            return "ok"

        result = call_with_backoff(fn, max_tries=5, delays=(0, 0, 0, 0))
        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)

    def test_exhausts_and_raises(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            raise FakeStatusError("still rate limited", 429)

        with self.assertRaises(RateLimitExhausted):
            call_with_backoff(fn, max_tries=5, delays=(0, 0, 0, 0))
        self.assertEqual(calls["n"], 5)

    def test_non_rate_limit_error_propagates_immediately(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            raise ValueError("invalid request: missing required field")

        with self.assertRaises(ValueError):
            call_with_backoff(fn, max_tries=5, delays=(0, 0, 0, 0))
        self.assertEqual(calls["n"], 1)  # no retry — fails fast on the first try


class TestBuildCallSpecs(unittest.TestCase):
    def test_order_index_unique_and_covers_full_range(self):
        cfg = load_config()
        jds = load_jds({"synth-001", "synth-002", "synth-003"})
        specs, _rng = build_call_specs(
            jds, cfg["models"], reps=3, ablation="institution_swap",
            resume_a_text="RESUME A", resume_b_text="RESUME B", seed=42,
        )
        n = len(jds) * len(cfg["models"]) * 3 * 2  # jds x models x reps x (A,B)
        self.assertEqual(len(specs), n)
        order_indices = sorted(s["order_index"] for s in specs)
        self.assertEqual(order_indices, list(range(n)))

    def test_same_seed_is_deterministic(self):
        cfg = load_config()
        jds = load_jds({"synth-001", "synth-002"})
        specs1, _ = build_call_specs(jds, cfg["models"], 2, "institution_swap", "A", "B", seed=7)
        specs2, _ = build_call_specs(jds, cfg["models"], 2, "institution_swap", "A", "B", seed=7)
        keys1 = [(s["jd"]["jd_id"], s["model_cfg"]["key"], s["condition"], s["rep"]) for s in specs1]
        keys2 = [(s["jd"]["jd_id"], s["model_cfg"]["key"], s["condition"], s["rep"]) for s in specs2]
        self.assertEqual(keys1, keys2)  # same seed -> identical interleaved order


def _run(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, env=env, timeout=60)


def _load_jsonl(path):
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _call_tuples(records):
    return {(r["jd_id"], r["model"], r["condition"], r["rep"]) for r in records}


class TestConcurrentRunEndToEnd(unittest.TestCase):
    """Runs the real script as a subprocess against a scratch results dir, so
    it exercises the actual CLI + ThreadPoolExecutor path, not just internals."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="screener-eval-test-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _run_screen(self, extra_args, out_dir=None, mock_latency="0"):
        import os
        env = os.environ.copy()
        env["MOCK_LATENCY"] = mock_latency
        cmd = [sys.executable, "scripts/run_screen.py", "--mock",
               "--jds", JDS] + extra_args
        if out_dir:
            cmd += ["--out-dir", str(out_dir)]
        result = _run(cmd, cwd=ROOT, env=env)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        return result

    def test_concurrency_speedup(self):
        out1 = self.tmp / "c1"
        out8 = self.tmp / "c8"
        t0 = time.monotonic()
        self._run_screen(["--reps", "2", "--ablation", "institution_swap", "--concurrency", "1"],
                          out_dir=out1, mock_latency="0.05")
        t1 = time.monotonic()
        self._run_screen(["--reps", "2", "--ablation", "institution_swap", "--concurrency", "8"],
                          out_dir=out8, mock_latency="0.05")
        t2 = time.monotonic()

        elapsed_c1 = t1 - t0
        elapsed_c8 = t2 - t1

        recs1 = _load_jsonl(out1 / "calls.jsonl")
        recs8 = _load_jsonl(out8 / "calls.jsonl")

        self.assertEqual(len(recs1), len(recs8))
        self.assertEqual(_call_tuples(recs1), _call_tuples(recs8))  # identical set of tuples
        # order_index unique 0..N-1 in both
        for recs in (recs1, recs8):
            ois = sorted(r["order_index"] for r in recs)
            self.assertEqual(ois, list(range(len(recs))))

        # concurrency=8 should be meaningfully faster — not asserting an exact
        # 8x (process/thread-pool overhead eats some of it), just a clear win.
        self.assertGreater(elapsed_c1 / elapsed_c8, 3.0,
                            msg=f"expected a clear speedup, got c1={elapsed_c1:.2f}s c8={elapsed_c8:.2f}s")

    def test_resume_after_truncation_no_duplicates_complete_set(self):
        out_dir = self.tmp / "resume-run"
        self._run_screen(["--reps", "2", "--ablation", "evidence_links", "--concurrency", "4"],
                          out_dir=out_dir)
        full = _load_jsonl(out_dir / "calls.jsonl")
        full_tuples = _call_tuples(full)
        self.assertGreater(len(full), 4)

        # Simulate the run being killed partway through: truncate calls.jsonl.
        calls_path = out_dir / "calls.jsonl"
        with open(calls_path) as f:
            lines = f.readlines()
        keep = max(1, len(lines) // 3)
        with open(calls_path, "w") as f:
            f.writelines(lines[:keep])

        run_id = out_dir.name
        result = _run(
            [sys.executable, "scripts/run_screen.py", "--resume", run_id,
             "--out-dir", str(out_dir), "--concurrency", "4"],
            cwd=ROOT,
        )
        resumed_records = _load_jsonl(calls_path)
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)

        resumed_tuples = _call_tuples(resumed_records)
        self.assertEqual(len(resumed_records), len(set(
            (r["jd_id"], r["model"], r["condition"], r["rep"], r["ts"]) for r in resumed_records
        )))  # no literal duplicate lines
        self.assertEqual(len(resumed_tuples), len(resumed_records))  # no duplicate tuples
        self.assertEqual(resumed_tuples, full_tuples)  # complete set, matching the original run


if __name__ == "__main__":
    unittest.main()
