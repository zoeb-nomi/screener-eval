#!/usr/bin/env python3
"""
Cross-screener comparison for a completed run's results/<run_id>/calls.jsonl.

Where analysis/analyze.py measures what one screener does to itself (A vs. B,
paired), this script measures what changes when a *different* screener reads
the *same* input — the variable nobody controls for in an ATS. Two families
of numbers, with different denominators by design (see each section below);
all of it is counted or computed directly from calls.jsonl, nothing is judged
by a model.

1. Same-résumé cross-model gap (condition A — the unmodified résumé — only,
   one mean fit_score per JD per model, n=21 JDs):
     - mean absolute gap, max absolute gap
     - which model scores higher, and on how many JDs
     - Pearson r between the two models' per-JD mean scores
     - majority-verdict agreement (mode recommendation per JD, condition A only)

2. Per-model noise/behavior characterization (every recorded call for that
   model in the run — both conditions, since this describes the screener's
   general behavior, not the A vs. B contrast):
     - mean fit score, distinct scores given, verdict distribution
     - (jd_id, condition) cells (n = n_jds x 2): how many have zero spread
       across reps, and the mean per-cell standard deviation (population SD)
     - verdict flips: for each JD, condition A reps only, did every rep agree
       on recommendation, or did the screener flip its own verdict? (n=21)

Usage:
    python3 analysis/cross_model.py results/<run_id>
Writes:
    reports/cross_model_<run_id>.md
"""
import argparse
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_calls(run_dir: Path):
    calls = []
    with open(run_dir / "calls.jsonl") as f:
        for line in f:
            calls.append(json.loads(line))
    manifest = json.loads((run_dir / "manifest.json").read_text())
    return calls, manifest


def pearson_r(xs, ys):
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx = math.sqrt(sum((a - mx) ** 2 for a in xs))
    sy = math.sqrt(sum((b - my) ** 2 for b in ys))
    if sx == 0 or sy == 0:
        return float("nan")
    return cov / (sx * sy)


def per_model_behavior(calls, model_key):
    """All calls (both conditions) for this model."""
    mc = [c for c in calls if c["model"] == model_key and c.get("fit_score") is not None]
    n_all = len(mc)
    scores = [c["fit_score"] for c in mc]
    distinct = len(set(scores))
    mean_score = sum(scores) / n_all if n_all else float("nan")
    verdicts = Counter(c["recommendation"] for c in mc)
    top_verdict, top_n = verdicts.most_common(1)[0] if verdicts else (None, 0)

    cells = defaultdict(list)
    for c in mc:
        cells[(c["jd_id"], c["condition"])].append(c["fit_score"])
    n_cells = len(cells)
    n_cells_sd0 = sum(1 for v in cells.values() if len(set(v)) == 1)
    cell_sds = [statistics.pstdev(v) for v in cells.values() if len(v) > 1]
    mean_cell_sd = sum(cell_sds) / len(cell_sds) if cell_sds else float("nan")

    # Verdict flips: condition A only, per JD.
    rec_a = defaultdict(list)
    for c in mc:
        if c["condition"] == "A":
            rec_a[c["jd_id"]].append(c["recommendation"])
    n_jds_a = len(rec_a)
    n_flips = sum(1 for v in rec_a.values() if len(set(v)) > 1)

    return {
        "model": model_key,
        "n_all": n_all,
        "distinct_scores": distinct,
        "mean_score": mean_score,
        "verdict_counts": dict(verdicts),
        "top_verdict": top_verdict,
        "top_verdict_n": top_n,
        "n_cells": n_cells,
        "n_cells_sd0": n_cells_sd0,
        "mean_cell_sd": mean_cell_sd,
        "n_jds_a": n_jds_a,
        "n_flips": n_flips,
    }


def cross_model_gap(calls, model_a, model_b):
    """Condition A only: one mean fit_score per JD per model."""
    means = {}
    recs = {}
    for model in (model_a, model_b):
        mc = [c for c in calls if c["model"] == model and c["condition"] == "A"
              and c.get("fit_score") is not None]
        by_jd = defaultdict(list)
        rec_by_jd = defaultdict(list)
        for c in mc:
            by_jd[c["jd_id"]].append(c["fit_score"])
            rec_by_jd[c["jd_id"]].append(c["recommendation"])
        means[model] = {jd: sum(v) / len(v) for jd, v in by_jd.items()}
        recs[model] = {jd: Counter(v).most_common(1)[0][0] for jd, v in rec_by_jd.items()}

    jds = sorted(set(means[model_a]) & set(means[model_b]))
    gaps = [means[model_b][jd] - means[model_a][jd] for jd in jds]
    abs_gaps = [abs(g) for g in gaps]
    mean_abs_gap = sum(abs_gaps) / len(abs_gaps) if abs_gaps else float("nan")
    max_abs_gap = max(abs_gaps) if abs_gaps else float("nan")
    b_higher = sum(1 for g in gaps if g > 0)
    x = [means[model_a][jd] for jd in jds]
    y = [means[model_b][jd] for jd in jds]
    r = pearson_r(x, y)
    agree = sum(1 for jd in jds if recs[model_a][jd] == recs[model_b][jd])

    per_jd = [{
        "jd_id": jd,
        "mean_a": means[model_a][jd],
        "mean_b": means[model_b][jd],
        "gap": means[model_b][jd] - means[model_a][jd],
        "rec_a": recs[model_a][jd],
        "rec_b": recs[model_b][jd],
        "agree": recs[model_a][jd] == recs[model_b][jd],
    } for jd in jds]

    return {
        "model_a": model_a,
        "model_b": model_b,
        "n_jds": len(jds),
        "mean_abs_gap": mean_abs_gap,
        "max_abs_gap": max_abs_gap,
        "b_higher_n": b_higher,
        "pearson_r": r,
        "majority_agree_n": agree,
        "per_jd": per_jd,
    }


