# Parser test — resume/v4_2.pdf vs canon/resume_fields.yaml

Real, deterministic run — no LLM involved anywhere in this test. Five parsers, the résumé PDF, one canon file. Definitions of MISSING / WRONG / GARBLED are in the docstring of `parser_test/run_parsers.py`; short version: MISSING = value not found anywhere; WRONG = the field's slot holds something, and it's not the right value (structured parsers only — raw text dumps have no slots to mislabel); GARBLED = the correct value is present but fused into a larger blob, unusable as a clean field value; unlabeled = correct and cleanly isolated.

**This run uses résumé v4.2** (`resume/v4_2.pdf`), which changes exactly one thing vs. v4.1 (`resume/v4_1_real.pdf`): the header's right-hand column now prints the three profile URLs as visible plain text — `linkedin.com/in/zoebnomi · zoebnomi.com · github.com/zoeb-nomi` — replacing the bare, hyperlink-annotation-only labels `LinkedIn · Portfolio · GitHub` that v4.1 used. `diff resume/v4_1_A.txt resume/v4_2_A.txt` confirms that's the *only* line that changed — summary, all four roles' bullets, the CrossSource project, skills, and education are byte-identical between the two files. `canon/resume_fields.yaml`'s three link fields were updated to match what's now actually printed (bare domain, no `https://`/`www.` — see the file's header comment for why). The v4.1 real-PDF run this compares against is archived at `reports/parser_test_v4_1_real.md`.

## Before/after — v4.1 real PDF vs. v4.2 (per parser, 29 core fields)

| parser | v4.1 ok/missing/wrong/garbled | v4.2 ok/missing/wrong/garbled | what changed |
|---|---|---|---|
| pdftotext | 26 / 3 / 0 / 0 | **29 / 0 / 0 / 0** | all 3 link fields flipped missing → ok |
| PyMuPDF | 26 / 3 / 0 / 0 | **29 / 0 / 0 / 0** | all 3 link fields flipped missing → ok |
| pdfminer.six | 26 / 3 / 0 / 0 | **29 / 0 / 0 / 0** | all 3 link fields flipped missing → ok |
| resumix (npm) | 7 / 9 / 12 / 1 | 9 / 8 / 11 / 1 | linkedin + github missing → ok; portfolio (`zoebnomi.com`) stays missing; `contact.name` flipped wrong → missing (still broken, differently) |
| resume-parser (npm) | 2 / 4 / 1 / 22 | 2 / 2 / 1 / 24 | linkedin + github missing → garbled (recovered, but fused into one unlabeled blob); portfolio stays missing |

Skills coverage is unchanged for every parser (37/39 resumix, 39/39 the other four) — the skills section is untouched between v4.1 and v4.2.

## Do all three links now survive? Per parser

| parser | linkedin | portfolio | github | verdict |
|---|---|---|---|---|
| pdftotext | ok | ok | ok | **all 3 survive, cleanly** |
| PyMuPDF | ok | ok | ok | **all 3 survive, cleanly** |
| pdfminer.six | ok | ok | ok | **all 3 survive, cleanly** |
| resumix (npm) | ok | missing | ok | **2 of 3** — `contact.linkedin`/`contact.github` populated correctly; no `portfolio`/`website` key exists in its output schema at all, so `zoebnomi.com` has nowhere to land even though it's sitting right there in the text (confirmed in `parser_test/output/resumix.json`) |
| resume-parser (npm) | garbled | missing | garbled | **0 of 3 cleanly** — its `profiles` field is a single unlabeled, unseparated string: `"github.com/zoeb-nomilinkedin.com/in/zoebnomigithub.com/zoeb-nomi/crosssource"` (three URLs concatenated with no delimiter). `linkedin`/`github` count as recovered-but-unusable (garbled); `zoebnomi.com` isn't in that blob at all and is missing outright |

So: the three raw-text extractors go from 0/3 to 3/3 the moment the URLs are visible text instead of annotation-only — exactly as expected, since none of them read link annotations. The two structured, résumé-aware parsers only *partially* benefit: both have a schema/regex blind spot for a bare `.com` domain that isn't `linkedin.com` or `github.com` shaped, so `zoebnomi.com` (the portfolio link) is invisible to both regardless of whether it's printed as text.

