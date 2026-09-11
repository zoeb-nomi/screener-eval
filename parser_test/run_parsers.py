#!/usr/bin/env python3
"""
Real, deterministic parser test. Runs resume/v4_1.pdf through:

  1. pdftotext (poppler-utils)          -- raw text extraction
  2. PyMuPDF (pymupdf/fitz)             -- raw text extraction
  3. pdfminer.six                       -- raw text extraction
  4. resumix (npm)                      -- structured résumé parser
  5. resume-parser (npm)                -- structured(ish) résumé parser

...for real (subprocess / library calls, no mocking here — this is the one part
of screener-eval that needs no API keys and produces its own ground truth), then
scores every parser's output against canon/resume_fields.yaml.

Definitions (used consistently for every parser):
  MISSING  — the canon field's value does not appear anywhere in the parser's
             output, in any recognizable form.
  WRONG    — the parser put SOME non-empty value in this field's slot (for the
             two structured parsers) or the correct value was found attributed
             to a semantically different field, and that value is not the
             correct one (structured parsers only — a raw text dump has no
             field slots to get wrong).
  GARBLED  — the correct value is present in the output but only as a substring
             fused into a much larger blob (line-wrap/hyphenation artifacts in
             the three text extractors; a giant unsegmented "experience"/
             "description" string in the structured parsers) — not usable as a
             clean field value by a downstream system.
  (unlabeled = OK) — the value is present, correct, and cleanly isolated.

Usage:
    python3 parser_test/run_parsers.py                          # default: resume/v4_2.pdf
    python3 parser_test/run_parsers.py --pdf resume/v4_1_real.pdf
Writes:
    parser_test/output/*                  (raw parser outputs, for inspection)
    reports/parser_test.md
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CANON_PATH = ROOT / "canon" / "resume_fields.yaml"
OUT_DIR = ROOT / "parser_test" / "output"
NODE_DIR = ROOT / "parser_test" / "node"
RESUME_PDF = ROOT / "resume" / "v4_2.pdf"  # overridden by --pdf in main()


def normalize(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_tight(s: str) -> str:
    """whitespace/hyphen-insensitive form, to detect line-wrap/hyphenation mangling"""
    s = normalize(s)
    return re.sub(r"[\s\-]+", "", s)


# ---------------------------------------------------------------------------
# Step 1: run the three raw-text extractors for real
# ---------------------------------------------------------------------------

def run_pdftotext() -> str:
    out = subprocess.run(
        ["pdftotext", "-layout", str(RESUME_PDF), "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    (OUT_DIR / "pdftotext.txt").write_text(out)
    return out


def run_pymupdf() -> str:
    import pymupdf
    doc = pymupdf.open(str(RESUME_PDF))
    out = "\n".join(page.get_text() for page in doc)
    (OUT_DIR / "pymupdf.txt").write_text(out)
    return out


def run_pdfminer() -> str:
    from pdfminer.high_level import extract_text
    out = extract_text(str(RESUME_PDF))
    (OUT_DIR / "pdfminer.txt").write_text(out)
    return out


# ---------------------------------------------------------------------------
# Step 2: run the two npm résumé parsers for real (subprocess -> node)
# ---------------------------------------------------------------------------

def run_resumix() -> dict:
    out_file = OUT_DIR / "resumix.json"
    subprocess.run(
        ["node", "run_resumix.js", str(RESUME_PDF), str(out_file)],
        cwd=str(NODE_DIR), check=True, capture_output=True, text=True,
    )
    return json.loads(out_file.read_text())


def run_resume_parser() -> dict:
    out_dir = OUT_DIR / "resume_parser_raw"
    subprocess.run(
        ["node", "run_resume_parser.js", str(RESUME_PDF), str(out_dir)],
        cwd=str(NODE_DIR), check=True, capture_output=True, text=True,
    )
    out_file = out_dir / (RESUME_PDF.name + ".json")
    return json.loads(out_file.read_text())


# ---------------------------------------------------------------------------
# Canon fields -> flat field list
# ---------------------------------------------------------------------------

def flatten_canon(canon: dict):
    fields = []
    fields.append(("contact.name", canon["name"]))
    fields.append(("contact.email", canon["email"]))
    fields.append(("contact.phone", canon["phone"]))
    fields.append(("contact.location", canon["location"]))
    fields.append(("contact.linkedin", canon["links"]["linkedin"]))
    fields.append(("contact.portfolio", canon["links"]["portfolio"]))
    fields.append(("contact.github", canon["links"]["github"]))
    for i, role in enumerate(canon["roles"]):
        fields.append((f"role[{i}].company", role["company"]))
        fields.append((f"role[{i}].title", role["title"]))
        fields.append((f"role[{i}].start", role["start"]))
        fields.append((f"role[{i}].end", role["end"]))
    for i, edu in enumerate(canon["education"]):
        fields.append((f"education[{i}].institution", edu["institution"]))
        fields.append((f"education[{i}].credential", edu["credential"]))
        fields.append((f"education[{i}].year", edu["year"]))
    return fields


CATEGORY_KEYPATH_PATTERNS = {
    "contact.name": [r"\bname\b"],
    "contact.email": [r"email"],
    "contact.phone": [r"phone"],
    "contact.location": [r"location|address|city"],
    "contact.linkedin": [r"linkedin"],
    "contact.portfolio": [r"website|portfolio"],
    "contact.github": [r"github"],
    "role.company": [r"company"],
    "role.title": [r"title|designation|position"],
    "role.start": [r"start"],
    "role.end": [r"end(?!orse)"],
    "education.institution": [r"institution|college|school"],
    "education.credential": [r"degree|credential"],
    "education.year": [r"year"],
}


def category_for(field_name: str) -> str:
    if field_name.startswith("role["):
        return "role." + field_name.split(".", 1)[1]
    if field_name.startswith("education["):
        return "education." + field_name.split(".", 1)[1]
    return field_name


# ---------------------------------------------------------------------------
# Scoring: raw-text extractors
# ---------------------------------------------------------------------------

def score_text_extractor(fields, text: str):
    haystack = normalize(text)
    haystack_tight = normalize_tight(text)
    results = {}
    for name, expected in fields:
        exp_n = normalize(expected)
        exp_tight = normalize_tight(expected)
        if exp_n in haystack:
            results[name] = "ok"
        elif exp_tight in haystack_tight:
            results[name] = "garbled"
        else:
            results[name] = "missing"
    return results


# ---------------------------------------------------------------------------
# Scoring: structured JSON parsers
# ---------------------------------------------------------------------------

def flatten_json(obj, prefix=""):
    """yield (keypath, string_value) for every string leaf"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten_json(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten_json(v, f"{prefix}[{i}]")
    elif isinstance(obj, str) and obj.strip():
        yield (prefix, obj)
    elif isinstance(obj, bool):
        return
    # ints/None/etc: not a string leaf, skip