def render_report(run_id, manifest, model_keys, gap, behaviors):
    lines = []
    lines.append(f"# Cross-screener comparison — {run_id}\n")
    lines.append(f"Ablation: `{manifest['ablation']}`  ")
    lines.append(f"Calls in run: {sum(b['n_all'] for b in behaviors)}  \n")
    lines.append(
        "All numbers below are counted/computed directly from `calls.jsonl` by "
        "`analysis/cross_model.py` — no LLM judged any output. Section 1 uses "
        "condition A (the unmodified résumé) only, one mean score per job "
        "description per model. Section 2 uses every recorded call for that "
        "model in this run (both conditions), because it characterizes the "
        "screener's own behavior, not the A/B contrast.\n"
    )

    lines.append("## 1. Same résumé, same posting — cross-model gap (condition A, "
                  f"n={gap['n_jds']} job descriptions)\n")
    lines.append(f"- Mean absolute gap ({gap['model_b']} − {gap['model_a']}): "
                  f"**{gap['mean_abs_gap']:.1f}** points")
    lines.append(f"- Max absolute gap: **{gap['max_abs_gap']:.1f}** points")
    lines.append(f"- {gap['model_b']} scores higher on **{gap['b_higher_n']} of "
                  f"{gap['n_jds']}** postings")
    lines.append(f"- Pearson r between the two models' per-JD mean scores: "
                  f"**{gap['pearson_r']:.2f}**")
    lines.append(f"- Majority-verdict agreement (mode recommendation per JD): "
                  f"**{gap['majority_agree_n']} of {gap['n_jds']}**\n")
    lines.append(f"| jd_id | mean {gap['model_a']} | mean {gap['model_b']} | gap | "
                  f"verdict {gap['model_a']} | verdict {gap['model_b']} | agree |")
    lines.append("|---|---|---|---|---|---|---|")
    for row in gap["per_jd"]:
        lines.append(
            f"| {row['jd_id']} | {row['mean_a']:.1f} | {row['mean_b']:.1f} | "
            f"{row['gap']:+.1f} | {row['rec_a']} | {row['rec_b']} | "
            f"{'yes' if row['agree'] else 'no'} |"
        )
    lines.append("")

    lines.append("## 2. Per-model noise and behavior (all calls in this run, both conditions)\n")
    lines.append("| Measure | " + " | ".join(behaviors[i]["model"] for i in range(len(behaviors))) + " |")
    lines.append("|---|" + "---|" * len(behaviors))
    lines.append("| Calls | " + " | ".join(str(b["n_all"]) for b in behaviors) + " |")
    lines.append("| Mean fit score | " + " | ".join(f"{b['mean_score']:.1f}" for b in behaviors) + " |")
    lines.append("| Distinct scores given | " + " | ".join(str(b["distinct_scores"]) for b in behaviors) + " |")
    lines.append("| Most common verdict | " + " | ".join(
        f"{b['top_verdict']} ({b['top_verdict_n']} of {b['n_all']})" for b in behaviors) + " |")
    lines.append("| (jd_id, condition) cells with zero spread across reps | " + " | ".join(
        f"{b['n_cells_sd0']} of {b['n_cells']}" for b in behaviors) + " |")
    lines.append("| Mean per-cell run-to-run SD (population) | " + " | ".join(
        f"{b['mean_cell_sd']:.1f}" for b in behaviors) + " |")
    lines.append("| Postings where the screener flipped its own verdict across reps "
                  "(condition A only) | " + " | ".join(
        f"{b['n_flips']} of {b['n_jds_a']}" for b in behaviors) + " |")
    lines.append("")

    lines.append("### Full verdict distributions\n")
    for b in behaviors:
        lines.append(f"- **{b['model']}**: " + ", ".join(
            f"{k} {v}" for k, v in sorted(b["verdict_counts"].items(), key=lambda kv: -kv[1])))
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

    calls, manifest = load_calls(run_path)
    model_keys = sorted({c["model"] for c in calls})
    if len(model_keys) != 2:
        print(f"expected exactly 2 models in this run, found {model_keys}", file=sys.stderr)
        sys.exit(1)

    gap = cross_model_gap(calls, model_keys[0], model_keys[1])
    behaviors = [per_model_behavior(calls, mk) for mk in model_keys]

    report = render_report(manifest["run_id"], manifest, model_keys, gap, behaviors)
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / f"cross_model_{manifest['run_id']}.md"
    out_path.write_text(report)
    print(f"Wrote {out_path}")
    print()
    print(report)


if __name__ == "__main__":
    main()
