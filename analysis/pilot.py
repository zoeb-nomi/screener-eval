#!/usr/bin/env python3
"""
Pilot mode: one JD x condition A x N reps per model -> SD of fit_score under an
IDENTICAL input, repeated -> reps needed to detect a stated minimum detectable
effect (MDE, default 5 fit_score points) at alpha 0.05 / power 0.8, paired design.

Run this BEFORE committing to a rep count for a real run. If the recommended reps
make the projected cost blow the budget, the effect you're chasing is too small to
afford — narrow the JD set or accept a larger MDE, don't run underpowered and
report it as if it meant something.

Sample-size note: the pilot only has repeated condition-A calls (no B), so it
measures per-call noise (sigma), not paired-difference noise directly. This script
uses the standard two-independent-sample power formula (n = 2*(z_a/2+z_b)^2*sigma^2
/ MDE^2) as a conservative upper bound on reps needed for the paired delta test —
conservative because a true paired analysis (analysis/analyze.py) benefits from any
positive correlation between A's and B's noise on the same call context, which this
pilot cannot observe. Treat the printed number as "at most this many," confirmed
generous, not tight.

Usage:
    python3 analysis/pilot.py --mock --jd synth-001 --reps 8       # mock, no keys/network needed
    python3 analysis/pilot.py --jd anthropic-pm-beneficial-deployments-001 --reps 10
        # real (needs .env populated — run `make keys-check` first)
    python3 analysis/pilot.py --mock --jd synth-001 --reps 8 --mde 3
Writes:
    reports/pilot_<jd_id>.md
"""
import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_screen import (  # noqa: E402
    load_config, load_jds, mock_call, est_cost, resume_path_for,
    call_model_with_retry, resolved_max_tokens,
)
from rubric import build_messages  # noqa: E402


def run_pilot(jd_id, reps, mock, models):
    cfg = load_config()
    jds = load_jds({jd_id})
    if not jds:
        print(f"JD {jd_id} not found or text missing", file=sys.stderr)
        sys.exit(1)
    jd = jds[0]
    resume_a_text = resume_path_for("A", None, cfg).read_text()
    system, user = build_messages(jd["text"], resume_a_text, jd["employer"], jd["title"])

    model_cfgs = [m for m in cfg["models"] if not models or m["key"] in models]
    per_model_scores = {}
    per_model_stats = {}  # key -> {n_calls, n_parsed, n_parse_errors}
    total_cost = 0.0

    for model_cfg in model_cfgs:
        scores = []
        n_parse_errors = 0
        resolved_tokens = resolved_max_tokens(model_cfg, cfg)
        for rep in range(reps):
            if mock:
                def mock_fn(attempt, jd=jd, model_cfg=model_cfg, rep=rep, resume_a_text=resume_a_text):
                    return mock_call(jd, model_cfg["key"], "A", "pilot", rep, 0, resume_a_text, attempt=attempt)
                result = call_model_with_retry(
                    model_cfg, system, user, resolved_tokens, mock=True, mock_fn=mock_fn
                )
            else:
                result = call_model_with_retry(model_cfg, system, user, resolved_tokens)

            total_cost += est_cost(result["in_tokens"], result["out_tokens"], model_cfg)

            if result["parse_error"]:
                n_parse_errors += 1
                print(f"  WARNING: {model_cfg['key']} rep {rep}: parse error after "
                      f"{result['n_attempts']} attempt(s) — raw_text[:200]="
                      f"{(result['raw_text'] or '')[:200]!r}", file=sys.stderr)
                continue  # excluded from SD/reps calc below — never crashes the pilot

            scores.append(result["raw"]["fit_score"])

        per_model_scores[model_cfg["key"]] = scores
        per_model_stats[model_cfg["key"]] = {
            "n_calls": reps, "n_parsed": reps - n_parse_errors, "n_parse_errors": n_parse_errors,
        }

    return jd, per_model_scores, per_model_stats, total_cost, cfg


