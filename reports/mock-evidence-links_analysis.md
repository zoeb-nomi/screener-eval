# Analysis — mock-evidence-links

Ablation: `evidence_links`  
Mock run: `True`  
Reps: 5  
Calls: 420  
Est. cost: $0.7106

All numbers below are counted/computed directly from `calls.jsonl` — no LLM judged any output. Paired bootstrap CI uses 10000 resamples at 95% confidence.

## claude-haiku-4-5

- Calls: 210 total, 210 parsed, 0 parse errors (parse errors excluded from all SD/delta calculations below, not imputed)
- Paired JD deltas (B - A): n = 21
- Mean delta: **-2.26** points, 95% bootstrap CI [-3.15, -1.42]
- Sign test p-value (two-sided): 0.0002
- Recommendation flips: 24 / 105 paired runs
- Frontier-lab subset (n=12): mean delta -2.17

| jd_id | employer | class | n_A | n_B | mean_A | mean_B | delta |
|---|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | Amazon | large_tech | 5 | 5 | 59.8 | 58.2 | -1.6 |
| amazon-pm-ai-studios-001 | Amazon | large_tech | 5 | 5 | 66.6 | 65.2 | -1.4 |
| anthropic-pm-beneficial-deployments-001 | Anthropic | frontier_lab | 5 | 5 | 68.4 | 67.6 | -0.8 |
| anthropic-pm-claude-code-model-perf-001 | Anthropic | frontier_lab | 5 | 5 | 74.0 | 73.0 | -1.0 |
| anthropic-pm-claude-science-001 | Anthropic | frontier_lab | 5 | 5 | 50.8 | 50.6 | -0.2 |
| deepmind-pm-cyber-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 53.6 | 49.2 | -4.4 |
| deepmind-pm-gemini-post-training-001 | Google DeepMind | frontier_lab | 5 | 5 | 58.2 | 55.2 | -3.0 |
| deepmind-pm-robotics-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 71.0 | 71.8 | +0.8 |
| google-pm-ai-acceleration-001 | Google | large_tech | 5 | 5 | 68.6 | 65.2 | -3.4 |
| google-pm-ai-search-growth-001 | Google | large_tech | 5 | 5 | 72.8 | 67.2 | -5.6 |
| meta-pm-evals-improvement-001 | Meta | large_tech | 5 | 5 | 69.0 | 66.8 | -2.2 |
| meta-pm-machine-learning-001 | Meta | large_tech | 5 | 5 | 74.2 | 75.0 | +0.8 |
| microsoft-pm-ai-experiences-001 | Microsoft | large_tech | 5 | 5 | 74.6 | 71.2 | -3.4 |
| nvidia-pm-agentic-ai-kernel-gen-001 | NVIDIA | large_tech | 5 | 5 | 53.0 | 52.8 | -0.2 |
| nvidia-pm-ai-platform-inference-001 | NVIDIA | large_tech | 5 | 5 | 68.8 | 64.4 | -4.4 |
| openai-pm-api-agents-001 | OpenAI | frontier_lab | 5 | 5 | 54.8 | 50.4 | -4.4 |
| openai-pm-api-infrastructure-001 | OpenAI | frontier_lab | 5 | 5 | 68.2 | 64.0 | -4.2 |
| openai-pm-core-models-001 | OpenAI | frontier_lab | 5 | 5 | 72.8 | 66.6 | -6.2 |
| openai-pm-financial-engineering-001 | OpenAI | frontier_lab | 5 | 5 | 53.0 | 51.0 | -2.0 |
| openai-pm-safety-measurement-001 | OpenAI | frontier_lab | 5 | 5 | 50.8 | 50.6 | -0.2 |
| openai-pm-sensitive-deployments-001 | OpenAI | frontier_lab | 5 | 5 | 75.6 | 75.2 | -0.4 |

## gpt-5-mini

- Calls: 210 total, 210 parsed, 0 parse errors (parse errors excluded from all SD/delta calculations below, not imputed)
- Paired JD deltas (B - A): n = 21
- Mean delta: **-2.40** points, 95% bootstrap CI [-3.42, -1.47]
- Sign test p-value (two-sided): 0.0004
- Recommendation flips: 37 / 105 paired runs
- Frontier-lab subset (n=12): mean delta -1.38

| jd_id | employer | class | n_A | n_B | mean_A | mean_B | delta |
|---|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | Amazon | large_tech | 5 | 5 | 58.8 | 56.4 | -2.4 |
| amazon-pm-ai-studios-001 | Amazon | large_tech | 5 | 5 | 58.6 | 56.2 | -2.4 |
| anthropic-pm-beneficial-deployments-001 | Anthropic | frontier_lab | 5 | 5 | 64.2 | 61.4 | -2.8 |
| anthropic-pm-claude-code-model-perf-001 | Anthropic | frontier_lab | 5 | 5 | 71.4 | 66.2 | -5.2 |
| anthropic-pm-claude-science-001 | Anthropic | frontier_lab | 5 | 5 | 47.8 | 47.4 | -0.4 |
| deepmind-pm-cyber-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 48.0 | 47.6 | -0.4 |
| deepmind-pm-gemini-post-training-001 | Google DeepMind | frontier_lab | 5 | 5 | 51.6 | 51.6 | +0.0 |
| deepmind-pm-robotics-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 66.8 | 64.4 | -2.4 |
| google-pm-ai-acceleration-001 | Google | large_tech | 5 | 5 | 63.8 | 60.4 | -3.4 |
| google-pm-ai-search-growth-001 | Google | large_tech | 5 | 5 | 66.8 | 65.8 | -1.0 |
| meta-pm-evals-improvement-001 | Meta | large_tech | 5 | 5 | 64.6 | 59.2 | -5.4 |
| meta-pm-machine-learning-001 | Meta | large_tech | 5 | 5 | 70.2 | 67.0 | -3.2 |
| microsoft-pm-ai-experiences-001 | Microsoft | large_tech | 5 | 5 | 68.4 | 65.4 | -3.0 |
| nvidia-pm-agentic-ai-kernel-gen-001 | NVIDIA | large_tech | 5 | 5 | 48.8 | 39.6 | -9.2 |
| nvidia-pm-ai-platform-inference-001 | NVIDIA | large_tech | 5 | 5 | 64.6 | 60.8 | -3.8 |
| openai-pm-api-agents-001 | OpenAI | frontier_lab | 5 | 5 | 48.4 | 45.4 | -3.0 |
| openai-pm-api-infrastructure-001 | OpenAI | frontier_lab | 5 | 5 | 63.8 | 64.8 | +1.0 |
| openai-pm-core-models-001 | OpenAI | frontier_lab | 5 | 5 | 65.8 | 63.6 | -2.2 |
| openai-pm-financial-engineering-001 | OpenAI | frontier_lab | 5 | 5 | 49.0 | 50.4 | +1.4 |
| openai-pm-safety-measurement-001 | OpenAI | frontier_lab | 5 | 5 | 45.4 | 43.6 | -1.8 |
| openai-pm-sensitive-deployments-001 | OpenAI | frontier_lab | 5 | 5 | 73.0 | 72.2 | -0.8 |
