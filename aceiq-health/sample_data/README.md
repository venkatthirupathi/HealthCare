# Sample Data

Three synthetic FDA SPL-style XML drug labels used for development and evaluation.

| File | Drug | Sections |
|------|------|---------|
| `metformin.xml` | Metformin Hydrochloride | 8 sections |
| `atorvastatin.xml` | Atorvastatin Calcium | 7 sections |
| `amoxicillin.xml` | Amoxicillin | 7 sections |

These files are **synthetic** — they follow the structure of real FDA Structured Product Labeling (SPL) XML but contain simplified text for development purposes.

Load them into the database with:

```bash
make seed
```
