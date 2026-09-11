#!/usr/bin/env python3
"""
Main harness: run résumé A vs résumé B (one ablation at a time) through the
screening prompt, paired per JD per model.

Design (fixed, see README): for each rep -> shuffle JDs -> for each JD -> for
each model -> run A and B in random order. Everything in one run window so
conditions are interleaved, not run as separate batches (agent/index nondeterminism
should hit both conditions equally, not correlate with which condition ran first).

--mock returns deterministic fake scores (seeded by run inputs, not by wall clock)
so the full pipeline is testable with no API keys and no network.

Usage:
    python3 scripts/run_screen.py --mock --reps 3 --ablation institution_swap
    python3 scripts/run_screen.py --reps 5 --ablation evidence_links --jds synth-001,synth-002
"""
import argparse
import hashlib
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from rubric import build_messages  # noqa: E402

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass  # fine in --mock mode; real mode needs python-dotenv or exported env vars


def load_config():
    return yaml.safe_load((ROOT / "config" / "config.yaml").read_text())


def load_jds(jd_ids_filter=None):
    idx = yaml.safe_load((ROOT / "jds" / "index.yaml").read_text())["jds"]
    jds = []
    found_ids = set()
    for entry in idx:
        if jd_ids_filter and entry["jd_id"] not in jd_ids_filter:
            continue
        text_path = ROOT / "jds" / "text" / f"{entry['jd_id']}.txt"
        if not text_path.exists():
            print(f"WARNING: skipping {entry['jd_id']} — jds/text/{entry['jd_id']}.txt not found "
                  f"(real JD text is gitignored; a real run needs it collected first)", file=sys.stderr)
            continue
        jd = dict(entry)
        jd["text"] = text_path.read_text()
        actual_hash = hashlib.sha256(jd["text"].encode()).hexdigest()
        if entry.get("sha256") and entry["sha256"] != actual_hash:
            print(f"WARNING: {entry['jd_id']} text does not match recorded sha256 in index.yaml "
                  f"(file changed since indexing?)", file=sys.stderr)
        jds.append(jd)
        found_ids.add(entry["jd_id"])

    # Fallback for a JD id explicitly requested via --jds/--jd that isn't in the real
    # census in jds/index.yaml — this is how the synthetic placeholders (synth-001..003,
    # jds/text/synth-*.txt, committed for pipeline testing) are still reachable by id
    # (e.g. `make pilot-mock`) without cluttering the real JD index with fake entries.
    if jd_ids_filter:
        for jd_id in jd_ids_filter - found_ids:
            text_path = ROOT / "jds" / "text" / f"{jd_id}.txt"
            if not text_path.exists():
                continue
            text = text_path.read_text()
            employer, title = jd_id, jd_id
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("["):
                    if " — " in line:
                        employer, title = (p.strip() for p in line.split(" — ", 1))
                    break
            jds.append({
                "jd_id": jd_id,
                "employer": employer,
                "employer_class": "synthetic",
                "title": title,
                "text": text,
            })
    return jds


def resume_prefix(cfg=None) -> str:
    """Derive the résumé-variant filename prefix (e.g. "v4_2") from
    paths.resume_a in config.yaml (e.g. "resume/v4_2_A.txt")."""
    cfg = cfg or load_config()
    name = Path(cfg["paths"]["resume_a"]).name
    if not name.endswith("_A.txt"):
        raise ValueError(f"paths.resume_a ({name}) must end in '_A.txt'")
    return name[: -len("_A.txt")]


def resume_path_for(condition: str, ablation: str, cfg=None) -> Path:
    prefix = resume_prefix(cfg)
    if condition == "A":
        return ROOT / "resume" / f"{prefix}_A.txt"
    return ROOT / "resume" / f"{prefix}_B_{ablation}.txt"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Mock scoring — deterministic, no network. Simulates a plausible ablation
# effect so the analysis pipeline has non-trivial (but clearly fake) signal.
# ---------------------------------------------------------------------------

