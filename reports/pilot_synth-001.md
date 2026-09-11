# Pilot — synth-001 (Nimbus Frontier Labs)

Pilot reps per model: 10  
MDE: 5.0 fit_score points  alpha: 0.05  power: 0.8

Sample-size formula treats the pilot's single-condition SD as a conservative stand-in for paired-difference noise (see script docstring) — recommended reps are an upper bound, not a tight estimate. SD is computed on PARSED calls only; calls with parse_error (empty/unparseable model output, after one retry) are excluded — see n_parse_errors below.

| model | n_calls | n_parsed | n_parse_errors | sigma (SD, parsed only) | recommended reps/JD/condition |
|---|---|---|---|---|---|
| claude-haiku-4-5 | 10 | 10 | 0 | 3.18 (n=10) | 7 |
| gpt-5-mini | 10 | 10 | 0 | 3.16 (n=10) | 7 |

Recommended rep count for a real run (max across models): **7**

Projected cost for 20 JDs x 2 models x 2 ablations x 7 reps x 2 conditions (1120 calls): **$1.26** (rough token estimate, see scripts/estimate_cost.py for a tunable version)

(Pilot itself cost ~$0.0286 in mock-equivalent tokens.)