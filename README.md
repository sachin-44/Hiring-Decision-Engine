# Hiring Decision Engine

> A structured, explainable hiring scoring engine built with Django.
---

## At a Glance

| Layer | Technology | Purpose |
|---|---|---|
| Backend | Python 3.10+, Django 4.2 | Web framework, session management, routing |
| Scoring Engine | Pure Python — `scoring.py` | Normalization, weighting, ranking, blind spot detection |
| Frontend | Bootstrap 5, Vanilla JS | Responsive wizard UI, what-if sliders |
| Data Storage | Django sessions + SQLite | Live state in session; saved decisions in DB |
| Export | ReportLab (PDF), csv module | Downloadable decision reports and data exports |
| Templates | Django templating + custom filters | `score_filters.py` handles score display logic |

---

## 1. Understanding the Problem

Hiring decisions are among the most consequential choices an organisation makes. They are also among the least structured. Most hiring panels compare candidates on gut feel, informal notes, and post-hoc justification — inconsistent, hard to audit, and prone to bias.

The core problem is not how to rank candidates. That is the easy part. The hard problems are:

| Problem | Why It Matters |
|---|---|
| Rankings don't reflect stated values | A manager who says Communication matters most may unknowingly build weights that optimise for salary |
| Scale bias corrupts raw scoring | Salary in rupees drowns out a 1–10 communication score regardless of weights |
| Confidence is invisible | A 0.02 margin and a 0.40 margin look identical in a ranked list |
| Decisions can't be audited | Intuitive hiring has no paper trail; structured scoring does |

This system addresses all four. It is not a black box that produces a rank. It is a transparent scoring engine that shows its working at every step and surfaces conflicts between stated priorities and actual outcomes.

---

## 2. Assumptions Made

### About the data
- All candidate values are numeric. Qualitative traits like "strong communicator" must be expressed as a number (e.g. 7/10) before entry.
- Values are entered by a human who has already gathered them. The system is a scoring tool, not a data collection tool.
- All values within a criterion are in consistent units. If one candidate's salary is in GBP and another's in INR, the system cannot detect that. Unit consistency is the hiring manager's responsibility.

### About weights
- Weights express relative importance, not absolute magnitudes. A weight of 40 and a weight of 4 produce identical results if all other weights scale proportionally. The system normalises weights to proportions internally.
- Weights are subjective and potentially imprecise — which is exactly why sensitivity analysis is built in.

### About the scoring model
- The model is **compensatory**. Strong performance on one criterion can offset weakness on another. This is appropriate for most hiring decisions. Non-negotiable minimums are handled by the planned constraint filter.
- Two candidates with identical scores are treated as tied. A tie at this precision level is a genuine signal to reconsider weights or conduct further evaluation.

---

## 3. Why the Solution Is Structured This Way

### Four-step wizard, not a single form
A single form asking for role, criteria, candidates, and values simultaneously overwhelms users and produces errors. The wizard separates concerns into digestible steps, each building on the previous. Session storage carries state between steps without a database write until the user explicitly saves.

### Pure Python scoring engine
The entire scoring logic lives in `scoring.py` with no Django ORM dependency. It can be tested independently with plain Python, imported into any context, and modified without touching the web layer. **Separating the engine from the framework was the most important architectural decision in the project.**

### Session-first, database-second
Candidate data lives in the Django session during active use. The database is written only when the user explicitly saves a decision. This keeps the common path fast, avoids half-written records, and means an abandoned session leaves no debris in the database.

### Raw values, not ratings
Users enter actual data — `salary=55000`, `experience=7`, `test_score=82` — not pre-summarised 1–10 ratings. Pre-summarising before the system sees it loses information and introduces subjectivity at the worst possible moment: the input stage. Normalisation happens inside the engine, not in the user's head.

### CSV upload for large candidate pools
Manual entry works for small decisions. Real hiring involves large applicant pools. The CSV upload accepts 100+ candidates, maps columns to criteria using 255 keyword patterns across 35+ criteria types, and processes the entire pool in a single run. The hiring manager specifies a shortlist size; the top N are surfaced for review.

---

## 4. Design Decisions and Trade-offs

### Min-max normalization over z-score

| | Min-Max (chosen) | Z-Score (rejected) |
|---|---|---|
| Output range | Always 0 to 1 | Unbounded, can be negative |
| Interpretability | Any manager can verify manually | Requires statistical knowledge |
| Direction handling | Built-in cost/benefit inversion | Requires manual pre-processing |
| Trade-off | Sensitive to small candidate pools | Robust to outliers but unreadable |

> **The accepted trade-off:** Min-max stretches a small candidate gap to the full 0–1 scale. Mitigated by user-defined scale bounds — set a realistic market range (e.g. 0–10 years) and the gap shrinks to its true proportional size.

### Quiet blind spot notes, not alerts
When a low-weight criterion drives more than 40% of the ranking gap, the system surfaces a quiet factual note rather than a warning. Early versions used confrontational language that triggered defensiveness rather than reflection. Same information, no judgment — the decision-maker draws their own conclusion.

### Written narrative alongside scores
The results page includes an auto-generated plain English explanation of the recommendation — what drove it, how confident the system is, where the decision is sensitive. Numbers alone are insufficient for high-stakes decisions. A hiring manager presenting to a leadership team needs words, not a score.

### What-if sliders
Interactive weight sliders recalculate the ranking live. Turns the system from a one-time calculator into an exploration tool — asking not just *"who won?"* but *"under what conditions could someone else win?"*

---

## 5. Edge Cases Considered