MOCK_ABLATION_EFFECT = {
    # condition B mean shift vs A, in fit_score points — pure fiction, tuned only
    # so the mock end-to-end run demonstrates the analysis pipeline working.
    "institution_swap": -3.5,
    "evidence_links": -2.0,
}

MOCK_RECS = ["advance", "hold", "reject"]


def mock_call(jd, model_key, condition, ablation, rep, order_index, resume_text, attempt=0):
    """Deterministic fake score, returned as a JSON text string (in, out, reasoning=None)
    to mirror the real-call signature so both paths go through the same extract_json +
    retry logic in call_model_with_retry.

    Set env MOCK_BAD_RATE (0..1) to make a fraction of calls come back as an empty
    string instead — simulates a reasoning model whose hidden reasoning ate the whole
    output-token budget, for exercising the parse-error/retry path in --mock mode.
    The bad/good coin flip is re-drawn per `attempt` so a retry gets an independent
    chance to succeed, like a real flaky call.
    """
    # Artificial per-call latency for concurrency testing (MOCK_LATENCY seconds,
    # default 0 = no delay). Sleeping here — inside the "provider call" — makes
    # a mock run's wall-clock time behave like a real one, so --concurrency's
    # speedup is actually observable/testable without hitting any network.
    latency = float(os.environ.get("MOCK_LATENCY", "0") or 0.0)
    if latency > 0:
        time.sleep(latency)

    seed_str = f"{jd['jd_id']}|{model_key}|{condition}|{ablation}|{rep}"
    rng = random.Random(int(hashlib.sha256(seed_str.encode()).hexdigest()[:16], 16))

    jd_base = 45 + (hash(jd["jd_id"]) % 30)  # 45-74, stable per JD
    model_offset = 3 if "haiku" in model_key else -2
    rep_noise = rng.gauss(0, 4)
    ablation_effect = MOCK_ABLATION_EFFECT.get(ablation, 0.0) if condition == "B" else 0.0

    fit_score = jd_base + model_offset + rep_noise + ablation_effect
    fit_score = max(0, min(100, round(fit_score)))

    if fit_score >= 65:
        rec = "advance"
    elif fit_score >= 45:
        rec = "hold"
    else:
        rec = "reject"

    raw = {
        "fit_score": fit_score,
        "recommendation": rec,
        "top_reasons": [
            f"[mock] relevant eval/RAG ownership for {jd['title']}",
            "[mock] quantified impact present in bullets",
            "[mock] domain overlap with JD requirements",
        ],
        "objections": [] if fit_score >= 55 else ["[mock] limited direct frontier-lab experience"],
        "discounted_claims": ["[mock] '~95% citation accuracy' — self-reported, no external link"]
        if condition == "B" and ablation == "evidence_links" else [],
    }

    input_tokens = len(resume_text.split()) + len(jd["text"].split()) + 220
    output_tokens = 140 + rng.randint(-20, 30)

    bad_rate = float(os.environ.get("MOCK_BAD_RATE", "0") or 0.0)
    if bad_rate > 0:
        bad_seed = f"{seed_str}|attempt{attempt}|badcheck"
        bad_rng = random.Random(int(hashlib.sha256(bad_seed.encode()).hexdigest()[:16], 16))
        if bad_rng.random() < bad_rate:
            return "", input_tokens, 5, None

    return json.dumps(raw), input_tokens, output_tokens, None


# ---------------------------------------------------------------------------
# Real API calls
# ---------------------------------------------------------------------------

def real_call_anthropic(model_id, system, user, max_tokens):
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=model_id,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in resp.content if hasattr(block, "text"))
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def _openai_rejects_param(exc: Exception, param_name: str) -> bool:
    """True if an OpenAI API error looks like it's rejecting a specific request
    param (e.g. a model that doesn't support reasoning_effort), so the caller can
    retry once without it rather than failing the whole call."""
    msg = str(exc).lower()
    if param_name.lower() not in msg:
        return False
    return any(s in msg for s in ("unsupported", "unknown parameter", "not supported", "unrecognized"))


