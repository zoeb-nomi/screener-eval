# Analysis — mock-institution-swap

Ablation: `institution_swap`  
Mock run: `True`  
Reps: 5  
Calls: 420  
Est. cost: $0.7089

All numbers below are counted/computed directly from `calls.jsonl` — no LLM judged any output. Paired bootstrap CI uses 10000 resamples at 95% confidence.

## claude-haiku-4-5

- Calls: 210 total, 210 parsed, 0 parse errors (parse errors excluded from all SD/delta calculations below, not imputed)
- Paired JD deltas (B - A): n = 21
- Mean delta: **-3.15** points, 95% bootstrap CI [-3.97, -2.36]
- Sign test p-value (two-sided): 0.0000
- Recommendation flips: 15 / 105 paired runs
- Frontier-lab subset (n=12): mean delta -3.28

| jd_id | employer | class | n_A | n_B | mean_A | mean_B | delta |
|---|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | Amazon | large_tech | 5 | 5 | 55.2 | 52.4 | -2.8 |
| amazon-pm-ai-studios-001 | Amazon | large_tech | 5 | 5 | 73.0 | 71.2 | -1.8 |
| anthropic-pm-beneficial-deployments-001 | Anthropic | frontier_lab | 5 | 5 | 74.4 | 70.2 | -4.2 |
| anthropic-pm-claude-code-model-perf-001 | Anthropic | frontier_lab | 5 | 5 | 73.2 | 69.4 | -3.8 |
| anthropic-pm-claude-science-001 | Anthropic | frontier_lab | 5 | 5 | 59.6 | 55.8 | -3.8 |
| deepmind-pm-cyber-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 71.6 | 68.8 | -2.8 |
| deepmind-pm-gemini-post-training-001 | Google DeepMind | frontier_lab | 5 | 5 | 62.0 | 60.2 | -1.8 |
| deepmind-pm-robotics-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 51.8 | 49.0 | -2.8 |
| google-pm-ai-acceleration-001 | Google | large_tech | 5 | 5 | 69.8 | 67.0 | -2.8 |
| google-pm-ai-search-growth-001 | Google | large_tech | 5 | 5 | 53.6 | 49.2 | -4.4 |
| meta-pm-evals-improvement-001 | Meta | large_tech | 5 | 5 | 58.0 | 56.6 | -1.4 |
| meta-pm-machine-learning-001 | Meta | large_tech | 5 | 5 | 50.8 | 47.0 | -3.8 |
| microsoft-pm-ai-experiences-001 | Microsoft | large_tech | 5 | 5 | 77.0 | 74.2 | -2.8 |
| nvidia-pm-agentic-ai-kernel-gen-001 | NVIDIA | large_tech | 5 | 5 | 55.4 | 49.8 | -5.6 |
| nvidia-pm-ai-platform-inference-001 | NVIDIA | large_tech | 5 | 5 | 74.2 | 72.8 | -1.4 |
| openai-pm-api-agents-001 | OpenAI | frontier_lab | 5 | 5 | 52.6 | 47.6 | -5.0 |
| openai-pm-api-infrastructure-001 | OpenAI | frontier_lab | 5 | 5 | 73.0 | 67.2 | -5.8 |
| openai-pm-core-models-001 | OpenAI | frontier_lab | 5 | 5 | 50.4 | 49.8 | -0.6 |
| openai-pm-financial-engineering-001 | OpenAI | frontier_lab | 5 | 5 | 70.0 | 70.8 | +0.8 |
| openai-pm-safety-measurement-001 | OpenAI | frontier_lab | 5 | 5 | 68.6 | 60.8 | -7.8 |
| openai-pm-sensitive-deployments-001 | OpenAI | frontier_lab | 5 | 5 | 55.4 | 53.6 | -1.8 |

## gpt-5-mini

- Calls: 210 total, 210 parsed, 0 parse errors (parse errors excluded from all SD/delta calculations below, not imputed)
- Paired JD deltas (B - A): n = 21
- Mean delta: **-3.77** points, 95% bootstrap CI [-4.90, -2.66]
- Sign test p-value (two-sided): 0.0002
- Recommendation flips: 38 / 105 paired runs
- Frontier-lab subset (n=12): mean delta -4.08

| jd_id | employer | class | n_A | n_B | mean_A | mean_B | delta |
|---|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | Amazon | large_tech | 5 | 5 | 50.4 | 44.6 | -5.8 |
| amazon-pm-ai-studios-001 | Amazon | large_tech | 5 | 5 | 71.0 | 66.6 | -4.4 |
| anthropic-pm-beneficial-deployments-001 | Anthropic | frontier_lab | 5 | 5 | 70.4 | 62.0 | -8.4 |
| anthropic-pm-claude-code-model-perf-001 | Anthropic | frontier_lab | 5 | 5 | 67.4 | 62.8 | -4.6 |
| anthropic-pm-claude-science-001 | Anthropic | frontier_lab | 5 | 5 | 54.6 | 52.0 | -2.6 |
| deepmind-pm-cyber-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 68.8 | 65.6 | -3.2 |
| deepmind-pm-gemini-post-training-001 | Google DeepMind | frontier_lab | 5 | 5 | 54.4 | 56.6 | +2.2 |
| deepmind-pm-robotics-security-001 | Google DeepMind | frontier_lab | 5 | 5 | 49.4 | 43.8 | -5.6 |
| google-pm-ai-acceleration-001 | Google | large_tech | 5 | 5 | 69.8 | 65.0 | -4.8 |
| google-pm-ai-search-growth-001 | Google | large_tech | 5 | 5 | 45.8 | 43.0 | -2.8 |
| meta-pm-evals-improvement-001 | Meta | large_tech | 5 | 5 | 55.6 | 53.4 | -2.2 |
| meta-pm-machine-learning-001 | Meta | large_tech | 5 | 5 | 42.2 | 41.0 | -1.2 |
| microsoft-pm-ai-experiences-001 | Microsoft | large_tech | 5 | 5 | 67.0 | 67.8 | +0.8 |
| nvidia-pm-agentic-ai-kernel-gen-001 | NVIDIA | large_tech | 5 | 5 | 52.6 | 47.4 | -5.2 |
| nvidia-pm-ai-platform-inference-001 | NVIDIA | large_tech | 5 | 5 | 71.8 | 67.2 | -4.6 |
| openai-pm-api-agents-001 | OpenAI | frontier_lab | 5 | 5 | 47.6 | 46.0 | -1.6 |
| openai-pm-api-infrastructure-001 | OpenAI | frontier_lab | 5 | 5 | 66.8 | 65.6 | -1.2 |
| openai-pm-core-models-001 | OpenAI | frontier_lab | 5 | 5 | 47.2 | 43.2 | -4.0 |
| openai-pm-financial-engineering-001 | OpenAI | frontier_lab | 5 | 5 | 67.2 | 62.4 | -4.8 |
| openai-pm-safety-measurement-001 | OpenAI | frontier_lab | 5 | 5 | 61.0 | 54.2 | -6.8 |
| openai-pm-sensitive-deployments-001 | OpenAI | frontier_lab | 5 | 5 | 51.0 | 42.6 | -8.4 |
