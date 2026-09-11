#!/usr/bin/env python3
"""
Generate résumé variant B for each ablation, from the résumé-A text named in
config/config.yaml's paths.resume_a (default resume/v4_2_A.txt as of 2026-09-10;
override with --txt for a one-off run against a different file).

Ablation 1 — institution_swap: replace every employer/institution proper noun
with its fictional match from config/swap_map.yaml. Descriptor lines are left
untouched; only the literal name is swapped (whole-phrase, case-sensitive).

Ablation 2 — evidence_links: strip every occurrence of the résumé's evidence
domains (linkedin.com, zoebnomi.com, github.com — with or without a
"https://"/"www." prefix) from the résumé text, wherever they appear (header
profile-links row, the CrossSource project-link column, or inline in a
sentence). As of v4.2 these appear as bare visible text with no "http(s)://"
scheme — see reports/parser_test.md "What surprised me" (v4.1) for why the
older https?://-only regex was a no-op on this résumé and had to be replaced.

Output filenames are derived from the input file's name: "<prefix>_A.txt" ->
"<prefix>_B_institution_swap.txt" and "<prefix>_B_evidence_links.txt".

Usage:
    python3 scripts/make_variants.py
    python3 scripts/make_variants.py --txt resume/v4_1_A.txt
Writes (default):
    resume/v4_2_B_institution_swap.txt
    resume/v4_2_B_evidence_links.txt
"""
import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.yaml"
SWAP_MAP = ROOT / "config" / "swap_map.yaml"

# Matches the résumé's evidence domains with an optional scheme/www prefix, e.g.
# "https://www.linkedin.com/in/zoebnomi", "linkedin.com/in/zoebnomi",
# "zoebnomi.com", "github.com/zoeb-nomi/crosssource" — stops at whitespace or
# the "·" column separator so it doesn't eat the text around it.
DOMAIN_RE = re.compile(
    r"(?:https?://)?(?:www\.)?(?:linkedin\.com|zoebnomi\.com|github\.com)(?:/[^\s·]*)?",
    re.IGNORECASE,
)


def load_config():
    return yaml.safe_load(CONFIG_PATH.read_text())


def make_institution_swap(text: str, swap_map: dict) -> str:
    out = text
    for swap in swap_map["swaps"]:
        real = swap["real_name"]
        fake = swap["fictional_name"]
        # Whole-phrase, case-sensitive literal replacement. Word-boundary guarded
        # so "Instead" doesn't clobber "instead" used as an ordinary word elsewhere
        # (it doesn't appear as such in the résumé text, but guard anyway).
        pattern = re.compile(r"\b" + re.escape(real) + r"\b")
        n = len(pattern.findall(out))
        if n == 0:
            print(f"WARNING: '{real}' not found in resume text — swap had no effect", file=sys.stderr)
        out = pattern.sub(fake, out)
    return out


def make_evidence_links(text: str) -> str:
    """Strip every evidence-link domain occurrence, replacing each with
    "[link removed]" in place — evidence is gone, not silently smoothed over."""
    return DOMAIN_RE.sub("[link removed]", text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--txt", type=str, default=None,
                     help="résumé-A text file to generate variants from "
                          "(default: paths.resume_a in config/config.yaml)")
    args = ap.parse_args()

    cfg = load_config()
    resume_a_path = ROOT / (args.txt or cfg["paths"]["resume_a"])
    if not resume_a_path.name.endswith("_A.txt"):
        sys.exit(f"expected a '..._A.txt' file, got {resume_a_path.name}")
    prefix = resume_a_path.name[: -len("_A.txt")]

    text = resume_a_path.read_text()
    swap_map = yaml.safe_load(SWAP_MAP.read_text())

    b_institution = make_institution_swap(text, swap_map)
    b_evidence = make_evidence_links(text)

    out_institution = ROOT / "resume" / f"{prefix}_B_institution_swap.txt"
    out_evidence = ROOT / "resume" / f"{prefix}_B_evidence_links.txt"
    out_institution.write_text(b_institution)
    out_evidence.write_text(b_evidence)

    print(f"Wrote {out_institution.relative_to(ROOT)}")
    print(f"Wrote {out_evidence.relative_to(ROOT)}")

    if b_institution == text:
        print("WARNING: institution_swap variant is byte-identical to A — ablation would be a no-op", file=sys.stderr)
    else:
        print(f"institution_swap variant differs from A: {'yes' if b_institution != text else 'no'}")

    if b_evidence == text:
        print("WARNING: evidence_links variant is byte-identical to A — ablation would be a no-op", file=sys.stderr)
    else:
        stripped = DOMAIN_RE.findall(text)
        print(f"evidence_links variant differs from A: yes — {len(stripped)} domain occurrence(s) stripped:")
        for m in DOMAIN_RE.finditer(text):
            print(f"  - {m.group(0)!r}")

    # sanity: confirm no real institution name leaks into the swapped variant,
    # and no evidence-domain string survives in the evidence-stripped variant
    for swap in swap_map["swaps"]:
        assert swap["real_name"] not in b_institution or swap["real_name"] in [
            s["fictional_name"] for s in swap_map["swaps"]
        ], f"real name '{swap['real_name']}' leaked into institution_swap variant"
    assert not DOMAIN_RE.search(b_evidence), "an evidence-link domain survived evidence_links stripping"
    print("Sanity checks passed.")


if __name__ == "__main__":
    main()