def score_structured_parser(fields, data: dict):
    leaves = list(flatten_json(data))
    results = {}
    for name, expected in fields:
        exp_n = normalize(expected)
        category = category_for(name)
        patterns = CATEGORY_KEYPATH_PATTERNS.get(category, [])

        designated = [
            (k, v) for k, v in leaves
            if any(re.search(p, k, re.IGNORECASE) for p in patterns)
        ]

        # 1. exact match under a designated (semantically appropriate) keypath
        if any(normalize(v) == exp_n for k, v in designated):
            results[name] = "ok"
            continue

        # 2. designated slot has SOME non-empty value, but not the right one
        if designated:
            results[name] = "wrong"
            continue

        # 3. exact match found, but under a keypath we didn't expect (mislabeled)
        if any(normalize(v) == exp_n for k, v in leaves):
            results[name] = "wrong"
            continue

        # 4. correct value present only as a substring inside a much larger blob
        substring_hit = any(
            exp_n in normalize(v) and len(v) > len(expected) * 1.4
            for k, v in leaves
        )
        if substring_hit:
            results[name] = "garbled"
            continue

        results[name] = "missing"
    return results


# ---------------------------------------------------------------------------
# Skills coverage (aggregate, not per-field)
# ---------------------------------------------------------------------------

def score_skills_text(skills, text: str):
    haystack = normalize(text)
    found = sum(1 for s in skills if normalize(s) in haystack)
    return found, len(skills)


def score_skills_structured(skills, data: dict):
    leaves = list(flatten_json(data))
    blob = normalize(" ".join(v for k, v in leaves))
    found = sum(1 for s in skills if normalize(s) in blob)
    return found, len(skills)


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def summarize(results: dict):
    counts = {"ok": 0, "missing": 0, "wrong": 0, "garbled": 0}
    for v in results.values():
        counts[v] += 1
    return counts


