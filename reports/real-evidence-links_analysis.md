# Analysis — real-evidence-links

Ablation: `evidence_links`  
Mock run: `False`  
Reps: 5  
Calls: 420  
Est. cost: $1.7333

All numbers below are counted/computed directly from `calls.jsonl` — no LLM judged any output. Paired bootstrap CI uses 10000 resamples at 95% confidence.

## claude-haiku-4-5

- Calls: 210 total, 210 parsed, 0 parse errors (parse errors excluded from all SD/delta calculations below, not imputed)
- Paired JD deltas (B - A): n = 21
- Mean delta: **-0.90** points, 95% bootstrap CI [-2.90, 1.03]
- Sign test p-value (two-sided): 1.0000
- Recommendation flips: 28 / 105 paired runs
- Frontier-lab subset (n=12): mean delta 0.53

| jd_id | employer | class | n_A | n_B | mean_A | mean_B | delta |
|---|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | Amazon | large_tech | 5 | 5 | 28.0 | 28.0 | +0.0 |
| amazon-pm-ai-studios-001 | Amazon | large_tech | 5 | 5 | 37.2 | 28.8 | -8.4 |
| anthropic-pm-beneficial-deployments-001 | Anthropic | frontier_lab | 5 | 5 | 40.6 | 40.6 | +0.0 |
| anthropic-pm-claude-code-model-perf-001 | Anthropic | frontier_lab | 5 | 5 | 72.0 | 72.0 | +0.0 |
| anthropic-pm-claude-science-001 | Anthropic | frontier_lab | 5 | 5 | 62.0 | 72.0 | +10.0 |
| deepmind-pm-cyber-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 40.0 | 40.6 | +0.6 |
| deepmind-pm-gemini-post-training-001 | Google DeepMind | frontier_lab | 5 | 5 | 70.0 | 72.0 | +2.0 |
| deepmind-pm-robotics-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 28.0 | 27.4 | -0.6 |
| google-pm-ai-acceleration-001 | Google | large_tech | 5 | 5 | 65.2 | 66.0 | +0.8 |
| google-pm-ai-search-growth-001 | Google | large_tech | 5 | 5 | 30.2 | 28.0 | -2.2 |
| meta-pm-evals-improvement-001 | Meta | large_tech | 5 | 5 | 78.0 | 78.8 | +0.8 |
| meta-pm-machine-learning-001 | Meta | large_tech | 5 | 5 | 47.2 | 36.4 | -10.8 |
| microsoft-pm-ai-experiences-001 | Microsoft | large_tech | 5 | 5 | 33.0 | 28.0 | -5.0 |
| nvidia-pm-agentic-ai-kernel-gen-001 | NVIDIA | large_tech | 5 | 5 | 40.6 | 42.0 | +1.4 |
| nvidia-pm-ai-platform-inference-001 | NVIDIA | large_tech | 5 | 5 | 33.6 | 31.6 | -2.0 |
| openai-pm-api-agents-001 | OpenAI | frontier_lab | 5 | 5 | 57.2 | 58.0 | +0.8 |
| openai-pm-api-infrastructure-001 | OpenAI | frontier_lab | 5 | 5 | 28.0 | 28.0 | +0.0 |
| openai-pm-core-models-001 | OpenAI | frontier_lab | 5 | 5 | 72.0 | 72.0 | +0.0 |
| openai-pm-financial-engineering-001 | OpenAI | frontier_lab | 5 | 5 | 28.0 | 26.8 | -1.2 |
| openai-pm-safety-measurement-001 | OpenAI | frontier_lab | 5 | 5 | 48.0 | 37.8 | -10.2 |
| openai-pm-sensitive-deployments-001 | OpenAI | frontier_lab | 5 | 5 | 28.0 | 33.0 | +5.0 |

## gpt-5-mini

- Calls: 210 total, 210 parsed, 0 parse errors (parse errors excluded from all SD/delta calculations below, not imputed)
- Paired JD deltas (B - A): n = 21
- Mean delta: **0.41** points, 95% bootstrap CI [-1.82, 2.71]
- Sign test p-value (two-sided): 1.0000
- Recommendation flips: 31 / 105 paired runs
- Frontier-lab subset (n=12): mean delta 2.27

| jd_id | employer | class | n_A | n_B | mean_A | mean_B | delta |
|---|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | Amazon | large_tech | 5 | 5 | 37.6 | 37.8 | +0.2 |
| amazon-pm-ai-studios-001 | Amazon | large_tech | 5 | 5 | 70.2 | 75.2 | +5.0 |
| anthropic-pm-beneficial-deployments-001 | Anthropic | frontier_lab | 5 | 5 | 73.2 | 68.8 | -4.4 |
| anthropic-pm-claude-code-model-perf-001 | Anthropic | frontier_lab | 5 | 5 | 74.4 | 76.4 | +2.0 |
| anthropic-pm-claude-science-001 | Anthropic | frontier_lab | 5 | 5 | 73.2 | 71.6 | -1.6 |
| deepmind-pm-cyber-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 64.0 | 64.8 | +0.8 |
| deepmind-pm-gemini-post-training-001 | Google DeepMind | frontier_lab | 5 | 5 | 56.0 | 69.2 | +13.2 |
| deepmind-pm-robotics-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 25.0 | 34.4 | +9.4 |
| google-pm-ai-acceleration-001 | Google | large_tech | 5 | 5 | 84.4 | 77.0 | -7.4 |
| google-pm-ai-search-growth-001 | Google | large_tech | 5 | 5 | 61.6 | 58.6 | -3.0 |
| meta-pm-evals-improvement-001 | Meta | large_tech | 5 | 5 | 85.8 | 83.8 | -2.0 |
| meta-pm-machine-learning-001 | Meta | large_tech | 5 | 5 | 58.6 | 49.6 | -9.0 |
| microsoft-pm-ai-experiences-001 | Microsoft | large_tech | 5 | 5 | 74.0 | 71.2 | -2.8 |
| nvidia-pm-agentic-ai-kernel-gen-001 | NVIDIA | large_tech | 5 | 5 | 39.6 | 45.0 | +5.4 |
| nvidia-pm-ai-platform-inference-001 | NVIDIA | large_tech | 5 | 5 | 58.0 | 53.0 | -5.0 |
| openai-pm-api-agents-001 | OpenAI | frontier_lab | 5 | 5 | 72.0 | 76.2 | +4.2 |
| openai-pm-api-infrastructure-001 | OpenAI | frontier_lab | 5 | 5 | 74.2 | 71.2 | -3.0 |
| openai-pm-core-models-001 | OpenAI | frontier_lab | 5 | 5 | 81.2 | 80.0 | -1.2 |
| openai-pm-financial-engineering-001 | OpenAI | frontier_lab | 5 | 5 | 50.4 | 57.0 | +6.6 |
| openai-pm-safety-measurement-001 | OpenAI | frontier_lab | 5 | 5 | 75.6 | 78.2 | +2.6 |
| openai-pm-sensitive-deployments-001 | OpenAI | frontier_lab | 5 | 5 | 79.0 | 77.6 | -1.4 |
