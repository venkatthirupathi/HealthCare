# Sample data

The three XML files in this directory are **synthetic** but follow the DailyMed
SPL XML structure (sections coded by LOINC, free-text bodies). They are large
enough to exercise the chunker, retriever, and reranker realistically.

## Replacing with real DailyMed data

When you're ready to scale up:

1. Visit https://dailymed.nlm.nih.gov and download SPL XML for the drugs you
   want. The bulk download endpoint is at:
   `https://dailymed.nlm.nih.gov/dailymed/spl-resources-all-drug-labels.cfm`

2. Extract the `.zip` archives. Each contains an `spl.xml` file.

3. Place those `.xml` files in this directory (or any directory you point
   `scripts/seed.py` at).

4. Re-run `make seed`. Existing documents are skipped (ingestion is idempotent
   on `(source, external_id)`).

## Source verification

The clinical content in these synthetic samples is drawn from publicly
available US prescribing information for each drug and is meant to be
clinically plausible for demo purposes — but always reground your evaluation
against real DailyMed before publishing any numbers.