| Edge Case | What Happens | Why This Approach |
|---|---|---|
| All candidates share the same value for a criterion | System assigns 0.5 to all; shows a note that this criterion had no discriminating power | Prevents division-by-zero; correctly signals the criterion is irrelevant in this pool |
| Only two candidates | Min-max assigns 1.0 and 0.0 per criterion — small gaps appear decisive | User-defined scale bounds mitigate this; stability margin flags fragile results |
| Cost criteria (salary, notice period) | Normalization formula is inverted: lowest raw value scores 1.0 | The `is_cost` flag is set by the manager at setup; inversion is automatic |
| Very close scores (gap < 0.05) | Result is flagged as fragile; second interview recommended | A 0.02 margin gives false confidence; the system names that explicitly |
| Session expiry mid-wizard | User redirected to step one; data is lost | Known limitation; auto-save to database planned for next version |
| Weights summing to zero | Form enforces minimum weight of 1 at field level | A zero-weight criterion has no influence and should not be in the model |
| 100+ candidates via CSV | Smart scale detection applies realistic bounds; shortlist size limits the results view | Prevents large pools from artificially compressing all candidates toward the mean |

---

## 6. How to Run the Project

### Prerequisites
- Python 3.10 or higher
- pip
- Git

### Setup

The project is deployed on render
URL:https://hiring-decision-engine.onrender.com

```bash
git clone https://github.com/sachin-44/Hiring-Decision-Engine.git
cd Hiring-Decision-Engine

python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac / Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```
Open your browser: **http://127.0.0.1:8000**

### Running tests

```bash
python manage.py test decisions
```

### Project structure

```
Hiring-Decision-Engine/
├── decision_tool/
│   ├── settings.py          # SENSITIVITY_DELTA, STABILITY_THRESHOLD
│   ├── urls.py
│   └── wsgi.py
├── decisions/
│   ├── scoring.py           # Core engine — no ORM dependency
│   ├── views.py             # Wizard steps, CSV upload, PDF/CSV export
│   ├── forms.py             # Criteria and candidate value forms
│   ├── models.py            # HiringDecision, HiringCriteria, Candidate, CandidateValue
│   ├── urls.py
│   ├── admin.py
│   ├── tests.py             # Unit and regression tests
│   ├── templatetags/
│   │   └── score_filters.py # Custom display filters
│   └── templates/decisions/
│       ├── base.html
│       ├── landing.html
│       ├── step1_role.html
│       ├── step2_criteria.html
│       ├── step3_candidates.html
│       ├── step4_ratings.html
│       ├── results.html
│       └── upload_csv.html
├── manage.py
├── requirements.txt
└── .env.example
```

---

## 7. What I Would Improve With More Time

| Improvement | What It Does | Why Not Yet |
|---|---|---|
| Hard constraint pre-filter | Remove candidates below minimum thresholds before scoring, with clear rejection reasons | A filter without feedback is worse than no filter; feedback layer design not yet complete |
| Pairwise weight calibration (AHP) | Derive weights through structured comparisons rather than direct number entry | Requires 10+ questions upfront for 5 criteria — too much friction for first-time users |
| Team consensus mode | Multiple evaluators score independently; system surfaces agreements and disagreements | Requires session isolation per evaluator and a merge layer — would have required restructuring mid-build |
| Dynamic sensitivity threshold | Show exact weight delta needed to flip the ranking, not binary stable/fragile | Requires solving a constrained optimisation problem; current perturbation test is directionally correct |
| Authentication and audit trail | Login system, decision history, compliance PDF export per decision | Intentionally deferred to keep setup friction low; designed and roadmapped |
| ATS integration via REST API | Accept candidate data from Greenhouse / Workday without manual CSV upload | Requires API layer and authentication; out of scope for this build phase |

---

## 8. Known Limitations

| Limitation | Detail |
|---|---|
| No hard constraint pre-filter | Candidates failing minimum thresholds are scored alongside qualifying candidates. Fully designed, intentionally not shipped — a half-built filter that silently eliminates candidates is worse than none. |
| Session expiry loses progress | If a Django session expires between steps, all data is lost. No auto-save or expiry warning. Future version would persist progress to the database at each step. |
| Numeric values only | Qualitative assessments must be converted to numbers before entry. The system does not guide this conversion, introducing subjectivity for non-numeric criteria. |
| Single evaluator only | Session architecture assumes one decision-maker. Multiple evaluators cannot collaborate; disagreements are invisible to the system. |
| Bias is not detected, only amplified | The engine scores what it is given. Biased input criteria produce biased rankings with mathematical precision. |
| Git history reflects learning | The commit history includes an accidental deletion and immediate restore during a git learning exercise. The codebase is complete and correct. The history is honest. |

---

## Scoring Formula — Quick Reference

Every number on the results page derives from these four steps.

**Step 1 — Normalize weights**
```
w'i = wi / Σ(wi)
```
Raw weights (e.g. 40, 30, 30) become proportions summing to 1.0 (e.g. 0.40, 0.30, 0.30).

**Step 2 — Normalize candidate values**
```
Benefit criteria:   r'ij = (rij − min_i) / (max_i − min_i)
Cost criteria:      r'ij = (max_i − rij) / (max_i − min_i)
Identical values:   r'ij = 0.5  (non-discriminating criterion)
```
Each value scaled to 0–1. If user-defined bounds are set, those are used instead of candidate min/max.

**Step 3 — Calculate weighted points**
```
points_ij = r'ij × w'i
```
A criterion with weight 40 can contribute at most 0.40 points to the total score.

**Step 4 — Sum to total score**
```
Sj = Σ(points_ij)   for all criteria i
```
Total score is between 0.0 and 1.0, displayed as a percentage. The gap between the top two scores determines stability: **Strong** (> 0.15), **Moderate** (0.05–0.15), or **Fragile** (< 0.05).

---
