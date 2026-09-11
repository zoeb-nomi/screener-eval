# Cross-screener comparison — real-evidence-links

Ablation: `evidence_links`  
Calls in run: 420  

All numbers below are counted/computed directly from `calls.jsonl` by `analysis/cross_model.py` — no LLM judged any output. Section 1 uses condition A (the unmodified résumé) only, one mean score per job description per model. Section 2 uses every recorded call for that model in this run (both conditions), because it characterizes the screener's own behavior, not the A/B contrast.

## 1. Same résumé, same posting — cross-model gap (condition A, n=21 job descriptions)

- Mean absolute gap (gpt-5-mini − claude-haiku-4-5): **20.8** points
- Max absolute gap: **51.0** points
- gpt-5-mini scores higher on **18 of 21** postings
- Pearson r between the two models' per-JD mean scores: **0.50**
- Majority-verdict agreement (mode recommendation per JD): **8 of 21**

| jd_id | mean claude-haiku-4-5 | mean gpt-5-mini | gap | verdict claude-haiku-4-5 | verdict gpt-5-mini | agree |
|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | 28.0 | 37.6 | +9.6 | reject | reject | yes |
| amazon-pm-ai-studios-001 | 37.2 | 70.2 | +33.0 | reject | hold | no |
| anthropic-pm-beneficial-deployments-001 | 40.6 | 73.2 | +32.6 | reject | hold | no |
| anthropic-pm-claude-code-model-perf-001 | 72.0 | 74.4 | +2.4 | advance | hold | no |
| anthropic-pm-claude-science-001 | 62.0 | 73.2 | +11.2 | hold | hold | yes |
| deepmind-pm-cyber-security-001 | 40.0 | 64.0 | +24.0 | reject | hold | no |
| deepmind-pm-gemini-post-training-001 | 70.0 | 56.0 | -14.0 | advance | reject | no |
| deepmind-pm-robotics-security-001 | 28.0 | 25.0 | -3.0 | reject | reject | yes |
| google-pm-ai-acceleration-001 | 65.2 | 84.4 | +19.2 | hold | advance | no |
| google-pm-ai-search-growth-001 | 30.2 | 61.6 | +31.4 | reject | hold | no |
| meta-pm-evals-improvement-001 | 78.0 | 85.8 | +7.8 | advance | advance | yes |
| meta-pm-machine-learning-001 | 47.2 | 58.6 | +11.4 | reject | hold | no |
| microsoft-pm-ai-experiences-001 | 33.0 | 74.0 | +41.0 | reject | hold | no |
| nvidia-pm-agentic-ai-kernel-gen-001 | 40.6 | 39.6 | -1.0 | reject | reject | yes |
| nvidia-pm-ai-platform-inference-001 | 33.6 | 58.0 | +24.4 | reject | hold | no |
| openai-pm-api-agents-001 | 57.2 | 72.0 | +14.8 | hold | hold | yes |
| openai-pm-api-infrastructure-001 | 28.0 | 74.2 | +46.2 | reject | hold | no |
| openai-pm-core-models-001 | 72.0 | 81.2 | +9.2 | advance | advance | yes |
| openai-pm-financial-engineering-001 | 28.0 | 50.4 | +22.4 | reject | hold | no |
| openai-pm-safety-measurement-001 | 48.0 | 75.6 | +27.6 | hold | hold | yes |
| openai-pm-sensitive-deployments-001 | 28.0 | 79.0 | +51.0 | reject | advance | no |

## 2. Per-model noise and behavior (all calls in this run, both conditions)

| Measure | claude-haiku-4-5 | gpt-5-mini |
|---|---|---|
| Calls | 210 | 210 |
| Mean fit score | 45.6 | 65.3 |
| Distinct scores given | 11 | 26 |
| Most common verdict | reject (122 of 210) | hold (139 of 210) |
| (jd_id, condition) cells with zero spread across reps | 18 of 42 | 1 of 42 |
| Mean per-cell run-to-run SD (population) | 2.8 | 5.0 |
| Postings where the screener flipped its own verdict across reps (condition A only) | 8 of 21 | 8 of 21 |

### Full verdict distributions

- **claude-haiku-4-5**: reject 122, advance 52, hold 36
- **gpt-5-mini**: hold 139, advance 41, reject 30
