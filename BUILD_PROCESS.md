## 1. How I Started

When I first read the assignment, my instinct was to build a generic decision tool — something that takes options, lets users rate them 1–10 on criteria, multiplies by weights, and ranks them.

That would have worked. But I paused and re-read the brief. So I asked myself — what decision domain would be the most meaningful, the hardest to get right, and the most relevant to the people evaluating this submission?

The answer was obvious: **hiring decisions.**

Hiring is high-stakes. It involves multiple conflicting criteria. It is deeply prone to unconscious bias. And the people reading this submission are, right now, making hiring decisions themselves. They would feel this problem personally.

The project began with the simplest possible formulation — a standard weighted scoring model:

```
Sj = Σ(wi * rij)
```

Where:
- `wi` = weight of criterion `i`
- `rij` = raw value of option `j` on criterion `i`
- `Sj` = total score of option `j`

At this stage I assumed:
- User inputs would be comparable across criteria
- Larger numeric values would not distort results
- Direct multiplication of weights and values would be sufficient

All three assumptions turned out to be wrong.

---

## 2. The First Problem I Hit — Scale Bias

Once I committed to hiring, I had to decide: should users rate candidates 1–10 on each criterion, or enter real raw data?

The 1–10 rating approach felt dishonest. It asks the user to pre-summarize their data before the system even sees it. You lose information and introduce subjectivity at the input stage — the worst possible place for it.

Real hiring data looks like this:

| Candidate | Tech Score | Experience | CTC Expected | Notice Period | Communication |
|-----------|-----------|------------|--------------|---------------|---------------|
| Arjun     | 84        | 3 years    | 8.5L         | 30 days       | 7/10          |
| Meera     | 71        | 6 years    | 11L          | 60 days       | 9/10          |
| Rohan     | 91        | 2 years    | 7L           | 90 days       | 6/10          |

These numbers live in completely different universes — rupees, years, days, scores. When tested with direct weighted scoring, CTC values completely dominated the final score even when their weight was moderate.

This revealed a **scale bias problem** that made the entire scoring engine unreliable:
- Cost-type criteria (where lower is better) were not handled at all
- Weight magnitudes could artificially inflate one criterion's influence
- The initial assumption of direct comparability was simply incorrect

---

## 3. Alternative Approaches I Explored and Rejected

### 3.1 Linear Inversion for Cost Criteria

I first tried converting cost criteria using: `max + min - x`

This flips the direction so lower values score higher. However it still preserved the original scale bias, required fixed input bounds, and did not generalise to arbitrary raw numeric inputs. **Rejected.**

### 3.2 Z-Score Normalization

```
z = (x - mean) / standard deviation
```

This removes scale bias effectively. However it produces negative values which are confusing to users, and reduces transparency — a hiring manager cannot intuitively verify a normalized score. Since interpretability was a core design priority, this approach was not adopted. **Rejected.**

### 3.3 Hard Constraint Pre-filtering as the Only Filter

I briefly considered replacing scoring entirely with pass/fail threshold elimination. Rejected as a complete replacement because it removes the compensatory nature of the model — a candidate slightly below a threshold but exceptional elsewhere gets unfairly eliminated. I kept the idea as a future pre-screening layer instead. **Rejected as sole mechanism.**

---