## Does the two-column header still confuse resumix?

Yes, unchanged in kind. The header layout — line 1 `ZOEB NOMI` (left) + location/phone/email (right); line 2 title (left) + profile links (right) — is identical in v4.1 and v4.2; only the *content* of line 2's right column changed (labels → URLs), which is orthogonal to the layout confusion. Evidence from `parser_test/output/resumix.json`:

- `contact.name` is **missing** (no name field populated at all — a change from v4.1, where it mis-captured the second header line's text as the name; here it apparently gives up entirely rather than mis-attributing).
- `contact.phone` is **wrong** — captured as `"+91"` only, the number truncated exactly as it was on v4.1 real.
- `contact.location` is **missing**, same as v4.1 real.
- Experience is still fragmented into far more than 4 entries (unchanged root cause, unrelated to the header).

Net: resumix's two-column-header sensitivity is a pre-existing, unresolved parser limitation independent of the evidence-links change — v4.2 doesn't fix or worsen it, it's simply not what the URL-visibility change touched.

## What this shows

Printing the URLs as visible header text (v4.2) is a real, unambiguous improvement for the three general-purpose text extractors — they go from silently dropping every profile link to recovering all three, because the fix addresses their actual limitation (none of them read PDF link annotations). It's a smaller, partial win for the two résumé-specific parsers: `resumix` and `resume-parser` both still fail to capture the portfolio link, not because it's invisible anymore but because neither tool's schema/pattern-matching expects a bare, non-branded `.com` domain as a profile URL — a different, parser-specific limitation that visible text alone doesn't fix. Practically, for an ATS/LLM screener that reads visible text only (which is the majority case — see `reports/parser_test_v4_1_real.md`'s "What surprised me" section on how link-annotation-only URLs made the evidence-links ablation a no-op): v4.2 is the resume to use. It also finally makes Ablation 2 (evidence-links) a real, non-trivial A/B contrast — see below.

## Evidence-links ablation: now a real contrast, not a no-op

On v4.1's extracted text, `scripts/make_variants.py`'s evidence-links ablation was a documented no-op (see `reports/parser_test_v4_1_real.md`, "What surprised me") — there were no visible `http(s)://` URLs to strip, so condition A and B were textually identical. v4.2 fixes this from the résumé side (URLs are now visible plain text), but `make_variants.py`'s stripping logic needed a matching fix: the old regex (`https?://\S+`) only matched scheme-prefixed URLs, and v4.2's printed URLs have no scheme (`linkedin.com/in/zoebnomi`, not `https://...`). It's rewritten to match the résumé's evidence domains (`linkedin.com`, `zoebnomi.com`, `github.com`) with or without a scheme/`www.` prefix. Re-running `python3 scripts/make_variants.py` against `resume/v4_2_A.txt` now strips 4 occurrences and produces a real diff:

```
2c2
< AI Product Manager · LLM Evaluation, Ground-Truth Data & RAG Quality         linkedin.com/in/zoebnomi · zoebnomi.com · github.com/zoeb-nomi
---
> AI Product Manager · LLM Evaluation, Ground-Truth Data & RAG Quality         [link removed] · [link removed] · [link removed]
69c69
< CrossSource - eval harness for citation-level reliability of legal RAG​                     github.com/zoeb-nomi/crosssource
---
> CrossSource - eval harness for citation-level reliability of legal RAG​                     [link removed]
```

`resume/v4_2_B_evidence_links.txt` now differs from `resume/v4_2_A.txt` in exactly those two lines (header profile links + CrossSource repo link), nothing else — confirmed by `diff`. `scripts/run_screen.py --ablation evidence_links` will send genuinely different resumé text for A vs. B for the first time.

## Exact commands run

```bash
pdftotext -layout resume/v4_2.pdf -
python3 -c "import pymupdf; ..."   # parser_test/run_parsers.py:run_pymupdf
python3 -c "from pdfminer.high_level import extract_text; ..."   # run_pdfminer
cd parser_test/node && npm install   # pins resumix@1.1.2, resume-parser@1.1.0, mime@1.6.0
node parser_test/node/run_resumix.js resume/v4_2.pdf parser_test/output/resumix.json
node parser_test/node/run_resume_parser.js resume/v4_2.pdf parser_test/output/resume_parser_raw
```

## Summary — error counts per parser (29 core contact/role/education fields)

| parser | ok | missing | wrong | garbled | skills found / 39 |
|---|---|---|---|---|---|
| pdftotext | 29 | 0 | 0 | 0 | 39 / 39 |
| PyMuPDF | 29 | 0 | 0 | 0 | 39 / 39 |
| pdfminer.six | 29 | 0 | 0 | 0 | 39 / 39 |
| resumix (npm) | 9 | 8 | 11 | 1 | 37 / 39 |
| resume-parser (npm) | 2 | 2 | 1 | 24 | 39 / 39 |

## Field-level detail

| field | expected | pdftotext | PyMuPDF | pdfminer.six | resumix (npm) | resume-parser (npm) |
|---|---|---|---|---|---|---|
| contact.name | Zoeb Nomi | ok | ok | ok | missing | wrong |
| contact.email | zoeb.nomi@gmail.com | ok | ok | ok | ok | ok |
| contact.phone | +91 86008 16072 | ok | ok | ok | wrong | ok |
| contact.location | Bengaluru, India | ok | ok | ok | missing | missing |
| contact.linkedin | linkedin.com/in/zoebnomi | ok | ok | ok | ok | garbled |
| contact.portfolio | zoebnomi.com | ok | ok | ok | missing | missing |
| contact.github | github.com/zoeb-nomi | ok | ok | ok | ok | garbled |
| role[0].company | Instead | ok | ok | ok | wrong | garbled |
| role[0].title | Product Manager | ok | ok | ok | wrong | garbled |
| role[0].start | Sept 2025 | ok | ok | ok | wrong | garbled |
| role[0].end | Present | ok | ok | ok | wrong | garbled |
| role[1].company | Multiplier | ok | ok | ok | wrong | garbled |
| role[1].title | Product Manager | ok | ok | ok | wrong | garbled |
| role[1].start | Mar 2025 | ok | ok | ok | ok | garbled |
| role[1].end | Sept 2025 | ok | ok | ok | ok | garbled |
| role[2].company | Keka HR | ok | ok | ok | wrong | garbled |
| role[2].title | Product Manager | ok | ok | ok | wrong | garbled |
| role[2].start | Dec 2022 | ok | ok | ok | ok | garbled |
| role[2].end | Mar 2025 | ok | ok | ok | ok | garbled |
| role[3].company | Hurix Digital | ok | ok | ok | wrong | garbled |
| role[3].title | Business Analyst | ok | ok | ok | wrong | garbled |
| role[3].start | Oct 2021 | ok | ok | ok | ok | garbled |
| role[3].end | Oct 2022 | ok | ok | ok | ok | garbled |
| education[0].institution | STOA | ok | ok | ok | missing | garbled |
| education[0].credential | General Management Program | ok | ok | ok | missing | garbled |
| education[0].year | 2022 | ok | ok | ok | garbled | garbled |
| education[1].institution | MIT Aurangabad | ok | ok | ok | missing | garbled |
| education[1].credential | B.E., Mechanical Engineering | ok | ok | ok | missing | garbled |
| education[1].year | 2019 | ok | ok | ok | missing | garbled |

## What I tried that didn't work

Five candidates beyond the three raw-text extractors were evaluated before settling on
`resumix` and `resume-parser` (both npm). In order:

1. **`pyresparser` (PyPI, 1.0.6)** — the best-known "open-source résumé parser" package.
   Installs, but is fundamentally broken on current spaCy/Python:
   - Its bundled custom NER model (`pyresparser/en_training/`) ships in spaCy 2.x's
     serialization format (`meta.json` + separate `ner/`/`vocab/`/`tokenizer` files, no
     `config.cfg`). spaCy 3.x's model loader requires `config.cfg` and refuses to load
     it: `OSError: [E053] Could not read config file from .../pyresparser/config.cfg`.
   - Monkeypatching `spacy.load` to substitute `en_core_web_sm` for the broken bundled
     model gets past that error, but then `pyresparser/utils.py` calls
     `matcher.add('NAME', None, *pattern)` — the 3-positional-argument spaCy **2.x**
     `Matcher.add()` signature, which spaCy 3.x's `Matcher.add()` (2-argument) rejects
     outright: `TypeError: add() takes exactly 2 positional arguments (3 given)`.
   - Verdict: not fixable without vendoring and patching the library's internals past
     two separate spaCy 2.x→3.x breaking changes. Unmaintained since spaCy 2.x era.

2. **`resume-parser` (PyPI, 0.8.4)** — same family/lineage as pyresparser (shares the
   same author's approach). Two separate failures:
   - `pip install` fails outright: a transitive dependency, `stemming==1.0.1`, has no
     wheel on PyPI and its `setup.py` (`bdist_wheel` → `install_lib.finalize_options`)
     hits a modern-setuptools incompatibility (`AttributeError: install_layout`).
     Worked around by hand-copying the (pure-Python, 13KB) `stemming` package into
     site-packages directly, then `pip install --no-deps resume-parser` plus its
     remaining real deps (`phonenumbers`, `tika`).
   - Once importable, it fails identically to pyresparser: it ships its own bundled
     spaCy 2.x-format NER models (`resume_parser/degree/model/`,
     `resume_parser/company_working/model/`) with no `config.cfg` —
     `OSError: [E053]`. Same root cause, same verdict.

3. **`pyresumeparser` (PyPI, 0.0.9, aka "PyResumeParser")** — a newer (spaCy 3.7 /
   spacy-transformers) rewrite. Installs (pulls in `torch`, `spacy-transformers`;
   this downgraded the environment's `spacy` 3.8.16→3.7.4 and `numpy`/`pdfminer.six`
   to versions pinned by its dependency tree — noted here since that's why the parser
   test was run and captured in one sitting, before any dependency drift could affect
   the three raw-text extractors' results above). At runtime it tries to download a
   custom NER model from `huggingface.co` on first use
   (`pyresumeparser/main.py:download_model()`); this sandboxed environment's egress
   policy blocks that host (`403 Forbidden` on the CONNECT tunnel). Untested beyond
   that point — likely to work on a machine with unrestricted internet access (the
   owner's Mac), since the code path itself looks sound. Not counted as "working"
   here because it could not actually be run end-to-end in this environment.

4. **`simple-resume-parser` (npm, 1.1.8)** — installs and runs out of the box with no
   workarounds, but it turned out to be a fork of the exact same underlying library
   as `resume-parser` (npm) — same `ParseBoy`/`processing.js` core, same dependency
   set (`cheerio`, `textract`, `tracer`, `underscore`), and it produced **byte-identical
   field output** on this résumé. Not included as the 5th parser because it isn't an
   independent implementation — including it alongside `resume-parser` (npm) would
   double-count one codebase as two data points, not five.

5. **`resumix` (npm, 1.1.2)** — worked immediately, no workarounds. Chosen as parser #4.

**Final lineup**: `resumix` (npm) worked cleanly; `resume-parser` (npm) needed two
documented workarounds (see `parser_test/node/run_resume_parser.js` docstring —
its own `index.js` calls a function that doesn't exist in `parseIt.js`, and a
transitive `mime` dependency needs to resolve to two different major versions
simultaneously in different parts of the dependency tree, which plain `npm install`
of a pinned `mime@1.6.0` direct dependency happens to produce via nested
`node_modules`, without forcing an `overrides` block that would break the other copy).

## Earlier rounds, archived

- **v4.1, text-only reconstruction vs. v4.1 real PDF**: see `reports/parser_test_reconstructed_2026-09-10.md`.
- **v4.1 real PDF** (links as hyperlink-annotations-only, no visible URL text — the
  round this v4.2 report is compared against above): see
  `reports/parser_test_v4_1_real.md`, including its "What surprised me" finding that
  the evidence-links ablation was a no-op on that file (fixed in this v4.2 round, see
  above).
