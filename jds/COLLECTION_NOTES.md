# JD Collection Notes — 2026-09-10

Census of currently-open, US-based (or US-remote) mid-level AI/ML/LLM Product
Manager roles at named large-tech and frontier-lab employers. Collected via
WebSearch/WebFetch and Claude-in-Chrome browser automation against each
employer's own careers board (Ashby, Greenhouse, or in-house search UI on
Workday/Eightfold/custom stacks). No login, no applications, no forms
submitted.

## Method

- Ashby- and Greenhouse-backed boards (OpenAI, Anthropic) expose a public
  JSON posting API (`api.ashbyhq.com/posting-api/job-board/<slug>`,
  `boards-api.greenhouse.io/v1/boards/<slug>/jobs`) that was queried directly
  from the browser tab via `javascript_tool` (same-origin fetch), filtered
  client-side for `/product\s*manager/i` in the title. This gave an exact,
  complete count per employer for those two boards.
- Google, Google DeepMind, Meta, Microsoft, Amazon, NVIDIA, Apple, xAI,
  Mistral, and Cohere each run their own in-house or Workday/Eightfold search
  UI. These were queried via their own search box/URL params and the results
  list scanned for `Product Manager` titles; individual JD pages were then
  opened in a fresh tab and read with `get_page_text`.
- For every match, level was screened from the posting's own title first
  (exclude Director/VP/Head/Principal/explicit "Senior Staff"; include plain
  "Product Manager" and "Senior Product Manager" per the brief), then
  US location was confirmed from the posting's own location field.

## Per-employer result (count of open, matching, mid-level postings found vs. collected)

| Employer | Class | Found (matching titles, US) | Collected (full JD saved) |
|---|---|---|---|
| OpenAI | frontier_lab | 11 | 6 |
| Anthropic | frontier_lab | 16 | 3 |
| Google DeepMind | frontier_lab | 3 (+1 excluded: Group PM) | 3 |
| xAI | frontier_lab | 0 | 0 |
| Mistral | frontier_lab | 0 (3 PM roles found, all Paris — US roles only per brief) | 0 |
| Cohere | frontier_lab | 0 (3 PM roles found, all Toronto — US only per brief) | 0 |
| Google (non-DeepMind) | large_tech | ~8-10 plausible AI-focused (not exhaustively counted; 94 total mid-level "Product Manager" hits, most not AI-focused) | 2 |
| Meta | large_tech | 3 clearly AI-titled (of 32 total "Product Manager" hits under the Product Management team) | 2 |
| Microsoft | large_tech | 2+ clearly AI-titled at Senior/mid level seen (of 897 broad hits; many more Principal-level AI PM roles exist but are excluded by level) | 1 |
| Amazon | large_tech | 2 clearly AI-titled US roles seen (of 767 total "Product Manager" hits globally, not exhaustively classified) | 2 |
| NVIDIA | large_tech | 11 mid/senior AI-titled US roles on page 1 alone (of 1062 broad hits; NVIDIA runs an unusually large PM org) | 2 |
| Apple | large_tech | 0 (two targeted searches — "product manager" within the ML/AI team, and "AI Product Manager" broadly — returned zero postings titled "Product Manager"; Apple appears to route most AI/ML product work through Engineering/Program Manager titles instead) | 0 |
| Netflix | large_tech | 0 (the widely-reported "AI Product Manager, Content Platform Operations and Publishing" posting had been pulled/closed by retrieval time; no other AI/ML/LLM-titled PM opening was found in a 286-result relevance search) | 0 |

**Total: 21 real JDs collected** (plus 3 synthetic placeholders, `synth-001..003`,
whose text is committed in `jds/text/` and whose entries stay in `jds/index.yaml`
flagged `synthetic: true` — they're the only JD text that ships in the public
repo/zip, so `make mock` / `make pilot-mock` work with zero real JDs collected).

## Boards/searches that were friction-heavy or effectively blocked

- **Google's careers search** (`google.com/about/careers/applications/jobs/results`)
  does not support a combined `q="Product Manager" DeepMind` phrase query —
  it silently falls back to a broad relevance search once the DeepMind term
  stops narrowing results (confirmed by paginating and watching DeepMind-branded
  results disappear after ~page 3). Worked around by running two separate
  searches: `q=DeepMind` (scanned for `Product Manager` in the h3 headings)
  and a separate generic `q="Product Manager"` pass for the large_tech bucket.
- **Microsoft's careers search** (`apply.careers.microsoft.com`) silently
  drops query-string parameters on a fresh navigation about half the time,
  redirecting to the unfiltered 2254-job listing; typing into the in-page
  search box and letting the SPA rewrite the URL (adding its own `pid=`
  token) was the only reliable path. This cost significant time and only one
  JD was fully collected as a result — Microsoft's true count of matching
  postings is almost certainly higher than what's reflected in the index.
- **NVIDIA and Google DeepMind's Workday/Google-careers job-detail links**:
  clicking a result in place did not always update the URL/page; the
  reliable path was reading the `href` off the link element via `read_page`
  and navigating to it directly.
- Several **stale search-engine-cached URLs** returned "job not found /
  taken down" (seen on OpenAI, Meta, NVIDIA, and Netflix) — postings churn
  fast enough that a WebSearch result from even a few days earlier can 404.
  Always re-verified via the employer's live search rather than trusting a
  cached deep link.
- No board **outright blocked fetching** (no CAPTCHA/bot-wall encountered).

## Ambiguous level-filtering calls made

- **"Sr. Product Manager" (Amazon) and "Sr. Product Manager" (various)**
  were treated as equivalent to "Senior Product Manager" and included.
- **"Group Product Manager" (Google DeepMind)** and **"Product Manager Lead"
  (Google DeepMind)** were excluded as leadership-track titles analogous to
  Director/Principal, even though neither word appears verbatim in the
  brief's exclude list — judgment call, flagged here for Zoeb to overrule if
  the wedge analysis wants them in.
- **OpenAI "Product Manager, Financial Engineering" and "Product Manager,
  Legal"** are PM roles at a frontier lab but the *product surface* itself
  (billing, legal ops) isn't obviously "AI/ML/LLM" on its face. Included them
  anyway on the reasoning that OpenAI's entire product line is AI and these
  are titled "Product Management" department roles, not because the JD text
  screams eval/LLM — worth a second look before using them as strong
  eval-wedge examples.
- **Cohere and Mistral** both had a handful of "Product Manager" roles open,
  all outside the US (Toronto and Paris respectively) — excluded per the
  brief's explicit "US roles only" instruction for these two employers,
  yielding an honest zero rather than a stretch match.
- **Apple and Netflix zeros** are based on a small number of targeted
  searches each (2-3 queries), not an exhaustive crawl of every team/locale
  filter combination — a genuine zero is plausible (Apple rarely titles
  roles "Product Manager"; the one Netflix posting that would have qualified
  had already closed) but should be read as "not found in the time
  available" rather than "provably zero."