def reps_needed(sigma, mde, alpha, power):
    if sigma == 0:
        return 1
    z_alpha = norm.ppf(1 - alpha / 2)
    z_power = norm.ppf(power)
    n = 2 * ((z_alpha + z_power) ** 2) * (sigma ** 2) / (mde ** 2)
    return math.ceil(n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jd", required=True, help="jd_id to pilot on")
    ap.add_argument("--reps", type=int, default=8, help="pilot reps per model")
    ap.add_argument("--mock", action="store_true")
    ap.add_argument("--mde", type=float, default=None, help="minimum detectable effect, fit_score points (default from config.yaml)")
    ap.add_argument("--models", type=str, default=None)
    ap.add_argument("--n-jds", type=int, default=20, help="for the cost projection: how many JDs a real run would cover")
    ap.add_argument("--n-ablations", type=int, default=2)
    args = ap.parse_args()

    models = args.models.split(",") if args.models else None
    jd, per_model_scores, per_model_stats, pilot_cost, cfg = run_pilot(args.jd, args.reps, args.mock, models)
    mde = args.mde if args.mde is not None else cfg["analysis"]["default_mde"]
    alpha = cfg["analysis"]["alpha"]
    power = cfg["analysis"]["power"]

    lines = [f"# Pilot — {jd['jd_id']} ({jd['employer']})\n",
             f"Pilot reps per model: {args.reps}  ",
             f"MDE: {mde} fit_score points  alpha: {alpha}  power: {power}\n",
             "Sample-size formula treats the pilot's single-condition SD as a conservative "
             "stand-in for paired-difference noise (see script docstring) — recommended reps "
             "are an upper bound, not a tight estimate. SD is computed on PARSED calls only; "
             "calls with parse_error (empty/unparseable model output, after one retry) are "
             "excluded — see n_parse_errors below.\n",
             "| model | n_calls | n_parsed | n_parse_errors | sigma (SD, parsed only) | recommended reps/JD/condition |",
             "|---|---|---|---|---|---|"]

    recommended = {}
    warnings = []
    for model_key, scores in per_model_scores.items():
        stats = per_model_stats[model_key]
        sigma = float(np.std(scores, ddof=1)) if len(scores) > 1 else 0.0
        n_rec = reps_needed(sigma, mde, alpha, power)
        recommended[model_key] = n_rec
        lines.append(f"| {model_key} | {stats['n_calls']} | {stats['n_parsed']} | "
                      f"{stats['n_parse_errors']} | {sigma:.2f} (n={len(scores)}) | {n_rec} |")

        if stats["n_calls"] > 0 and stats["n_parse_errors"] / stats["n_calls"] > 0.5:
            alt = "gpt-4.1-mini (non-reasoning)" if "gpt" in model_key else "an alternate model in config.yaml"
            warnings.append(
                f"*** WARNING: {model_key} had {stats['n_parse_errors']}/{stats['n_calls']} "
                f"({stats['n_parse_errors'] / stats['n_calls'] * 100:.0f}%) parse errors in this pilot "
                f"— its sigma/reps estimate above is based on very few (or zero) parsed calls and is "
                f"not trustworthy. Consider switching to {alt}, raising run.max_output_tokens, or "
                f"lowering reasoning_effort in config.yaml before running a real pilot/run on it. ***"
            )

    for w in warnings:
        print(w, file=sys.stderr)
    if warnings:
        lines.append("")
        lines.extend(warnings)

    worst_case_reps = max(recommended.values()) if recommended else 0
    lines.append(f"\nRecommended rep count for a real run (max across models): **{worst_case_reps}**\n")

    # cost projection for a plausible real run using the recommended rep count
    n_models = len(per_model_scores)
    total_calls = args.n_jds * n_models * args.n_ablations * worst_case_reps * 2  # x2 for A and B
    price_map = {m["key"]: m for m in cfg["models"]}
    avg_in = 900   # rough tokens/call, resume + JD + prompt scaffolding
    avg_out = 160
    est = 0.0
    for model_key in per_model_scores:
        m = price_map[model_key]
        per_call = est_cost(avg_in, avg_out, m)
        calls_this_model = args.n_jds * args.n_ablations * worst_case_reps * 2
        est += per_call * calls_this_model

    lines.append(f"Projected cost for {args.n_jds} JDs x {n_models} models x {args.n_ablations} "
                 f"ablations x {worst_case_reps} reps x 2 conditions ({total_calls} calls): "
                 f"**${est:.2f}** (rough token estimate, see scripts/estimate_cost.py for a tunable version)\n")
    lines.append(f"(Pilot itself cost ~${pilot_cost:.4f} in mock-equivalent tokens.)")

    report = "\n".join(lines)
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / f"pilot_{jd['jd_id']}.md"
    out_path.write_text(report)
    print(f"Wrote {out_path}\n")
    print(report)


if __name__ == "__main__":
    main()