def real_call_openai(model_id, system, user, max_tokens, reasoning_effort="low"):
    """gpt-5-mini (and other reasoning-family models) spend part of the
    max_completion_tokens budget on HIDDEN reasoning tokens before writing the
    visible answer — a small budget can be entirely consumed by reasoning, leaving
    an empty `message.content`. Mitigations here: a caller-enforced token floor
    (see resolved_max_tokens), reasoning_effort="low" to shrink the reasoning
    budget (dropped and retried once if the model rejects the param), and
    response_format=json_object (OpenAI requires the word "JSON" to appear
    somewhere in the prompt for this — see rubric.SYSTEM_PROMPT)."""
    import openai
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    kwargs = dict(
        model=model_id,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_completion_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    if reasoning_effort:
        kwargs["reasoning_effort"] = reasoning_effort
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:  # noqa: BLE001
        if reasoning_effort and _openai_rejects_param(e, "reasoning_effort"):
            kwargs.pop("reasoning_effort", None)
            resp = client.chat.completions.create(**kwargs)
        else:
            raise
    text = resp.choices[0].message.content or ""
    reasoning_tokens = None
    details = getattr(resp.usage, "completion_tokens_details", None)
    if details is not None:
        reasoning_tokens = getattr(details, "reasoning_tokens", None)
    if reasoning_tokens is not None:
        print(f"      [{model_id}] reasoning_tokens={reasoning_tokens} "
              f"completion_tokens={resp.usage.completion_tokens}", file=sys.stderr)
    return text, resp.usage.prompt_tokens, resp.usage.completion_tokens, reasoning_tokens


def extract_json(text):
    """Best-effort JSON extraction from a model response: strip markdown fences,
    take the substring from the first '{' to the last '}', then json.loads it.
    Never raises — returns None on any failure (empty text, no braces, truncated
    JSON, etc.) so callers can retry or record a parse error instead of crashing."""
    if not text:
        return None
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        stripped = t.lstrip()
        t = stripped[4:] if stripped[:4].lower() == "json" else stripped
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(t[start:end + 1])
    except (json.JSONDecodeError, ValueError):
        return None


def resolved_max_tokens(model_cfg, cfg):
    """Per-provider output-token floor, applied on top of run.max_output_tokens in
    config.yaml. Reasoning models (gpt-5-mini) need real headroom for hidden
    reasoning tokens on top of the visible JSON answer — a config value lower than
    this floor would silently starve them. See real_call_openai docstring."""
    base = cfg["run"]["max_output_tokens"]
    if model_cfg["provider"] == "openai":
        return max(base, 2000)
    if model_cfg["provider"] == "anthropic":
        return max(base, 1500)
    return base


class RateLimitExhausted(Exception):
    """Raised by call_with_backoff when a provider is still rate-limited /
    overloaded after every retry — distinguishes an infra-level failure
    (recorded as api_error) from a content-level one (parse_error)."""


def is_rate_limit_error(exc: Exception) -> bool:
    """Heuristic for a transient, worth-retrying provider error: HTTP 429
    (rate limited, both providers) or 529 (Anthropic 'overloaded'). Checks
    the SDK exception's status_code when present (anthropic/openai both set
    one on their APIStatusError subclasses) and falls back to the message
    text so this still works if a differently-shaped exception reaches here."""
    status = getattr(exc, "status_code", None)
    if status in (429, 529):
        return True
    msg = str(exc).lower()
    return any(s in msg for s in
               ("rate limit", "rate_limit", "too many requests", "overloaded", "429", "529"))


def call_with_backoff(fn, max_tries=5, delays=(1, 2, 4, 8)):
    """Call fn() (no args), retrying with exponential backoff (delays, seconds)
    only on a rate-limit/overloaded error (see is_rate_limit_error). Any other
    exception propagates immediately, unchanged, on the first try. Up to
    max_tries attempts total; raises RateLimitExhausted (wrapping the last
    error) if every attempt was rate-limited."""
    last_exc = None
    for attempt in range(max_tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            if not is_rate_limit_error(e):
                raise
            last_exc = e
            if attempt < max_tries - 1:
                time.sleep(delays[min(attempt, len(delays) - 1)])
    raise RateLimitExhausted(str(last_exc))


def call_model_with_retry(model_cfg, system, user, max_output_tokens, mock=False, mock_fn=None):
    """Make one scoring call, retrying once (same params) on empty content, an
    unparseable response, or a transient API exception. Never raises.

    A 429/overloaded error is handled one level below this retry-on-empty
    loop: each real provider call is wrapped in call_with_backoff, which
    retries with exponential backoff (1,2,4,8s, up to 5 tries) before this
    function ever sees it. Only once backoff is exhausted does that count as
    one of this function's two attempts, recorded as api_error rather than
    parse_error (there was no content to fail to parse).

    mock_fn: when mock=True, a callable(attempt) -> (text, in_tok, out_tok, reasoning_tokens),
    e.g. a closure over mock_call(...). Ignored when mock=False.

    Returns a dict:
        raw            parsed JSON dict, or None if both attempts failed
        in_tokens      summed prompt/input tokens across attempts actually made
        out_tokens     summed completion/output tokens across attempts actually made
        reasoning_tokens  last attempt's value (openai reasoning models), else None
        parse_error    True iff `raw` is None (both attempts failed)
        api_error      True iff the failure was a rate-limit/overloaded error that
                       survived backoff (a subset of parse_error==True cases)
        raw_text       first 2000 chars of the failing text/error, only set if parse_error
        n_attempts     1 or 2
        error          last API exception string, if failure was an exception; else None
    """
    total_in = 0
    total_out = 0
    reasoning_tokens = None
    last_text = None
    last_error = None
    attempts_made = 0

    for attempt in range(2):
        attempts_made += 1
        try:
            if mock:
                text, in_tok, out_tok, r_tok = mock_fn(attempt)
            elif model_cfg["provider"] == "anthropic":
                text, in_tok, out_tok = call_with_backoff(
                    lambda: real_call_anthropic(model_cfg["model_id"], system, user, max_output_tokens)
                )
                r_tok = None
            elif model_cfg["provider"] == "openai":
                text, in_tok, out_tok, r_tok = call_with_backoff(
                    lambda: real_call_openai(
                        model_cfg["model_id"], system, user, max_output_tokens,
                        reasoning_effort=model_cfg.get("reasoning_effort", "low"),
                    )
                )
            else:
                raise ValueError(f"unknown provider {model_cfg['provider']}")
        except RateLimitExhausted as e:
            # Infra-level failure, not a content one — no point burning the
            # second empty-content retry on a provider that's still rate-limited.
            return {
                "raw": None, "in_tokens": total_in, "out_tokens": total_out,
                "reasoning_tokens": reasoning_tokens, "parse_error": True, "api_error": True,
                "raw_text": None, "n_attempts": attempts_made, "error": str(e),
            }
        except Exception as e:  # noqa: BLE001
            last_error = str(e)
            continue  # retry once on API exceptions too

        total_in += in_tok
        total_out += out_tok
        reasoning_tokens = r_tok
        last_text = text
        last_error = None
        raw = extract_json(text) if text else None
        if text and raw is not None:
            return {
                "raw": raw, "in_tokens": total_in, "out_tokens": total_out,
                "reasoning_tokens": reasoning_tokens, "parse_error": False, "api_error": False,
                "raw_text": None, "n_attempts": attempts_made, "error": None,
            }
        # empty content or unparseable JSON — loop retries once more

    return {
        "raw": None, "in_tokens": total_in, "out_tokens": total_out,
        "reasoning_tokens": reasoning_tokens, "parse_error": True, "api_error": False,
        "raw_text": (last_text or last_error or "")[:2000],
        "n_attempts": attempts_made, "error": last_error,
    }


def est_cost(input_tokens, output_tokens, model_cfg):
    return (input_tokens / 1_000_000 * model_cfg["price_input_per_1m"]) + (
        output_tokens / 1_000_000 * model_cfg["price_output_per_1m"]
    )


def preflight():
    """Load .env, confirm both API keys are present, and make one tiny real
    call per provider (cheapest/only models in config.yaml) so a non-technical
    user can confirm their keys work before spending anything on a real run."""
    cfg = load_config()
    missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.environ.get(k)]
    if missing:
        print(f"Missing from .env: {', '.join(missing)}", file=sys.stderr)
        print("Open .env (e.g. `open -e .env` on a Mac) and paste your key(s) in, then re-run "
              "`make keys-check`.", file=sys.stderr)
        sys.exit(1)

    print("Found ANTHROPIC_API_KEY and OPENAI_API_KEY in .env.")
    print("Making one tiny test call per provider (cheapest/configured models)...\n")

    all_ok = True
    for model_cfg in cfg["models"]:
        resolved = resolved_max_tokens(model_cfg, cfg)
        reasoning_effort = model_cfg.get("reasoning_effort", "low") if model_cfg["provider"] == "openai" else None
        params_note = f"max_output_tokens={resolved}" + (f", reasoning_effort={reasoning_effort!r}" if reasoning_effort else "")
        try:
            if model_cfg["provider"] == "anthropic":
                text, in_tok, out_tok = real_call_anthropic(
                    model_cfg["model_id"], "Reply with exactly one word: OK", "Reply now.", resolved
                )
                reasoning_tokens = None
            elif model_cfg["provider"] == "openai":
                text, in_tok, out_tok, reasoning_tokens = real_call_openai(
                    model_cfg["model_id"],
                    'Reply with exactly one word, as JSON: {"reply": "OK"}',
                    "Reply now.", resolved, reasoning_effort=reasoning_effort,
                )
            else:
                print(f"  [{model_cfg['provider']}] {model_cfg['model_id']}: unknown provider, skipped")
                continue
        except Exception as e:  # noqa: BLE001
            all_ok = False
            print(f"  FAIL {model_cfg['provider']:9s} {model_cfg['model_id']:20s} "
                  f"({params_note}) — {e}", file=sys.stderr)
            continue

        if not text or not text.strip():
            all_ok = False
            print(f"  FAIL {model_cfg['provider']:9s} {model_cfg['model_id']:20s} "
                  f"({params_note}) — responded empty (reasoning model ate the budget?). "
                  f"Try raising run.max_output_tokens in config.yaml, or switch to a "
                  f"non-reasoning alternative (see the comment next to gpt-5-mini in "
                  f"config.yaml, e.g. gpt-4.1-mini).", file=sys.stderr)
            continue

        cost = est_cost(in_tok, out_tok, model_cfg)
        reasoning_note = f", reasoning_tokens={reasoning_tokens}" if reasoning_tokens is not None else ""
        print(f"  OK  {model_cfg['provider']:9s} {model_cfg['model_id']:20s} "
              f"({params_note}) responded {text.strip()[:20]!r} — ~${cost:.6f} for this call "
              f"(in={in_tok} out={out_tok} tokens{reasoning_note})")
        print(f"      est. per-call price for a real pilot/run call (~900 in / ~160 out tok): "
              f"${est_cost(900, 160, model_cfg):.5f}")

    if not all_ok:
        print("\nAt least one provider failed — check the key(s) and error above before running "
              "`make pilot`.", file=sys.stderr)
        sys.exit(1)
    print("\nBoth providers responded. You're ready for `make pilot`.")


def build_call_specs(jds, models, reps, ablation, resume_a_text, resume_b_text, seed):
    """Build the FULL ordered list of calls before anything is executed:
    rep -> shuffled JDs -> model -> randomized A/B order — the interleaved
    design (see module docstring). order_index is this list's position
    (0..N-1), global across the whole run, not per (rep, jd, model) pair —
    it exists so a line in calls.jsonl can be placed back into run order even
    though completion order (and hence file-write order) may differ once
    calls run concurrently. Returns (specs, rng) — rng is exposed only so a
    caller could keep drawing from the same stream if ever needed; nothing
    here does that today.
    """
    rng = random.Random(seed)
    specs = []
    order_index = 0
    for rep in range(reps):
        jd_order = jds[:]
        rng.shuffle(jd_order)
        for jd in jd_order:
            for model_cfg in models:
                conditions = ["A", "B"]
                rng.shuffle(conditions)
                for condition in conditions:
                    specs.append({
                        "order_index": order_index,
                        "rep": rep,
                        "jd": jd,
                        "model_cfg": model_cfg,
                        "condition": condition,
                        "resume_text": resume_a_text if condition == "A" else resume_b_text,
                        "ablation": ablation,
                    })
                    order_index += 1
    return specs, rng


def call_key(spec):
    """The (jd, model, condition, rep) tuple identifying a call, independent
    of order_index — used for --resume de-duplication."""
    return (spec["jd"]["jd_id"], spec["model_cfg"]["key"], spec["condition"], spec["rep"])


def record_key(record):
    return (record["jd_id"], record["model"], record["condition"], record["rep"])


def execute_call_spec(spec, cfg, run_id, mock):
    """Run one call spec to completion (including its own empty-content and
    rate-limit retries) and return the calls.jsonl record dict. Safe to call
    from a worker thread — touches no shared state."""
    jd, model_cfg, condition, rep = spec["jd"], spec["model_cfg"], spec["condition"], spec["rep"]
    ablation, order_index = spec["ablation"], spec["order_index"]
    resume_text = spec["resume_text"]
    system, user = build_messages(jd["text"], resume_text, jd["employer"], jd["title"])
    resolved_tokens = resolved_max_tokens(model_cfg, cfg)

    ts = datetime.now(timezone.utc).isoformat()
    if mock:
        def mock_fn(attempt, jd=jd, model_cfg=model_cfg, condition=condition,
                    ablation=ablation, rep=rep, order_index=order_index, resume_text=resume_text):
            return mock_call(jd, model_cfg["key"], condition, ablation, rep,
                              order_index, resume_text, attempt=attempt)
        result = call_model_with_retry(model_cfg, system, user, resolved_tokens, mock=True, mock_fn=mock_fn)
    else:
        result = call_model_with_retry(model_cfg, system, user, resolved_tokens)

    raw = result["raw"] if result["raw"] is not None else {
        "fit_score": None, "recommendation": None, "top_reasons": [],
        "objections": [], "discounted_claims": [],
    }
    in_tok, out_tok = result["in_tokens"], result["out_tokens"]
    cost = est_cost(in_tok, out_tok, model_cfg)

    return {
        "run_id": run_id,
        "ts": ts,
        "jd_id": jd["jd_id"],
        "employer": jd["employer"],
        "employer_class": jd["employer_class"],
        "model": model_cfg["key"],
        "condition": condition,
        "ablation": ablation,
        "rep": rep,
        "order_index": order_index,
        "fit_score": raw.get("fit_score"),
        "recommendation": raw.get("recommendation"),
        "raw": raw,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "reasoning_tokens": result["reasoning_tokens"],
        "est_cost_usd": round(cost, 6),
        "parse_error": result["parse_error"],
        "api_error": result.get("api_error", False),
        "raw_text": result["raw_text"],
        "n_attempts": result["n_attempts"],
        "error": result["error"],
    }


def run_calls(specs, cfg, run_id, mock, concurrency, calls_path, file_mode="w"):
    """Execute specs with a thread pool of `concurrency` workers, appending
    each finished record to calls_path as a single JSON line under a lock
    (flushed immediately) as it completes — so completion order, not
    order_index, decides line order; analysis must key off record fields,
    not position (see analysis/analyze.py, which already does). Prints a
    progress line every 20 completions: done/total, elapsed, rate/min, ETA.
    """
    total = len(specs)
    write_lock = threading.Lock()
    progress_lock = threading.Lock()
    done = 0
    start = time.monotonic()

    with open(calls_path, file_mode) as f:
        results = []
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
            futures = {pool.submit(execute_call_spec, spec, cfg, run_id, mock): spec for spec in specs}
            for fut in as_completed(futures):
                record = fut.result()
                with write_lock:
                    f.write(json.dumps(record) + "\n")
                    f.flush()
                results.append(record)
                with progress_lock:
                    done += 1
                    n = done
                if n % 20 == 0 or n == total:
                    elapsed = time.monotonic() - start
                    rate_per_min = (n / elapsed * 60) if elapsed > 0 else 0.0
                    remaining = total - n
                    eta_s = (remaining / (n / elapsed)) if n > 0 and elapsed > 0 else 0.0
                    print(f"[progress] {n}/{total} done, elapsed {elapsed:.1f}s, "
                          f"rate {rate_per_min:.1f}/min, ETA {eta_s:.1f}s", flush=True)

    return results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mock", action="store_true", help="deterministic fake scores, no API calls")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--ablation", choices=["institution_swap", "evidence_links"], default=None,
                     help="required unless --preflight/--resume is set")
    ap.add_argument("--jds", type=str, default=None, help="comma-separated jd_ids, default = all indexed JDs with text present")
    ap.add_argument("--models", type=str, default=None, help="comma-separated model keys from config.yaml, default = all")
    ap.add_argument("--run-id", type=str, default=None)
    ap.add_argument("--out-dir", type=str, default=None)
    ap.add_argument("--concurrency", type=int, default=None,
                     help="parallel workers (ThreadPoolExecutor); default = config.yaml run.concurrency, or 8")
    ap.add_argument("--resume", type=str, default=None, metavar="RUN_ID",
                     help="continue an interrupted run: reuses that run's manifest (ablation, reps, "
                          "seed, jds, models) so the ordered call list reproduces identically, then "
                          "skips any (jd, model, condition, rep) already present in its calls.jsonl")
    ap.add_argument("--preflight", action="store_true",
                     help="load .env, confirm both API keys are present, make one tiny real call "
                          "per provider, print model ids and estimated per-call cost, then exit")
    args = ap.parse_args()

    if args.preflight:
        preflight()
        return

    cfg = load_config()
    concurrency = args.concurrency if args.concurrency is not None else cfg.get("run", {}).get("concurrency", 8)

    resumed_from = None
    existing_records = []

    if args.resume:
        run_id = args.resume
        out_dir = Path(args.out_dir) if args.out_dir else ROOT / "results" / run_id
        manifest_path = out_dir / "manifest.json"
        calls_path = out_dir / "calls.jsonl"
        if not manifest_path.exists():
            print(f"--resume {run_id}: no manifest.json at {manifest_path}", file=sys.stderr)
            sys.exit(1)
        prior = json.loads(manifest_path.read_text())
        resumed_from = run_id
        args.mock = prior["mock"]
        args.ablation = prior["ablation"]
        args.reps = prior["reps"]
        seed = prior["seed"]
        jd_filter = set(prior["jd_ids"])
        models = prior["models"]
        if calls_path.exists():
            with open(calls_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        existing_records.append(json.loads(line))
        print(f"Resuming {run_id}: {len(existing_records)} calls already recorded "
              f"(ablation={args.ablation}, reps={args.reps}, mock={args.mock}, concurrency={concurrency})")
    else:
        if not args.ablation:
            ap.error("--ablation is required (unless --preflight or --resume is set)")
        jd_filter = set(args.jds.split(",")) if args.jds else None
        model_keys = args.models.split(",") if args.models else [m["key"] for m in cfg["models"]]
        models = [m for m in cfg["models"] if m["key"] in model_keys]
        run_id = args.run_id or f"{'mock-' if args.mock else 'real-'}{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        out_dir = Path(args.out_dir) if args.out_dir else ROOT / "results" / run_id
        seed = random.randrange(2**31)

    out_dir.mkdir(parents=True, exist_ok=True)
    calls_path = out_dir / "calls.jsonl"

    jds = load_jds(jd_filter)
    if not jds:
        print("No JDs with text available — nothing to run. (Real JD text is gitignored; "
              "run against the synthetic placeholders or collect real JDs first.)", file=sys.stderr)
        sys.exit(1)

    resume_a_path = resume_path_for("A", None, cfg)
    resume_b_path = resume_path_for("B", args.ablation, cfg)
    resume_a_text = resume_a_path.read_text()
    resume_b_text = resume_b_path.read_text()
    resume_hashes = {"A": sha256_file(resume_a_path), "B": sha256_file(resume_b_path)}

    started_at = datetime.now(timezone.utc).isoformat()

    specs, _rng = build_call_specs(jds, models, args.reps, args.ablation, resume_a_text, resume_b_text, seed)

    if not resumed_from:
        # Manifest written at start (requirement: config + resolved concurrency
        # recorded before any calls run, updated again once they finish).
        manifest = {
            "run_id": run_id,
            "mock": args.mock,
            "ablation": args.ablation,
            "reps": args.reps,
            "seed": seed,
            "concurrency": concurrency,
            "resumed_from": resumed_from,
            "started_at": started_at,
            "n_calls_planned": len(specs),
            "models": models,
            "jd_ids": [jd["jd_id"] for jd in jds],
            "jd_sha256": {jd["jd_id"]: hashlib.sha256(jd["text"].encode()).hexdigest() for jd in jds},
            "resume_sha256": resume_hashes,
            "resume_paths": {"A": str(resume_a_path.relative_to(ROOT)), "B": str(resume_b_path.relative_to(ROOT))},
            "config_snapshot": cfg,
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
        completed_keys = set()
    else:
        completed_keys = {record_key(r) for r in existing_records}

    pending_specs = [s for s in specs if call_key(s) not in completed_keys]
    skipped = len(specs) - len(pending_specs)
    if resumed_from and skipped:
        print(f"Skipping {skipped} already-completed call(s) from the prior run.")

    file_mode = "a" if (resumed_from and calls_path.exists()) else "w"
    if pending_specs:
        run_calls(pending_specs, cfg, run_id, args.mock, concurrency, calls_path, file_mode=file_mode)
    else:
        print("Nothing to do — every call in this run's spec is already in calls.jsonl.")

    # Recompute totals from the whole file on disk (existing + newly written)
    # so a resumed run's manifest reflects the run as a whole, not just this
    # session's slice of it.
    all_records = []
    if calls_path.exists():
        with open(calls_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    all_records.append(json.loads(line))

    n_calls = len(all_records)
    n_parse_errors = sum(1 for r in all_records if r.get("parse_error"))
    n_api_errors = sum(1 for r in all_records if r.get("api_error"))
    total_cost = sum(r.get("est_cost_usd", 0.0) for r in all_records)
    ended_at = datetime.now(timezone.utc).isoformat()

    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    resume_events = manifest.get("resume_events", [])
    if resumed_from:
        resume_events.append({"at": started_at, "skipped_already_done": skipped, "ran": len(pending_specs)})
    manifest.update({
        "run_id": run_id,
        "ended_at": ended_at,
        "finished_at": ended_at,  # kept for backward compatibility with older tooling
        "completed_calls": n_calls,
        "n_calls": n_calls,  # kept for backward compatibility (analysis/analyze.py reads this)
        "api_errors": n_api_errors,
        "parse_errors": n_parse_errors,
        "n_parse_errors": n_parse_errors,  # kept for backward compatibility
        "total_est_cost_usd": round(total_cost, 4),
        "concurrency": concurrency,
        "resume_events": resume_events,
    })
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"Run {run_id}: {n_calls} calls ({n_parse_errors} parse errors, {n_api_errors} api errors), "
          f"est. cost ${total_cost:.4f}")
    if n_calls and n_parse_errors / n_calls > 0.5:
        print(f"*** WARNING: {n_parse_errors}/{n_calls} calls had parse errors in this run — "
              f"results are unreliable. Check calls.jsonl `raw_text` fields and consider the "
              f"model alternatives noted in config.yaml. ***", file=sys.stderr)
    print(f"Wrote {calls_path}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
