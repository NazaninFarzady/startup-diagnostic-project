# Startup Diagnostic Pipeline

## Run the complete pipeline

From the project root, run:

```bash
python src/run_pipeline.py
```

To restart from a later step, for example Step 6:

```bash
python src/run_pipeline.py --from-step 6
```

## Execution order

1. Audit raw data.
2. Clean and standardize data.
3. Build separate analysis tables.
4. Engineer features.
5. Perform exploratory analysis.
6. Answer the diagnostic questions.
7. Validate the findings.
8. Convert findings into diagnostics.
9. Refresh documentation and reproducibility checks.

## Important limits

- Do not merge the three principal datasets without verified company matches.
- Failure data describes failed startups only.
- Synthetic metrics demonstrate the method and do not estimate real-world risk.
- Funding results are observational associations, not causal estimates.

## Documentation

See the documentation folder for cleaning rules, assumptions, data dictionaries, code hashes, data hashes, output hashes, and environment versions.
