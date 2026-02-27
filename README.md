## Understanding the Problem

Hiring decisions are among the most high-stakes, bias-prone judgments a team makes. The challenge is not a lack of data — it is that the data lives in incompatible formats (scores, years, rupees, days), criteria pull in different directions (higher CTC is worse, higher tech score is better), and human beings routinely say one thing with their weights and do another with their choices.

A generic 1–10 rating tool sidesteps this problem by asking users to pre-summarize their data before the system sees it. That introduces subjectivity at the worst possible stage — the input. This system was built to work with raw, heterogeneous data and surface the math honestly.

The deeper problem this solves is not calculation. It is self-awareness. When a hiring manager sets Communication as their top priority but the budget-friendly candidate wins anyway, the system should notice that — quietly, without judgment.

---

## Assumptions Made

- **Raw data is preferable to pre-rated scores.** Candidates are entered with real values (CTC in lakhs, experience in years, notice period in days) rather than asking users to convert everything to a 1–10 scale first.
- **Criteria direction must be explicit.** The system assumes users know whether a criterion is benefit-type (higher is better) or cost-type (lower is better). This is captured at input.
- **Weights are relative, not absolute.** A user entering weights of 8, 6, 9 means the same as 4, 3, 4.5 — the system normalizes them proportionally before scoring.
- **At least two candidates are required** for normalization to be meaningful. Single-candidate inputs are handled but flagged.
- **All criteria are compensatory** — a weakness in one area can be offset by strength in another. Non-compensatory elimination (hard constraints) is designed but treated as a separate pre-screening layer.

---

## Why I Structured the Solution This Way

The system is built around a single insight: **calculation and interpretation are two different jobs**, and most decision tools only do the first one.

The architecture reflects this separation:

```
input_handler        → validates and parses raw candidate data
normalizer           → min-max, direction-aware per criterion
weight_processor     → normalizes weights proportionally
scoring_engine       → weighted sum of normalized values
stability_evaluator  → margin and sensitivity analysis
blindspot_detector   → stated vs actual influence comparison
recommendation       → final output with explanation
constraint_filter    → (designed — see Trade-offs)
```

Each module has one job. Separating the normalizer from the scoring engine was particularly important — it meant normalization logic could be tested and improved independently without touching how scores are computed.

The Blind Spot Detector exists because of a specific failure I observed during testing: a manager set Communication as weight 9/10, but the candidate with the lowest communication score ranked first because of budget. The math was correct. The outcome contradicted the manager's stated intent. A system that stays silent about that is just a calculator. This one doesn't.

---
