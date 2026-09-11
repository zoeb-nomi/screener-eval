# Parser test — resume/v4_1.pdf vs canon/resume_fields.yaml

Real, deterministic run — no LLM involved anywhere in this test. Five parsers, the résumé PDF, one canon file. Definitions of MISSING / WRONG / GARBLED are in the docstring of `parser_test/run_parsers.py`; short version: MISSING = value not found anywhere; WRONG = the field's slot holds something, and it's not the right value (structured parsers only — raw text dumps have no slots to mislabel); GARBLED = the correct value is present but fused into a larger blob, unusable as a clean field value; unlabeled = correct and cleanly isolated.

**This run uses the REAL résumé PDF** — the Google Docs export Zoeb actually uploads to ATSs (previously `resume/v4_1_real.pdf`, now `resume/v4_1.pdf`). The prior run used a reconstruction built from résumé *text* alone (no real layout, fonts, or link annotations); that report is archived at `reports/parser_test_reconstructed_2026-09-10.md` and compared below. `resume/v4_1_A.txt` and both `resume/v4_1_B_*.txt` variants were regenerated from the real PDF for this run.

## Exact commands run

```bash
# regenerate canon text source from the real PDF
pdftotext -layout resume/v4_1.pdf - | tr -d '\f' > resume/v4_1_A.txt
python3 scripts/make_variants.py

# node deps (parser_test/node/node_modules was missing, reinstalled)
cd parser_test/node && npm ci

# parser test itself
pdftotext -layout resume/v4_1.pdf -
python3 -c "import pymupdf; ..."   # parser_test/run_parsers.py:run_pymupdf
python3 -c "from pdfminer.high_level import extract_text; ..."   # run_pdfminer
node parser_test/node/run_resumix.js resume/v4_1.pdf parser_test/output/resumix.json
node parser_test/node/run_resume_parser.js resume/v4_1.pdf parser_test/output/resume_parser_raw
python3 parser_test/run_parsers.py
```

## Summary — error counts per parser (29 core contact/role/education fields)

| parser | ok | missing | wrong | garbled | skills found / 39 |
|---|---|---|---|---|---|
| pdftotext | 26 | 3 | 0 | 0 | 39 / 39 |
| PyMuPDF | 26 | 3 | 0 | 0 | 39 / 39 |
| pdfminer.six | 26 | 3 | 0 | 0 | 39 / 39 |
| resumix (npm) | 7 | 9 | 12 | 1 | 37 / 39 |
| resume-parser (npm) | 2 | 4 | 1 | 22 | 39 / 39 |

## Evidence links preserved (separate from the field score — this is what the evidence-links ablation depends on)

The résumé's header carries three profile links (LinkedIn, Portfolio, GitHub) plus one project link (CrossSource repo). In the real PDF, the header links are **hyperlink annotations only** — PyMuPDF's `page.get_links()` confirms all three (`https://www.linkedin.com/in/zoebnomi`, `https://zoebnomi.com`, `https://github.com/zoeb-nomi`) exist as clickable link objects, but the visible/extractable text under them is just the bare words "LinkedIn", "Portfolio", "GitHub" — no URL characters at all. The CrossSource project link is the opposite case: its URL *is* present as visible text, but without the `https://` scheme (`github.com/zoeb-nomi/crosssource`).

| parser | evidence links preserved | why |
|---|---|---|
| pdftotext | partial | 3 header profile URLs: 0/3 (annotation-only, not in text). CrossSource URL: present, scheme-less. |
| PyMuPDF (`.get_text()`) | partial | same as pdftotext — `get_text()` doesn't read link annotations; `get_links()` would, but the parser test doesn't call it. |
| pdfminer.six | partial | same as pdftotext. |
| resumix (npm) | no | CrossSource section wasn't segmented at all (`projects: []`); zero URL text of any kind, scheme-less or not, appears anywhere in its output. |
| resume-parser (npm) | partial | header profile URLs: 0/3. CrossSource URL string survives, scheme-less, in `profiles`. |

No parser recovers a single fully-formed, clickable URL. This directly undercuts the evidence-links ablation as currently built — see "What surprised me" below.

## Field-level detail

