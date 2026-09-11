# Cross-screener comparison — real-institution-swap

Ablation: `institution_swap`  
Calls in run: 465  

All numbers below are counted/computed directly from `calls.jsonl` by `analysis/cross_model.py` — no LLM judged any output. Section 1 uses condition A (the unmodified résumé) only, one mean score per job description per model. Section 2 uses every recorded call for that model in this run (both conditions), because it characterizes the screener's own behavior, not the A/B contrast.

## 1. Same résumé, same posting — cross-model gap (condition A, n=21 job descriptions)

- Mean absolute gap (gpt-5-mini − claude-haiku-4-5): **22.3** points
- Max absolute gap: **51.3** points
- gpt-5-mini scores higher on **19 of 21** postings
- Pearson r between the two models' per-JD mean scores: **0.46**
- Majority-verdict agreement (mode recommendation per JD): **6 of 21**

| jd_id | mean claude-haiku-4-5 | mean gpt-5-mini | gap | verdict claude-haiku-4-5 | verdict gpt-5-mini | agree |
|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | 28.0 | 38.8 | +10.8 | reject | hold | no |
| amazon-pm-ai-studios-001 | 37.0 | 70.4 | +33.4 | reject | hold | no |
| anthropic-pm-beneficial-deployments-001 | 34.4 | 74.2 | +39.8 | reject | hold | no |
| anthropic-pm-claude-code-model-perf-001 | 72.0 | 80.8 | +8.8 | advance | hold | no |
| anthropic-pm-claude-science-001 | 56.3 | 69.3 | +13.0 | hold | hold | yes |
| deepmind-pm-cyber-security-001 | 42.0 | 56.2 | +14.2 | reject | hold | no |
| deepmind-pm-gemini-post-training-001 | 72.0 | 53.6 | -18.4 | advance | reject | no |
| deepmind-pm-robotics-security-001 | 28.0 | 30.5 | +2.5 | reject | reject | yes |
| google-pm-ai-acceleration-001 | 67.0 | 78.8 | +11.8 | hold | advance | no |
| google-pm-ai-search-growth-001 | 30.2 | 63.6 | +33.4 | reject | hold | no |
| meta-pm-evals-improvement-001 | 78.0 | 86.4 | +8.4 | advance | advance | yes |
| meta-pm-machine-learning-001 | 62.0 | 57.8 | -4.2 | hold | hold | yes |
| microsoft-pm-ai-experiences-001 | 32.7 | 76.5 | +43.8 | reject | hold | no |
| nvidia-pm-agentic-ai-kernel-gen-001 | 35.0 | 48.7 | +13.7 | reject | hold | no |
| nvidia-pm-ai-platform-inference-001 | 28.0 | 55.3 | +27.3 | reject | hold | no |
| openai-pm-api-agents-001 | 46.0 | 77.0 | +31.0 | hold | hold | yes |
| openai-pm-api-infrastructure-001 | 28.7 | 70.3 | +41.7 | reject | hold | no |
| openai-pm-core-models-001 | 72.0 | 79.2 | +7.2 | advance | advance | yes |
| openai-pm-financial-engineering-001 | 28.0 | 52.0 | +24.0 | reject | hold | no |
| openai-pm-safety-measurement-001 | 48.7 | 77.7 | +29.0 | hold | advance | no |
| openai-pm-sensitive-deployments-001 | 28.0 | 79.3 | +51.3 | reject | advance | no |

## 2. Per-model noise and behavior (all calls in this run, both conditions)

| Measure | claude-haiku-4-5 | gpt-5-mini |
|---|---|---|
| Calls | 233 | 232 |
| Mean fit score | 44.8 | 64.7 |
| Distinct scores given | 10 | 30 |
| Most common verdict | reject (136 of 233) | hold (157 of 232) |
| (jd_id, condition) cells with zero spread across reps | 17 of 42 | 0 of 42 |
| Mean per-cell run-to-run SD (population) | 3.0 | 4.8 |
| Postings where the screener flipped its own verdict across reps (condition A only) | 6 of 21 | 12 of 21 |

### Full verdict distributions

- **claude-haiku-4-5**: reject 136, advance 55, hold 42
- **gpt-5-mini**: hold 157, advance 48, reject 27