def render_report(fields, all_results, skills_coverage, commands, resume_pdf_rel):
    lines = []
    lines.append(f"# Parser test — {resume_pdf_rel} vs canon/resume_fields.yaml\n")
    lines.append(
        "Real, deterministic run — no LLM involved anywhere in this test. Five parsers, "
        "the résumé PDF, one canon file. Definitions of MISSING / WRONG / GARBLED are in "
        "the docstring of `parser_test/run_parsers.py`; short version: MISSING = value not "
        "found anywhere; WRONG = the field's slot holds something, and it's not the right "
        "value (structured parsers only — raw text dumps have no slots to mislabel); "
        "GARBLED = the correct value is present but fused into a larger blob, unusable as "
        "a clean field value; unlabeled = correct and cleanly isolated.\n"
    )

    lines.append("## Exact commands run\n")
    lines.append("```bash")
    for c in commands:
        lines.append(c)
    lines.append("```\n")

    lines.append("## Summary — error counts per parser (29 core contact/role/education fields)\n")
    total_skills = next(iter(skills_coverage.values()))[1]
    lines.append(f"| parser | ok | missing | wrong | garbled | skills found / {total_skills} |")
    lines.append("|---|---|---|---|---|---|")
    for parser_name, results in all_results.items():
        c = summarize(results)
        sk_found, sk_total = skills_coverage[parser_name]
        lines.append(f"| {parser_name} | {c['ok']} | {c['missing']} | {c['wrong']} | {c['garbled']} | {sk_found} / {sk_total} |")
    lines.append("")

    lines.append("## Field-level detail\n")
    lines.append("| field | expected | " + " | ".join(all_results.keys()) + " |")
    lines.append("|---|---|" + "---|" * len(all_results))
    field_expected = dict(fields)
    for name, expected in fields:
        row = [name, expected.replace("|", "/")]
        for parser_name in all_results:
            row.append(all_results[parser_name][name])
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")

    return "\n".join(lines)


def main():
    global RESUME_PDF
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", type=str, default=None,
                     help="résumé PDF to run the five parsers against "
                          "(default: resume/v4_2.pdf)")
    args = ap.parse_args()
    if args.pdf:
        RESUME_PDF = ROOT / args.pdf
    resume_pdf_rel = RESUME_PDF.relative_to(ROOT).as_posix()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    canon = yaml.safe_load(CANON_PATH.read_text())
    fields = flatten_canon(canon)
    skills = canon["skills"]

    commands = [
        f"pdftotext -layout {resume_pdf_rel} -",
        "python3 -c \"import pymupdf; ...\"   # parser_test/run_parsers.py:run_pymupdf",
        "python3 -c \"from pdfminer.high_level import extract_text; ...\"   # run_pdfminer",
        "cd parser_test/node && npm install   # pins resumix@1.1.2, resume-parser@1.1.0, mime@1.6.0",
        f"node parser_test/node/run_resumix.js {resume_pdf_rel} parser_test/output/resumix.json",
        f"node parser_test/node/run_resume_parser.js {resume_pdf_rel} parser_test/output/resume_parser_raw",
    ]

    print("Running pdftotext...")
    text_pdftotext = run_pdftotext()
    print("Running PyMuPDF...")
    text_pymupdf = run_pymupdf()
    print("Running pdfminer.six...")
    text_pdfminer = run_pdfminer()
    print("Running resumix (npm)...")
    data_resumix = run_resumix()
    print("Running resume-parser (npm)...")
    data_resume_parser = run_resume_parser()

    all_results = {
        "pdftotext": score_text_extractor(fields, text_pdftotext),
        "PyMuPDF": score_text_extractor(fields, text_pymupdf),
        "pdfminer.six": score_text_extractor(fields, text_pdfminer),
        "resumix (npm)": score_structured_parser(fields, data_resumix),
        "resume-parser (npm)": score_structured_parser(fields, data_resume_parser),
    }

    skills_coverage = {
        "pdftotext": score_skills_text(skills, text_pdftotext),
        "PyMuPDF": score_skills_text(skills, text_pymupdf),
        "pdfminer.six": score_skills_text(skills, text_pdfminer),
        "resumix (npm)": score_skills_structured(skills, data_resumix),
        "resume-parser (npm)": score_skills_structured(skills, data_resume_parser),
    }

    report = render_report(fields, all_results, skills_coverage, commands, resume_pdf_rel)
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)
    out_path = reports_dir / "parser_test.md"
    # preserve the hand-authored "what I tried and what broke" section if present
    existing = out_path.read_text() if out_path.exists() else ""
    marker = "## What I tried that didn't work"
    tail = existing[existing.index(marker):] if marker in existing else ""
    out_path.write_text(report + ("\n" + tail if tail else ""))
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