| field | expected | pdftotext | PyMuPDF | pdfminer.six | resumix (npm) | resume-parser (npm) |
|---|---|---|---|---|---|---|
| contact.name | Zoeb Nomi | ok | ok | ok | wrong | wrong |
| contact.email | zoeb.nomi@gmail.com | ok | ok | ok | ok | ok |
| contact.phone | +91 86008 16072 | ok | ok | ok | wrong | ok |
| contact.location | Bengaluru, India | ok | ok | ok | missing | missing |
| contact.linkedin | https://www.linkedin.com/in/zoebnomi | missing | missing | missing | missing | missing |
| contact.portfolio | https://zoebnomi.com | missing | missing | missing | missing | missing |
| contact.github | https://github.com/zoeb-nomi | missing | missing | missing | missing | missing |
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

## Per-parser errors specific to the real file

- **pdftotext / PyMuPDF / pdfminer.six** — identical error pattern across all three: the 3 profile-link fields (`contact.linkedin`, `.portfolio`, `.github`) are `missing`, and nothing else. Every other field (29 − 3 = 26) is `ok`. Confirmed by inspecting `parser_test/output/pdftotext.txt` / `pymupdf.txt` / `pdfminer.txt`: the header line reads `...LinkedIn · Portfolio · GitHub` with zero URL characters — the link data lives only in the PDF's annotation objects (verified via `PyMuPDF.page.get_links()`, which returns the three correct URIs even though `page.get_text()` doesn't).

