#!/usr/bin/env python3
"""
Project USD cost for a real run, given #JDs, #models, reps, and #ablations.
Uses per-model prices from config/config.yaml and a rough tokens/call estimate
(resume + JD text + prompt scaffolding in, strict-JSON response out) —
override with --avg-input-tokens/--avg-output-tokens if you have better numbers
from a pilot run (analysis/pilot.py reports realistic token counts on real calls).

Each (JD, model, ablation, rep) produces 2 calls — condition A and condition B.

Usage:
    python3 scripts/estimate_cost.py --jds 20 --reps 3 --ablations 2
    python3 scripts/estimate_cost.py --jds 20 --reps 3 --ablations 2 --models claude-haiku-4-5
"""
import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jds", type=int, required=True)
    ap.add_argument("--reps", type=int, required=True)
    ap.add_argument("--ablations", type=int, default=2)
    ap.add_argument("--models", type=str, default=None, help="comma-separated model keys, default = all in config")
    ap.add_argument("--avg-input-tokens", type=int, default=900)
    ap.add_argument("--avg-output-tokens", type=int, default=160)
    args = ap.parse_args()

    cfg = yaml.safe_load((ROOT / "config" / "config.yaml").read_text())
    model_keys = args.models.split(",") if args.models else [m["key"] for m in cfg["models"]]
    models = [m for m in cfg["models"] if m["key"] in model_keys]

    calls_per_model = args.jds * args.ablations * args.reps * 2  # A + B
    print(f"{args.jds} JDs x {args.ablations} ablations x {args.reps} reps x 2 conditions "
          f"= {calls_per_model} calls per model\n")

    total = 0.0
    for m in models:
        per_call = (
            args.avg_input_tokens / 1_000_000 * m["price_input_per_1m"]
            + args.avg_output_tokens / 1_000_000 * m["price_output_per_1m"]
        )
        model_total = per_call * calls_per_model
        total += model_total
        print(f"  {m['key']:20s} {calls_per_model:5d} calls x ${per_call:.5f}/call = ${model_total:.2f}")

    print(f"\nTotal projected cost: ${total:.2f}")
    print("(Prices in config/config.yaml are placeholders — verify against current provider "
          "pricing pages before a real run.)")


if __name__ == "__main__":
    main()
