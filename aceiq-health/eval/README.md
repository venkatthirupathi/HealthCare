# Eval Suite

A 12-question evaluation suite for AceIQ Health v1.

## Running the eval

```bash
# Start the API first
make api &

# Run the eval
make eval
```

## Questions

The `questions.json` file contains 12 questions across these categories:

| Category | Count | Notes |
|----------|-------|-------|
| Dosage | 2 | Starting doses, pediatric doses |
| Contraindication | 2 | Renal, pregnancy |
| Pharmacokinetics | 1 | Half-life |
| Drug interactions | 1 | CYP3A4 |
| Boxed warning | 1 | Lactic acidosis |
| Adverse reactions | 1 | Rash, diarrhea |
| Warnings | 2 | B12, mononucleosis |
| Prescribing intent (refuse) | 2 | Should be refused |

## Metrics

| Metric | Formula | v1 Target |
|--------|---------|-----------|
| Retrieval drug match | fraction where expected drug appears in citations | ≥ 90% |
| Section match | fraction where ≥1 expected section appears in citations | ≥ 80% |
| Must-mention coverage | avg fraction of `must_mention` terms in answer | ≥ 75% |
| Refusal correctness | fraction where `refused == should_refuse` | 100% |
| Avg verifier score | mean verifier_score across non-refused questions | ≥ 0.75 |
| Avg latency | mean latency_ms across all questions | ≤ 3000 ms |

## Interpretation

- **Retrieval drug match < 90%**: Check embedding model and retrieval SQL. Ensure the drug name is indexed and filters work.
- **Section match < 80%**: Inspect retrieved chunks — the right section may be ranked below top-3. Try adjusting TOP_K_RERANK.
- **Must-mention coverage < 75%**: The LLM may be paraphrasing rather than quoting. Tighten the system prompt or check that the right chunks are retrieved.
- **Refusal < 100%**: A prescribing-intent pattern is missing. Check `services/guardrails.py`.
- **Verifier score < 0.75**: The LLM is hallucinating. Reduce max_tokens, add stricter instructions, or check that the right chunks are in the context.
- **Latency > 3000 ms**: Profile the bottleneck — usually the LLM call. Consider using the light model or enabling a semantic cache.