- **resumix (npm)** — got measurably worse than on the reconstruction, for a new reason beyond its existing 19-way experience fragmentation:
  - `contact.name` is now `wrong`: it extracted `"AI Product Manager · LLM Evaluation, Ground-Truth Data & RAG Quality LinkedIn · Portfolio · GitHub"` as the name (the résumé's second header line, right-column contact labels included), not `"ZOEB NOMI"`. The real PDF's two-column header (name+location on one visual row, title+links on the next) broke whatever line-position heuristic resumix uses for name detection; the reconstruction's plain stacked-line header didn't trigger this.
  - `contact.phone` is `wrong`: it captured only `"+91"`, truncating the rest of the number — likely the same header-parsing confusion bleeding into phone extraction.
  - `contact.location` flipped from `wrong` (in the reconstruction) to `missing` here — no location value is populated at all now.
  - Education and skills are still empty arrays (unchanged from before) and experience is still fragmented into ~19 entries instead of 4 (unchanged root cause).

- **resume-parser (npm)** — `contact.name` came back as `"B N"` (two capital-letter tokens from somewhere in the header, not "Zoeb Nomi"). `contact.linkedin` and `contact.github`, which were `garbled` (found as a substring in a giant blob) on the reconstruction, are now `missing` outright — because the substring they used to be found in (the literal URLs) doesn't exist in this file's text at all. Its `profiles` field captured only `"github.com/zoeb-nomi/crosssource"` — the one link that is present as literal text — and nothing else, confirming the profile links are unrecoverable by this tool.

## Diff findings — real PDF vs. the reconstructed text (`resume/v4_1_A.txt` before this run)

`diff -u` between the old `resume/v4_1_A.txt` and `pdftotext -layout` output of the real PDF (cleaned of form feeds) shows the body content — every sentence, number, and bullet — is unchanged. All differences are Google-Docs-export artifacts of the same content, not new/different facts:

1. **Header profile links are hyperlink-annotation-only** (the headline finding — see "Evidence links preserved" above). No canon field value changed as a result; the *ground truth* (Zoeb's actual LinkedIn/portfolio/GitHub URLs) is unchanged, but no parser under test can recover it from this file's text layer.
2. **Two-column header layout.** Line 1 is `ZOEB NOMI` (left) + `Bengaluru, India · +91 86008 16072 · zoeb.nomi@gmail.com` (right); line 2 is the title (left) + the LinkedIn/Portfolio/GitHub labels (right) — merged onto shared lines by `-layout`'s column detection, rather than four separate stacked lines as in the reconstruction. This is what broke resumix's name/phone extraction (see above).
3. **Side-by-side education line.** `STOA - General Management Program (2022)` and `MIT Aurangabad - B.E., Mechanical Engineering (2019)` are on one physical line, column-separated by `·`, instead of two stacked lines. No field impact (both values still substring-match), but it's a second instance of the same two-column layout pattern.
4. **Page break lands inside the Experience section.** The real PDF is 2 pages; page 2 starts exactly at `Product Manager, Keka HR - 3 roles, 2 promotions`. `pdftotext` inserts a form-feed (`\f`) there, stripped before diffing/committing. No content was lost or reordered across the break in any of the three text extractors.
5. **Typography**: real export uses curly apostrophes (`Instead's` → `Instead’s`), en dashes for date ranges (`Sept 2025 – Present` vs `Sept 2025 - Present`), arrows in place of "to"/"→" in bullets (`flag → classify-by-failure-mode` vs `flag to classify-by-failure-mode`), `•` bullets instead of `-`, `&` instead of some "and"s, non-breaking/zero-width spaces after header labels, and `·` instead of `,` as the skills-list separator. None of this changed any of the 29 canon field values or their match outcomes — `normalize()` handles whitespace/case but was never asked to handle en dashes or curly quotes, since no field value contains them.
6. **Section order and content**: identical — SUMMARY → EXPERIENCE → OPEN-SOURCE PROJECTS → SKILLS & TOOLS → EDUCATION, same 4 roles, same 1 project, same dates, same numbers, same skills list.

**Canon changes made:** none to field *values* — every one of the 29 fields' ground-truth values was re-verified against the real PDF and is unchanged. `canon/resume_fields.yaml` got a documentation comment (dated 2026-09-10) recording that the real file is now the source and explaining the link-annotation situation, so the "why does everyone miss the links" question doesn't require re-deriving this investigation later.

**Swap map check:** `scripts/make_variants.py` run against the regenerated `resume/v4_1_A.txt` printed no "not found" warnings — all 6 institution/education names in `config/swap_map.yaml` (Instead, Multiplier, Keka HR, Hurix Digital, STOA, MIT Aurangabad) still match exactly once each in the real text and were swapped correctly in `resume/v4_1_B_institution_swap.txt`.

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

## Reconstructed vs. real: did the numbers change?

Yes, for two of the five parsers substantively, and for the raw-text extractors on one axis only. `pdftotext`, `PyMuPDF`, and `pdfminer.six` each dropped from 29/29 `ok` to 26/29 `ok` + 3 `missing` — purely the 3 profile-link fields, nothing else. `resumix` dropped from 11 `ok` to 7 `ok` (the 3 link fields plus a new `contact.name` failure `ok→wrong`, and `contact.location` moved `wrong→missing`); `resume-parser` held at 2 `ok` but 2 of its 24 `garbled` fields (`contact.linkedin`, `contact.github`) became `missing` since the substrings they were `garbled`-matched against no longer exist in the text. Skills coverage (37/39, 39/39, 39/39) was unaffected for every parser — the skills section itself is unchanged between the two files.

## What this shows

Running the actual Google Docs export instead of a text-only reconstruction did not change any underlying résumé fact, but it changed how much of that résumé a parser can actually recover: every one of the five parsers lost ground on the exact fields the evidence-links ablation is built around, because Google Docs renders the header's LinkedIn/Portfolio/GitHub links as hyperlink annotations with no URL text underneath — a detail invisible in a hand-reconstructed PDF and invisible to every text-extraction method under test here (none of which read link annotations). The two résumé-specific parsers (`resumix`, `resume-parser`) additionally proved sensitive to the real file's two-column header layout in ways the single-column reconstruction never exercised, degrading further on fields (`contact.name`, `.phone`, `.location`) that had scored correctly before. Net effect: the "dumbest tool wins" finding from the earlier run holds even more strongly on the real file (`pdftotext -layout` is still the best performer, now by an even larger margin on the two structured parsers), but the earlier report's practical usefulness — as a proxy for "how does this résumé actually parse" — required running the actual file, not a stand-in built from its text.

## What surprised me

The evidence-links ablation (`scripts/make_variants.py`'s `make_evidence_links()`, comparing résumé-with-URLs vs. résumé-without) is currently **a no-op on the real résumé's extracted text**: `resume/v4_1_A.txt`, regenerated from the real PDF, contains zero literal `http(s)://` URLs anywhere — `diff resume/v4_1_A.txt resume/v4_1_B_evidence_links.txt` after re-running `make_variants.py` shows no content difference at all (only a trailing-newline artifact). The stripping logic (`line.startswith("LinkedIn:")`, `URL_RE = r"https?://\S+"`) was written against the reconstructed file's plain "LinkedIn: https://... · Portfolio: ..." line; the real file never had that line to begin with — the URLs were always annotation-only. This means an LLM screener fed `v4_1_A.txt` as-is already sees a résumé with no visible evidence links, so condition A and condition B of Ablation 2 would currently score identically not because links don't move the needle, but because the harness can't construct a real A/B contrast from this résumé's extracted text. That's a design question for the screening harness (not touched here, out of this task's scope), not a parser-test finding, but it's the single most consequential thing this diff turned up — flagging it rather than quietly patching the ablation's semantics.
