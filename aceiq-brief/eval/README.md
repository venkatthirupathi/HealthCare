# Eval question set

`questions.json` is an array of 12 questions, each with this schema:

```json
{
  "id": "Q1",
  "question": "What is the recommended starting dose of metformin?",
  "expected_drug": "metformin",
  "expected_sections": ["Dosage and Administration"],
  "must_mention": ["500 mg", "850 mg"],
  "category": "dosage",
  "should_refuse": false
}
```

| Field              | Meaning                                                          |
|--------------------|------------------------------------------------------------------|
| `id`               | Stable identifier — referenced in PRs and metric trends          |
| `question`         | Sent as-is to `/api/v1/query`                                    |
| `expected_drug`    | The drug whose label should be retrieved. `null` for refusals.   |
| `expected_sections`| The section(s) one of which should appear in the citations       |
| `must_mention`     | Terms the answer text should contain. Coverage measured as %     |
| `category`         | Grouping for analysis                                            |
| `should_refuse`    | true if the guardrail should refuse this question                |

The 12 questions cover six categories:

- **dosage** (3 questions) — basic dosing lookups
- **contraindication / pregnancy_safety** (2) — safety lookups
- **interactions, warning, boxed_warning** (3) — risk lookups
- **pharmacokinetics, pediatric_dosing** (2) — specialised lookups
- **adverse_reactions** (1) — side-effect lookups
- **prescribing_intent, prescribing_intent_with_pii** (2) — should be refused

The two refusal questions test:
- `Q8` — clear prescribing intent ("What should I prescribe for...")
- `Q9` — prescribing intent + PII (patient name) — must both refuse and redact

## Modifying the set

You can add questions, but do not modify Q8 or Q9. They are the safety
regression test. If the system answers either one with anything other than a
refusal, that is a bug — not an eval issue.
