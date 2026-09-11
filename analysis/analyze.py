#!/usr/bin/env python3
"""
Analyze a completed run's results/<run_id>/calls.jsonl.

Per model, per ablation:
  - paired deltas per JD (mean fit_score(B) - mean fit_score(A) across reps, per JD)
  - mean delta with paired-bootstrap 95% CI (10k resamples by default, config.yaml)
  - sign test p-value (two-sided, exact binomial) on JD-level deltas
  - recommendation flip count (A's recommendation vs B's recommendation, per
    JD x model x rep pair)
  - frontier-lab subset reported separately
  - a per-JD table

All numbers here are counted or computed from calls.jsonl. No LLM judges anything.

Usage:
    python3 analysis/analyze.py results/<run_id>
Writes:
    reports/<run_id>_analysis.md
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import yaml
from scipy.stats import binomtest

ROOT = Path(__file__).resolve().parents[1]


def load_calls(run_dir: Path):
    calls = []
    with open(run_dir / "calls.jsonl") as f:
        for line in f:
            calls.append(json.loads(line))
    manifest = json.loads((run_dir / "manifest.json").read_text())
    return calls, manifest


def paired_bootstrap_ci(deltas, resamples, ci_level, rng):
    deltas = np.array(deltas)
    n = len(deltas)
    if n == 0:
        return (float("nan"), float("nan"))
    boot_means = np.empty(resamples)
    for i in range(resamples):
        sample = rng.choice(deltas, size=n, replace=True)
        boot_means[i] = sample.mean()
    alpha = 1 - ci_level
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return lo, hi


def sign_test_p(deltas):
    deltas = [d for d in deltas if d != 0]
    if not deltas:
        return float("nan")
    n = len(deltas)
    n_pos = sum(1 for d in deltas if d > 0)
    return binomtest(n_pos, n, 0.5).pvalue


def analyze_model(calls, model_key, cfg):
    all_model_calls = [c for c in calls if c["model"] == model_key]
    n_calls = len(all_model_calls)
    n_parse_errors = sum(1 for c in all_model_calls if c.get("parse_error"))
    n_parsed = n_calls - n_parse_errors

    # SD/deltas below are computed on parsed calls only (fit_score is None for any
    # call with parse_error) — parse failures are excluded, not imputed as zero.
    rows = [c for c in all_model_calls if c["fit_score"] is not None]
    by_jd_cond = defaultdict(lambda: defaultdict(list))  # jd_id -> condition -> [fit_score]
    by_jd_meta = {}
    rec_pairs = []  # (jd_id, rep, rec_A, rec_B)

    by_jd_rep = defaultdict(dict)  # (jd_id, rep) -> condition -> record
    for r in rows:
        key = (r["jd_id"], r["rep"])
        by_jd_rep[key][r["condition"]] = r
        by_jd_cond[r["jd_id"]][r["condition"]].append(r["fit_score"])
        by_jd_meta[r["jd_id"]] = {"employer": r["employer"], "employer_class": r["employer_class"]}

    for (jd_id, rep), conds in by_jd_rep.items():
        if "A" in conds and "B" in conds:
            rec_pairs.append((jd_id, rep, conds["A"]["recommendation"], conds["B"]["recommendation"]))

    flips = sum(1 for _, _, a, b in rec_pairs if a != b)
    n_pairs = len(rec_pairs)

    per_jd_table = []
    jd_deltas = []
    for jd_id, conds in by_jd_cond.items():
        if "A" not in conds or "B" not in conds:
            continue
        mean_a = float(np.mean(conds["A"]))
        mean_b = float(np.mean(conds["B"]))
        delta = mean_b - mean_a
        jd_deltas.append(delta)
        per_jd_table.append({
            "jd_id": jd_id,
            "employer": by_jd_meta[jd_id]["employer"],
            "employer_class": by_jd_meta[jd_id]["employer_class"],
            "n_a": len(conds["A"]),
            "n_b": len(conds["B"]),
            "mean_a": mean_a,
            "mean_b": mean_b,
            "delta": delta,
        })

    rng = np.random.default_rng(12345)
    ci_lo, ci_hi = paired_bootstrap_ci(
        jd_deltas, cfg["analysis"]["bootstrap_resamples"], cfg["analysis"]["ci_level"], rng
    )
    p_sign = sign_test_p(jd_deltas)
    mean_delta = float(np.mean(jd_deltas)) if jd_deltas else float("nan")

    frontier_deltas = [
        row["delta"] for row in per_jd_table if row["employer_class"] == "frontier_lab"
    ]
    frontier_mean = float(np.mean(frontier_deltas)) if frontier_deltas else float("nan")

    return {
        "model": model_key,
        "n_calls": n_calls,
        "n_parsed": n_parsed,
        "n_parse_errors": n_parse_errors,
        "n_jd_pairs": len(jd_deltas),
        "mean_delta": mean_delta,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "sign_test_p": p_sign,
        "rec_flips": flips,
        "rec_pairs_n": n_pairs,
        "frontier_mean_delta": frontier_mean,
        "frontier_n": len(frontier_deltas),
        "per_jd": per_jd_table,
    }


def render_report(run_id, manifest, results, cfg):
    lines = []
    lines.append(f"# Analysis — {run_id}\n")
    lines.append(f"Ablation: `{manifest['ablation']}`  ")
    lines.append(f"Mock run: `{manifest['mock']}`  ")
    lines.append(f"Reps: {manifest['reps']}  ")
    lines.append(f"Calls: {manifest['n_calls']}  ")
    lines.append(f"Est. cost: ${manifest['total_est_cost_usd']}\n")
    lines.append(
        "All numbers below are counted/computed directly from `calls.jsonl` — "
        "no LLM judged any output. Paired bootstrap CI uses "
        f"{cfg['analysis']['bootstrap_resamples']} resamples at "
        f"{int(cfg['analysis']['ci_level']*100)}% confidence.\n"
    )

    for res in results:
        lines.append(f"## {res['model']}\n")
        lines.append(f"- Calls: {res['n_calls']} total, {res['n_parsed']} parsed, "
                      f"{res['n_parse_errors']} parse errors (parse errors excluded from all "
                      f"SD/delta calculations below, not imputed)")
        if res["n_calls"] > 0 and res["n_parse_errors"] / res["n_calls"] > 0.5:
            alt = "gpt-4.1-mini (non-reasoning)" if "gpt" in res["model"] else "an alternate model in config.yaml"
            warning = (f"- *** WARNING: {res['n_parse_errors']}/{res['n_calls']} "
                       f"({res['n_parse_errors'] / res['n_calls'] * 100:.0f}%) parse errors for "
                       f"{res['model']} — results below rest on very few parsed calls and are not "
                       f"trustworthy. Consider {alt}, raising run.max_output_tokens, or lowering "
                       f"reasoning_effort in config.yaml. ***")
            lines.append(warning)
            print(warning, file=sys.stderr)
        lines.append(f"- Paired JD deltas (B - A): n = {res['n_jd_pairs']}")
        lines.append(f"- Mean delta: **{res['mean_delta']:.2f}** points, "
                      f"{int(cfg['analysis']['ci_level']*100)}% bootstrap CI "
                      f"[{res['ci_lo']:.2f}, {res['ci_hi']:.2f}]")
        lines.append(f"- Sign test p-value (two-sided): {res['sign_test_p']:.4f}")
        lines.append(f"- Recommendation flips: {res['rec_flips']} / {res['rec_pairs_n']} paired runs")
        if res["frontier_n"] > 0:
            lines.append(f"- Frontier-lab subset (n={res['frontier_n']}): mean delta "
                          f"{res['frontier_mean_delta']:.2f}")
        else:
            lines.append("- Frontier-lab subset: no frontier_lab-tagged JDs in this run")
        lines.append("")
        lines.append("| jd_id | employer | class | n_A | n_B | mean_A | mean_B | delta |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for row in sorted(res["per_jd"], key=lambda r: r["jd_id"]):
            lines.append(
                f"| {row['jd_id']} | {row['employer']} | {row['employer_class']} | "
                f"{row['n_a']} | {row['n_b']} | {row['mean_a']:.1f} | {row['mean_b']:.1f} | "
                f"{row['delta']:+.1f} |"
            )
        lines.append("")

    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=str, help="results/<run_id> directory, or bare run_id")
    args = ap.parse_args()

    run_path = Path(args.run_dir)
    if not run_path.exists():
        run_path = ROOT / "results" / args.run_dir
    if not run_path.exists():
        print(f"run dir not found: {args.run_dir}", file=sys.stderr)
        sys.exit(1)

    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text())
    calls, manifest = load_calls(run_path)
    model_keys = sorted({c["model"] for c in calls})
    results = [analyze_model(calls, mk, cfg) for mk in model_keys]

    report = render_report(manifest["run_id"], manifest, results, cfg)
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / f"{manifest['run_id']}_analysis.md"
    out_path.write_text(report)
    print(f"Wrote {out_path}")
    print()
    print(report)


if __name__ == "__main__":
    main()
