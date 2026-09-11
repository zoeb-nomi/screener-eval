# Analysis — real-institution-swap

Ablation: `institution_swap`  
Mock run: `False`  
Reps: 5  
Calls: 420  
Est. cost: $1.7333

All numbers below are counted/computed directly from `calls.jsonl` — no LLM judged any output. Paired bootstrap CI uses 10000 resamples at 95% confidence.

## claude-haiku-4-5

- Calls: 233 total, 233 parsed, 0 parse errors (parse errors excluded from all SD/delta calculations below, not imputed)
- Paired JD deltas (B - A): n = 21
- Mean delta: **0.07** points, 95% bootstrap CI [-3.05, 2.76]
- Sign test p-value (two-sided): 1.0000
- Recommendation flips: 17 / 116 paired runs
- Frontier-lab subset (n=12): mean delta 1.86

| jd_id | employer | class | n_A | n_B | mean_A | mean_B | delta |
|---|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | Amazon | large_tech | 6 | 6 | 28.0 | 28.0 | +0.0 |
| amazon-pm-ai-studios-001 | Amazon | large_tech | 5 | 6 | 37.0 | 34.5 | -2.5 |
| anthropic-pm-beneficial-deployments-001 | Anthropic | frontier_lab | 5 | 5 | 34.4 | 38.0 | +3.6 |
| anthropic-pm-claude-code-model-perf-001 | Anthropic | frontier_lab | 5 | 5 | 72.0 | 72.0 | +0.0 |
| anthropic-pm-claude-science-001 | Anthropic | frontier_lab | 6 | 6 | 56.3 | 67.0 | +10.7 |
| deepmind-pm-cyber-security-001 | Google DeepMind | frontier_lab | 6 | 6 | 42.0 | 40.8 | -1.2 |
| deepmind-pm-gemini-post-training-001 | Google DeepMind | frontier_lab | 5 | 5 | 72.0 | 72.0 | +0.0 |
| deepmind-pm-robotics-security-001 | Google DeepMind | frontier_lab | 6 | 6 | 28.0 | 27.0 | -1.0 |
| google-pm-ai-acceleration-001 | Google | large_tech | 6 | 6 | 67.0 | 70.3 | +3.3 |
| google-pm-ai-search-growth-001 | Google | large_tech | 5 | 5 | 30.2 | 28.8 | -1.4 |
| meta-pm-evals-improvement-001 | Meta | large_tech | 5 | 5 | 78.0 | 78.0 | +0.0 |
| meta-pm-machine-learning-001 | Meta | large_tech | 5 | 5 | 62.0 | 39.2 | -22.8 |
| microsoft-pm-ai-experiences-001 | Microsoft | large_tech | 6 | 6 | 32.7 | 29.8 | -2.8 |
| nvidia-pm-agentic-ai-kernel-gen-001 | NVIDIA | large_tech | 6 | 6 | 35.0 | 39.2 | +4.2 |
| nvidia-pm-ai-platform-inference-001 | NVIDIA | large_tech | 6 | 6 | 28.0 | 29.3 | +1.3 |
| openai-pm-api-agents-001 | OpenAI | frontier_lab | 5 | 5 | 46.0 | 60.0 | +14.0 |
| openai-pm-api-infrastructure-001 | OpenAI | frontier_lab | 6 | 6 | 28.7 | 29.2 | +0.5 |
| openai-pm-core-models-001 | OpenAI | frontier_lab | 5 | 5 | 72.0 | 72.0 | +0.0 |
| openai-pm-financial-engineering-001 | OpenAI | frontier_lab | 5 | 5 | 28.0 | 28.0 | +0.0 |
| openai-pm-safety-measurement-001 | OpenAI | frontier_lab | 6 | 6 | 48.7 | 42.0 | -6.7 |
| openai-pm-sensitive-deployments-001 | OpenAI | frontier_lab | 6 | 6 | 28.0 | 30.3 | +2.3 |

## gpt-5-mini

- Calls: 232 total, 232 parsed, 0 parse errors (parse errors excluded from all SD/delta calculations below, not imputed)
- Paired JD deltas (B - A): n = 21
- Mean delta: **-1.14** points, 95% bootstrap CI [-3.03, 0.84]
- Sign test p-value (two-sided): 0.1892
- Recommendation flips: 31 / 116 paired runs
- Frontier-lab subset (n=12): mean delta -0.36

| jd_id | employer | class | n_A | n_B | mean_A | mean_B | delta |
|---|---|---|---|---|---|---|---|
| amazon-pm-ai-ml-training-annapurna-001 | Amazon | large_tech | 6 | 6 | 38.8 | 43.3 | +4.5 |
| amazon-pm-ai-studios-001 | Amazon | large_tech | 5 | 5 | 70.4 | 65.6 | -4.8 |
| anthropic-pm-beneficial-deployments-001 | Anthropic | frontier_lab | 5 | 5 | 74.2 | 75.6 | +1.4 |
| anthropic-pm-claude-code-model-perf-001 | Anthropic | frontier_lab | 5 | 5 | 80.8 | 72.4 | -8.4 |
| anthropic-pm-claude-science-001 | Anthropic | frontier_lab | 6 | 6 | 69.3 | 66.5 | -2.8 |
| deepmind-pm-cyber-security-001 | Google DeepMind | frontier_lab | 6 | 6 | 56.2 | 58.0 | +1.8 |
| deepmind-pm-gemini-post-training-001 | Google DeepMind | frontier_lab | 5 | 5 | 53.6 | 64.6 | +11.0 |
| deepmind-pm-robotics-security-001 | Google DeepMind | frontier_lab | 6 | 6 | 30.5 | 30.0 | -0.5 |
| google-pm-ai-acceleration-001 | Google | large_tech | 6 | 6 | 78.8 | 76.8 | -2.0 |
| google-pm-ai-search-growth-001 | Google | large_tech | 5 | 5 | 63.6 | 56.6 | -7.0 |
| meta-pm-evals-improvement-001 | Meta | large_tech | 5 | 5 | 86.4 | 83.4 | -3.0 |
| meta-pm-machine-learning-001 | Meta | large_tech | 5 | 5 | 57.8 | 58.0 | +0.2 |
| microsoft-pm-ai-experiences-001 | Microsoft | large_tech | 6 | 6 | 76.5 | 75.5 | -1.0 |
| nvidia-pm-agentic-ai-kernel-gen-001 | NVIDIA | large_tech | 6 | 6 | 48.7 | 39.2 | -9.5 |
| nvidia-pm-ai-platform-inference-001 | NVIDIA | large_tech | 6 | 6 | 55.3 | 58.3 | +3.0 |
| openai-pm-api-agents-001 | OpenAI | frontier_lab | 5 | 5 | 77.0 | 76.4 | -0.6 |
| openai-pm-api-infrastructure-001 | OpenAI | frontier_lab | 6 | 6 | 70.3 | 73.0 | +2.7 |
| openai-pm-core-models-001 | OpenAI | frontier_lab | 5 | 5 | 79.2 | 79.0 | -0.2 |
| openai-pm-financial-engineering-001 | OpenAI | frontier_lab | 5 | 5 | 52.0 | 47.0 | -5.0 |
| openai-pm-safety-measurement-001 | OpenAI | frontier_lab | 6 | 6 | 77.7 | 75.0 | -2.7 |
| openai-pm-sensitive-deployments-001 | OpenAI | frontier_lab | 6 | 6 | 79.3 | 78.3 | -1.0 |
