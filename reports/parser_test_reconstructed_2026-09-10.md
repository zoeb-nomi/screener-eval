# Parser test — resume/v4_1.pdf vs canon/resume_fields.yaml

Real, deterministic run — no LLM involved anywhere in this test. Five parsers, the résumé PDF, one canon file. Definitions of MISSING / WRONG / GARBLED are in the docstring of `parser_test/run_parsers.py`; short version: MISSING = value not found anywhere; WRONG = the field's slot holds something, and it's not the right value (structured parsers only — raw text dumps have no slots to mislabel); GARBLED = the correct value is present but fused into a larger blob, unusable as a clean field value; unlabeled = correct and cleanly isolated.

**Note (2026-09-10): this run used `resume/v4_1.pdf` when that file was a reconstruction** — rebuilt from résumé text pulled via `project_read`, not the real Google Docs export Zoeb actually uploads to ATSs. It is archived here for comparison after the real PDF (`resume/v4_1_real.pdf` at the time, now `resume/v4_1.pdf`) replaced it. See `reports/parser_test.md` for the current, real-PDF run and the reconstructed-vs-real comparison.

## Exact commands run

```bash
pdftotext -layout resume/v4_1.pdf -
python3 -c "import pymupdf; ..."   # parser_test/run_parsers.py:run_pymupdf
python3 -c "from pdfminer.high_level import extract_text; ..."   # run_pdfminer
cd parser_test/node && npm install   # pins resumix@1.1.2, resume-parser@1.1.0, mime@1.6.0
node parser_test/node/run_resumix.js resume/v4_1.pdf parser_test/output/resumix.json
node parser_test/node/run_resume_parser.js resume/v4_1.pdf parser_test/output/resume_parser_raw
```

## Summary — error counts per parser (29 core contact/role/education fields)

| parser | ok | missing | wrong | garbled | skills found / 39 |
|---|---|---|---|---|---|
| pdftotext | 29 | 0 | 0 | 0 | 39 / 39 |
| PyMuPDF | 29 | 0 | 0 | 0 | 39 / 39 |
| pdfminer.six | 29 | 0 | 0 | 0 | 39 / 39 |
| resumix (npm) | 11 | 5 | 12 | 1 | 37 / 39 |
| resume-parser (npm) | 2 | 2 | 1 | 24 | 39 / 39 |

## Field-level detail

| field | expected | pdftotext | PyMuPDF | pdfminer.six | resumix (npm) | resume-parser (npm) |
|---|---|---|---|---|---|---|
| contact.name | Zoeb Nomi | ok | ok | ok | ok | wrong |
| contact.email | zoeb.nomi@gmail.com | ok | ok | ok | ok | ok |
| contact.phone | +91 86008 16072 | ok | ok | ok | wrong | ok |
| contact.location | Bengaluru, India | ok | ok | ok | wrong | missing |
| contact.linkedin | https://www.linkedin.com/in/zoebnomi | ok | ok | ok | ok | garbled |
| contact.portfolio | https://zoebnomi.com | ok | ok | ok | ok | missing |
| contact.github | https://github.com/zoeb-nomi | ok | ok | ok | ok | garbled |
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

## Reading the results

The three raw-text extractors (pdftotext, PyMuPDF, pdfminer.six) get every field
right on this résumé — it's a clean, single-column, no-table PDF, which is exactly
the case raw text extraction handles well. That's a real, if unglamorous, finding:
for a résumé like this one, the "dumbest" tool in the test is also the most reliable
one. Where it would predictably fail — multi-column layouts, tables, text boxes — is
untested here; this résumé doesn't have any.

The two résumé-*specific* parsers both do meaningfully worse than plain text
extraction, in different ways:
- `resumix` fragments the "Experience" section into 19 disconnected entries instead
  of 4 (one per bullet, roughly), which is why company/title/start/end for the first
  role all come back `wrong` — the fields exist and are populated, just with content
  from the wrong bullet. Education and skills sections were not detected at all
  (both came back empty arrays) despite being present and well-labeled in the PDF.
- `resume-parser` (npm) barely segments past top-level sections (`name`, `email`,
  `phone`, `profiles`, `summary`, `experience`, `projects`, `skills`, `education` —
  9 keys total, no per-role or per-degree structure), so every role- and
  education-level field is `garbled`: technically present as a substring of one
  giant blob, not usable as a clean field on its own.

Neither result should be surprising in hindsight — this is the literal thing an
eval-driven case study should show, not assume: shrink-wrapped open-source résumé
parsers, run for real against a real résumé, do worse than `pdftotext -layout` on
a document simple enough that pdftotext has no trouble with it.

**Caveat this run did not know it needed:** this résumé was a plain-headings-and-bullets
reconstruction of Zoeb's résumé *text*, not the actual Google Docs PDF export he
uploads to ATSs. It had no two-column header, no hyperlink annotations, no curly
typography — all of which the real export turns out to have. See
`reports/parser_test.md` for what changed once the real file was used.
