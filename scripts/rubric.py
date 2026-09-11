"""
The screening prompt — a PROXY, not any vendor's actual scoring formula.

No ATS/LLM-screening vendor (Ashby, Greenhouse, Workday/HiredScore, LinkedIn Hiring
Assistant, Eightfold, Paradox) publishes their matching algorithm — see
claude/MIRROR_EVAL_V2_RESEARCH_2026-09-10.md §1 in the source project. What IS
published is which signals move an LLM's résumé-fit judgment:

  - Iso, Pezeshkpour, Bhutani & Hruschka / Megagon Labs (arXiv 2503.19182,
    12 LLMs, 384,000 scored résumé-JD pairs): institution-name signal (prestige/
    familiarity of the school or employer named) shifts scores in 20-40% of
    occupations tested, independent of the underlying work described.
  - General LLM-screening literature converges on: explicit JD-keyword/skill
    overlap, quantified-impact density (numbers attached to claims), and
    evidence/verifiability of claims as score-moving features.

This rubric asks the model to score fit using exactly those signals, phrased as
a screener would phrase them — not reverse-engineered from any real product,
and not claimed to match what Ashby/Greenhouse/Workday/etc. actually compute.
Say this in every publication of results from this repo.
"""

SYSTEM_PROMPT = """You are a résumé screener for a company hiring an AI Product \
Manager. You are shown one job description and one résumé. Score how well this \
résumé fits THIS job, the way an experienced technical recruiter doing a first-pass \
screen would: relevance of role scope and domain, density and specificity of \
quantified impact, evidence that claims are verifiable, and alignment with the \
job description's stated requirements and vocabulary. You may also be influenced, \
as real screeners measurably are, by the prestige/familiarity of named employers \
and schools — score honestly, do not correct for that bias.

Respond with STRICT JSON only, no markdown fencing, no commentary outside the JSON, \
matching exactly this schema:

{
  "fit_score": <integer 0-100>,
  "recommendation": "<advance|hold|reject>",
  "top_reasons": ["<reason 1>", "<reason 2>", "<reason 3>"],
  "objections": ["<objection>", ...],
  "discounted_claims": ["<claim you would not take at face value>", ...]
}

"top_reasons" must have exactly 3 items. "objections" and "discounted_claims" may \
be empty arrays if you have none. Output nothing but the JSON object."""

USER_TEMPLATE = """JOB DESCRIPTION ({employer}, {title}):
{jd_text}

---

RÉSUMÉ:
{resume_text}

---

Score this résumé's fit for this job. Respond with the JSON object only."""


def build_messages(jd_text: str, resume_text: str, employer: str, title: str):
    user = USER_TEMPLATE.format(
        employer=employer, title=title, jd_text=jd_text.strip(), resume_text=resume_text.strip()
    )
    return SYSTEM_PROMPT, user
