# Hiring Decision Engine — Build Process

> *How a simple weighted scoring idea became a system that holds a mirror to human bias.*

---

## Executive Summary

| | |
|---|---|
| **The Problem** | Standard weighted scoring produces results that are mathematically correct but humanly misleading. Numbers from different scales — salary, test scores, notice period — cannot be multiplied together without first being made comparable. The largest numbers dominate, not the most important criteria. |
| **What Was Built** | A four-step Django web application implementing a Multi-Criteria Decision Analysis (MCDA) engine for hiring. It normalizes raw values across incompatible scales, weights criteria proportionally, ranks candidates, and surfaces the gap between what a hiring manager says they value and what their weights actually optimise for. |
| **The One Insight** | After the engine was built correctly, a test run showed a candidate ranked first despite having the lowest communication score — even though communication was the stated top priority. The math was right. The result contradicted intent. This was not a bug. It was the product. |
| **This Document** | A record of how the thinking evolved — which approaches were rejected and why, which mistakes were made and corrected, where AI was used and where it failed, and one honest account of an evening spent debugging something that showed no error but produced entirely wrong data. |

**16 Sections · 5 Mistakes Documented · 3 Approaches Rejected · 1 Insight That Changed Everything**

---

## Section 1 — The Question Before the First Line of Code

Most people start with the most obvious solution. I almost did too.

The brief asked for a decision support tool. A simple weighted scoring system would satisfy it. I could have had version one running in an afternoon.

But I paused. The people evaluating this submission work in a company. Companies hire people. Right now, the evaluators are making or have recently made hiring decisions themselves.

> *"The best way to make someone feel a problem is to build the solution for the problem they are living right now."*

That realization changed everything. This would not be a generic decision tool. It would be a hiring decision engine — built for the exact domain the reader would feel personally.

The project began with the simplest formulation from multi-attribute decision making theory:

```
Sj = Σ(wi × rij)

wi  = weight of criterion i
rij = raw value of candidate j on criterion i
Sj  = total score of candidate j
```

Three assumptions lived inside this formula. **All three turned out to be wrong.**

First: that raw values from different criteria could be multiplied meaningfully. Second: that larger numbers deserve more influence. Third: that the ranking produced would reflect what the decision-maker wanted. The journey of building this system is the story of discovering why each assumption failed — and what to do about it.

---

## Section 2 — The Formal Decision Model

The engine implements a **Multi-Criteria Decision Analysis (MCDA)** model — designed for problems where no single criterion determines the right answer and trade-offs must be made explicitly.

### Notation

| Symbol | Meaning |
|---|---|
| `C = {c₁, c₂ ... cₙ}` | Set of n candidates |
| `K = {k₁, k₂ ... kₘ}` | Set of m criteria |
| `wᵢ` | Weight of criterion i, where Σwᵢ = 1 after normalization |
| `rᵢⱼ` | Raw value of candidate j on criterion i |
| `r'ᵢⱼ` | Normalized value (always 0 to 1) |
| `Sⱼ` | Final weighted score of candidate j |

### Naive formula (fails on heterogeneous data)

```
Sⱼ = Σ(wᵢ × rᵢⱼ)
```

A CTC of 800,000 and a communication rating of 8 cannot be meaningfully multiplied by the same weight. The large number dominates regardless of its weight.

### Corrected formula with normalization

**Benefit criteria** (higher is better):
```
r'ᵢⱼ = (rᵢⱼ − min(rᵢ)) / (max(rᵢ) − min(rᵢ))
```

**Cost criteria** (lower is better — salary, notice period):
```
r'ᵢⱼ = (max(rᵢ) − rᵢⱼ) / (max(rᵢ) − min(rᵢ))
```

**Final score:**
```
Sⱼ = Σ(wᵢ × r'ᵢⱼ)
```

Every r'ᵢⱼ falls strictly between 0 and 1. Best value on any criterion = 1.0. Worst = 0.0. All criteria are now dimensionless and directly comparable.

**Special case — identical values:** When max = min, the denominator is zero. The system assigns r'ᵢⱼ = 0.5 to all candidates and shows a note. The criterion had no discriminating power.

> **Why MCDA and not ML?** ML ranking requires historical hiring data with outcome labels — rarely available, frequently biased, legally sensitive. MCDA requires only explicit human judgment. Making that judgment explicit is itself a feature: it forces the decision-maker to commit to their priorities before seeing results.

---

## Section 3 — The Scale Bias Problem

Consider this realistic hiring dataset:

| Candidate | Tech Score | Experience | CTC (₹L) | Notice (days) | Communication |
|---|---|---|---|---|---|
| Arjun | 84 | 3 yrs | 8.5 | 30 | 7/10 |
| Meera | 71 | 6 yrs | 11 | 60 | 9/10 |
| Rohan | 91 | 2 yrs | 7 | 90 | 6/10 |

These numbers live in completely different universes. When multiplied directly by weights and summed, the largest numbers — CTC and notice period — dominate the final score even when their weights are modest.

**This is scale bias.** The first version produced results where expected salary single-handedly determined the ranking, regardless of how weights were distributed.

> *"The formula was mathematically correct and factually wrong — a particularly dangerous combination."*

---

## Section 4 — Three Roads Rejected

Before committing to an approach, three alternatives were evaluated seriously.

### Road 1 — Linear Inversion
Transform cost values using `max + min − x`. Easy to explain and verify.

**Rejected:** Preserves the original scale. A ₹7L CTC and a 30-day notice period still produce numbers in different universes. Addresses direction, not magnitude.

### Road 2 — Z-Score Normalization
Express each value as standard deviations from the mean. Statistically rigorous.

```
z = (x − mean) / standard deviation
```

**Rejected:** Z-scores produce negative numbers. Telling a hiring manager a candidate scores −0.73 on experience is not interpretable. A system whose output cannot be understood by its user is not a tool — it is a black box wearing a calculator's clothing.

### Road 3 — Pure Threshold Elimination
Pass/fail filters. Candidates below minimums are removed before ranking.

**Rejected as the sole mechanism:** Destroys the compensatory nature of the model. A candidate marginally below a threshold but exceptional on everything else gets silently discarded. Thresholds belong as a pre-screening layer, not as the entire engine.

> **Design principle established here:** Every approach that sacrifices interpretability for mathematical rigour was rejected. The system must be explainable to a person who does not know what a z-score is. This constraint shaped every subsequent decision.

---

## Section 5 — The Normalization Decision

The approach that survived all constraints: **direction-aware min-max normalization**.

- Benefit criteria → highest value gets 1.0, lowest gets 0.0
- Cost criteria → lowest value gets 1.0 (frugality rewarded, not penalised)
- All values fall strictly between 0 and 1
- All criteria become comparable regardless of original units

> *"Any hiring manager can verify this transformation with a calculator. That transparency was non-negotiable."*

**The new problem it introduced:** If all candidates score between 4 and 5 years of experience, the formula stretches that one-year gap to the full 0–1 scale. A difference that should barely matter suddenly dominates.

**The fix:** User-defined scale bounds. Set the actual market range (0–10 years) and the 4-to-5-year gap occupies only 10% of the scale, as it should. Bounds default to auto-derived from candidates if not set.

---

## Section 6 — Five Mistakes Made and Corrected

### Mistake 1 — Raw Weights Used Directly
A user typing 8, 6, 9, 5, 7 had criteria compared at those magnitudes, inflating any criterion with a large number.

**Correction:** Weights normalized to proportions. Weight of 8 in a total of 35 becomes 0.229. Influence is now each criterion's share of the total.

### Mistake 2 — Division by Zero on Identical Values
When all candidates share the same value for a criterion, the formula divides by zero. First version crashed silently.

**Correction:** Any criterion where max equals min receives 0.5 for all candidates. A visible note explains why.

### Mistake 3 — Equal Confidence for All Rankings
Rank 1 appeared equally authoritative whether the margin was 0.02 or 0.40 points.

**Correction:** Stability margin introduced. Below 0.05 = fragile. Above 0.15 = strong. Confidence shown alongside the recommendation.

### Mistake 4 — Step 4 Table Breaking Beyond Two Candidates
Column-per-candidate layout overflowed the viewport for three or more candidates. Form submission silently dropped all columns beyond the second.

**Correction:** Redesigned to card-per-candidate. Each card contains all criteria rows vertically. Independent. Scales to any number of candidates.

### Mistake 5 — The Confrontational Blind Spot Message
First version displayed: *"Rohan's ranking is driven 60% by his low CTC. But your most important criterion was Communication. Are you optimizing for budget over quality?"* Testing showed defensiveness, not reflection.

**Correction:** Replaced with a quiet factual note: *"CTC is contributing more to this result than Communication, though Communication has a higher stated weight."* No question. No challenge. Just information.

---

## Section 7 — The Insight That Changed What the System Is For

After the scoring engine was working correctly, I ran a test scenario. The hiring manager rated Communication as their top priority, assigning it the highest weight. The result showed Rohan in first place.

**Rohan had the lowest communication score of all three candidates.**

The math was correct. The weights were correct. The normalization was accurate. The result directly contradicted stated intent.

> *"The system was technically correct and humanly wrong. That is not a bug in the algorithm. That is a bug in human self-awareness."*

What happened: the manager said Communication mattered most, but their weight distribution quietly allowed CTC and tech score to together contribute more to the gap. The system did what it was told. What it was told did not match what the manager meant.

A calculator shows the result and stops. A companion notices the conflict.

This insight reframed the entire purpose. The scoring engine was not the product. **The product was a system that could surface the gap between what a decision-maker says they want and what their decisions actually optimise for.**

That became the **Blind Spot Detector** — a module that compares the stated weight of each criterion against its actual contribution to the score gap between the top two candidates. When a low-weight criterion drives more than 40% of the ranking difference, a quiet note appears.

> A hiring decision engine is not useful because it calculates quickly. It is useful because it makes visible the things the decision-maker cannot see about their own priorities.

---

## Section 8 — Stability, Sensitivity, and the Confidence Layer

A ranking without a confidence level is dangerous.

### 8.1 The Stability Margin

| Gap Range | Classification | Interpretation |
|---|---|---|
| > 0.15 | Strong | Winner is clear. Recommend with confidence. |
| 0.05 – 0.15 | Moderate | Worth reviewing weights before deciding. |
| < 0.05 | Fragile | Small weight changes could flip the result. Run a second interview. |

### 8.2 Sensitivity Analysis
The highest-weight criterion is increased by 5% and the ranking is recalculated. If the winner changes, the decision is flagged as sensitive. If unchanged, confirmed as stable.

### 8.3 The What-If Slider
Interactive weight sliders on the results page recalculate the ranking live. Turns the system from a one-time calculator into an exploration tool — asking not just *"who won?"* but *"under what conditions could someone else win?"*

---

## Section 9 — How the System Evolved

No feature was planned upfront in its final form. Each emerged from an observed limitation in the previous version.

Phases 1–11 were the algorithmic journey — building the math, making it honest, making it safe to act on. Phases 12–16 were the product journey — the moment the engine stopped being a function and became something a non-technical user could actually use. The transition happened when I asked who the real user was. The answer was not an engineer. It was a hiring manager with a browser and a spreadsheet.

| Phase | What Changed | Why | Status |
|---|---|---|---|
| 1 | Direct weighted scoring | Initial implementation | ✅ |
| 2 | Raw inputs instead of 1–10 ratings | Remove input subjectivity | ✅ |
| 3 | Min-max normalization | Eliminate scale bias | ✅ |
| 4 | Direction-aware cost/benefit flipping | Handle salary and notice period | ✅ |
| 5 | Weight normalization to proportions | Proportional influence regardless of magnitude | ✅ |
| 6 | Stability margin and confidence level | Rankings without confidence are misleading | ✅ |
| 7 | Sensitivity analysis — perturbation test | Evaluate robustness of subjective weights | ✅ |
| 8 | Blind spot detector | Surface conflicts between intent and outcome | ✅ |
| 9 | User-defined scale bounds | Prevent tiny candidate gaps distorting the scale | ✅ |
| 10 | Auto-generated written analysis | Numeric output alone insufficient for high-stakes decisions | ✅ |
| 11 | Winner hero card + gap badges | Visual hierarchy makes recommendation scannable | ✅ |
| 12 | CSV bulk upload + review flow | Manual entry doesn't scale beyond 10 candidates | ✅ |
| 13 | Smart scale detection (255 patterns) | Hiring data follows known real-world ranges | ✅ |
| 14 | Django web application | Browser-based; removes setup friction for non-technical users | ✅ |
| 15 | PDF and CSV export | Hiring decisions need a paper trail | ✅ |
| 16 | Landing page | First impression communicates credibility before the tool is used | ✅ |
| 17 | Hard constraint pre-filter | Eliminate unqualified candidates before scoring | 📋 Planned |

---

## Section 10 — Building the Django Application

A Python function is not a product — it is a capability. The decision to build a full web application came from one question: who is the real user?

Not an engineer who runs a script. A hiring manager who opens a browser, uploads a spreadsheet, and expects a result. That person clicks.

**Django over Flask:** Built-in session management. The entire multi-step wizard needed to persist state between pages without a database. The session became the working memory of the application.

### The Four-Step Wizard
Role title → criteria with weights → candidates → values. Each step validates before proceeding. Navigating backwards is always safe.

Step 4 was the hardest. The first design used a grid table: candidates as columns, criteria as rows. It worked for two candidates and failed catastrophically for three or more — column overflow broke the layout, and form submission silently dropped all columns beyond the second.

**Fix:** Card-per-candidate layout. Each candidate gets their own card with all criteria as vertical rows. Scrollable, independent, scales without data loss.

### Session Serialization — A Silent Data Corruption Bug
Django's session engine serializes data as JSON. JSON converts integer dictionary keys to strings. A dictionary stored as `{1: value}` is retrieved as `{"1": value}`.

The breakdown lookup used integer criterion IDs. After the session roundtrip they were strings. The lookup returned `None`. `None` displayed as zero — no error, no traceback, just confident wrong data.

**Fix:** Helper function `_bd()` that checks both integer and string versions of every key before lookup.

### CSV Bulk Upload — 100+ Candidates
Three non-trivial decisions:
1. **Column mapping** — uploaded headers must match criteria from Step 2. Mismatches are flagged before scoring, not silently wrong.
2. **Smart scale auto-detection** — 255 keyword patterns across 35+ criteria types apply realistic real-world ranges automatically.
3. **Shortlist size** — hiring manager specifies how many top candidates to surface. The rest are scored and available in export.

---

## Section 11 — The Night I Did Not Know What Was Wrong

There is a version of this document where every problem is solved cleanly. Problem identified. Fix applied. Moving on. That version is not honest.

The session key bug took the better part of an evening. The symptom: the Best Per Criteria section showed all zeros. Not an error. Not a crash. Confidently displayed zeros, formatted correctly, in the right cells, completely wrong.

I checked the scoring function. Correct. The normalization. Correct. The template. Reading the right variable. I added print statements. The breakdown dictionary printed correctly in the terminal. The page still showed zeros.

For a stretch of time I genuinely did not know if the problem was in Python, in Django's template engine, in the session, or in the JavaScript. Four locations ruled out. Bug still present. There is no algorithm for that moment. You are just wrong about something and you do not yet know what.

The answer: JSON does not preserve integer dictionary keys. `{1: value}` becomes `{"1": value}`. The lookup used integer IDs. After the session roundtrip they were strings. The lookup returned `None`. One character difference. Integer `1` versus string `"1"`. The fix was two lines. The time spent finding it was not.

> The most disorienting bugs are not the ones that crash loudly. They are the ones that succeed quietly with wrong data. Trust the shape of data coming out of external systems — including Django itself — as little as you trust data coming from users.

---

## Section 12 — The Tool I Used to Build the Tool

Significant parts of this system were built in collaboration with Claude,ChatGPT,Anthropic's AI assistant. The Django views, PDF export, CSV upload flow, landing page, and several of the bugs in the next section were worked through with AI assistance. This is not a disclaimer — it is a design decision worth examining honestly.

**Where AI was useful:** Syntax recall under pressure, boilerplate for structures I already understood conceptually, a second pair of eyes on logic I had been staring at too long. The session key bug — I described the symptom after forty minutes of searching. Claude identified the JSON serialization cause in one response. I would have found it eventually. I found it faster.

**Where AI was wrong:**
- First landing page design was dark and editorial — mismatched to a non-technical hiring manager audience. Required re-scoping the entire brief.
- Initial blind spot message was confrontational — exactly the mistake described in Section 6. I rewrote it.
- First CSV column mapping logic had no error handling for mismatched headers. I added it.

The pattern: AI is a fast first draft. First drafts are not finished work. Every piece of generated code was read, understood, tested, and in most cases modified. Nothing was accepted without comprehension. The architectural decisions — normalization over z-scores, cards over grid, quiet blind spot message, not shipping the constraint filter — none came from AI. They came from thinking about who this tool was actually for.

> *"Using AI to build faster is not different in kind from using a framework, a library, or Stack Overflow. The judgment about what to build, and why, still has to come from somewhere. That somewhere is the person responsible for the outcome."*

---

## Section 13 — Real Bugs Fixed in Production

### Bug 1 — `export_pdf: name 'responses' is not defined`
Typo: `return responses` instead of `return response`. NameError at runtime, only surfaced when the Export PDF button was actually clicked — not exercised during development.

**Lesson:** Test all code paths, not just the happy path.

### Bug 2 — CSV Candidates Bleeding into Manual Flow
After a CSV run, navigating to Step 3 showed all 100 CSV candidates pre-filled. Session retained the previous run without checking context.

**Fix:** Step 3 clears `candidates`, `is_csv`, and `num_to_rank` from session on every GET request.

### Bug 3 — Landing Page Not Rendering
Landing page built, view written, root URL still showed Step 1. Three separate fix attempts failed because the wrong file was being edited.

The project has two `urls.py` files: `decision_tool/urls.py` (project-level) and `decisions/urls.py` (app-level). A stray `views.py` in the project root was also intercepting Django's import resolution.

**Fix:** Deleted root-level `views.py`. Updated `decisions/urls.py` to route `''` to `views.landing` and `step1/` to `views.step1_role`.

### Bug 4 — Shortlist Count Missing from Manual Flow
CSV upload had a "how many to shortlist?" input. Manual flow did not. Manual decisions always defaulted to `shortlist_n = 1`.

**Fix:** Added shortlist count input to `step3_candidates.html`. POST handler in `views.py` reads and saves `num_to_rank` to session. Both flows now behave identically.

---

## Section 14 — Architecture and Module Separation

As the system grew, keeping all logic in one function became untenable. A change to normalization could break contribution calculation. A change to sensitivity analysis could break the blind spot detector.

| Module | Responsibility |
|---|---|
| `input_handler` | Validates and parses raw candidate data |
| `normalizer` | Min-max normalization, direction-aware, with user-defined or auto-derived bounds |
| `weight_processor` | Converts raw weights to proportions summing to 1.0 |
| `scoring_engine` | Weighted sum of normalized values per candidate |
| `stability_evaluator` | Margin calculation and perturbation testing |
| `blindspot_detector` | Stated weight vs actual score gap contribution |
| `narrative_generator` | Converts scoring data into plain English for results page |
| `constraint_filter` | Designed, not yet implemented — pre-screens against hard thresholds |

Separating normalization from scoring was the most consequential decision. It allowed the normalization layer to be tested independently before being connected to anything else. It also made user-defined bounds clean to add — the bounds logic lives entirely within the normalizer.

---

## Section 15 — The Feature I Chose Not to Build

Real hiring starts with elimination, not scoring. A candidate expecting ₹25L for a ₹10L role does not need to be ranked — they need to be removed. This is how Workday and Greenhouse actually function.

I designed the constraint pre-filter fully:

```
for each candidate:
  if experience < min_required  → eliminate, show reason
  if ctc > max_acceptable       → eliminate, show reason
  if notice > max_acceptable    → eliminate, show reason
  else                          → pass to scoring engine
```

**Why it was not shipped:** A filter that silently eliminates candidates without clear feedback is worse than no filter. I chose to ship nothing rather than ship something that could wrongly eliminate a strong candidate without explaining why.

> *"I chose honesty over completeness."*

---

## Section 16 — Limitations and What Comes Next

A system that cannot name its own limitations is not trustworthy.

| Limitation | Why It Exists | Impact |
|---|---|---|
| Weights are subjectively assigned | No historical data; AHP deferred due to onboarding friction | Two managers may weight the same role differently |
| Single evaluator only | Session assumes one user; consensus mode requires merge layer | Group decisions and evaluator disagreements are invisible |
| No authentication or persistence | Session-based for simplicity; no login built | Decisions lost on browser close; no HR audit trail |
| No hard constraint pre-filter | Deliberate deferral — feedback layer not yet complete | Unqualified candidates enter the scoring pool |
| Bias is not detected, only amplified | Engine scores what it is given | Biased input produces biased rankings with mathematical precision |
| Static sensitivity threshold | Perturbation test built in one evening; analytical version not yet | Users get binary stable/unstable, not exact weight delta to flip result |

> This system makes hiring more consistent. It does not make it more objective. The criteria, weights, and raw values all come from humans. The engine is only as unbiased as the people who configure it. That is not a flaw to be fixed — it is a truth to be stated clearly.

### Deliberate Deferrals

**Hard constraint pre-filter** — fully designed, first in roadmap. Not shipped because a filter without feedback is more dangerous than no filter.

**AHP weight calibration** — derives weights through pairwise comparisons. Not shipped because AHP requires n(n−1)/2 questions upfront — ten questions for five criteria before a single candidate is entered. Too much friction for first-time users.

**Team consensus mode** — requires session isolation per evaluator and a merge layer. Would have required restructuring the session model mid-build.

**Dynamic sensitivity threshold** — calculates exact weight delta to flip a ranking, not binary stable/fragile. Requires solving a constrained optimization problem. Current perturbation test is directionally correct.

---

## Section 17 — A Complete Worked Example

**Role:** Senior Software Engineer · **6 candidates** · **5 criteria** · **Shortlist: top 2**

### Criteria

| Criterion | Weight | Direction | Rationale |
|---|---|---|---|
| Technical Score | 35 | Higher = better | Core job requirement |
| Experience (years) | 25 | Higher = better | Seniority level fit |
| CTC Expected (₹L) | 20 | Lower = better | Budget constraint |
| Notice Period (days) | 10 | Lower = better | Urgency of hire |
| Communication | 10 | Higher = better | Client-facing role |

### Raw Input Data

| Candidate | Tech Score | Exp (yrs) | CTC (₹L) | Notice (days) | Comm. |
|---|---|---|---|---|---|
| Arjun Pillai | 84 | 3 | 8.5 | 30 | 7/10 |
| Meera Nair | 71 | 6 | 11 | 60 | 9/10 |
| Rohan Desai | 91 | 2 | 7 | 90 | 6/10 |
| Divya Sharma | 78 | 5 | 9.5 | 45 | 8/10 |
| Kiran Menon | 65 | 8 | 13 | 30 | 9/10 |
| Priya Iyer | 88 | 4 | 8 | 15 | 8/10 |

Without normalization, CTC and notice period dominate regardless of weights. The next step removes scale — every value becomes a number between 0 and 1 where 1 = best on this criterion.

### After Min-Max Normalization

| Candidate | Tech Score | Exp (yrs) | CTC | Notice | Comm. |
|---|---|---|---|---|---|
| Arjun Pillai | 0.731 | 0.167 | 0.750 | 0.800 | 0.333 |
| Meera Nair | 0.231 | 0.667 | 0.333 | 0.400 | 1.000 |
| Rohan Desai | 1.000 | 0.000 | 1.000 | 0.000 | 0.000 |
| Divya Sharma | 0.500 | 0.500 | 0.583 | 0.600 | 0.667 |
| Kiran Menon | 0.000 | 1.000 | 0.000 | 0.800 | 1.000 |
| Priya Iyer | 0.885 | 0.333 | 0.833 | 1.000 | 0.667 |

Notice Rohan Desai: perfect 1.000 on Tech and CTC, but 0.000 on Experience and Communication. Without normalization his raw score of 91 would inflate his total. After normalization his weaknesses are equally visible.

### Final Rankings

| Rank | Candidate | Score | What drove it |
|---|---|---|---|
| 1 | Priya Iyer | 72.6% | Best notice period (1.0), strong tech (0.885), low CTC (0.833) |
| 2 | Arjun Pillai | 56.1% | Solid tech (0.731), good CTC (0.750), short notice (0.800) |
| 3 | Rohan Desai | 55.0% | Perfect tech and CTC but zero experience and zero communication |
| 4 | Divya Sharma | 54.3% | Balanced across all criteria — no standout, no weakness |
| 5 | Meera Nair | 45.4% | Best communication but high CTC and long notice drag score |
| 6 | Kiran Menon | 43.0% | Best experience but highest CTC and lowest technical score |

### Blind Spot Analysis

Gap between Rank 1 and Rank 2: **0.165 — STRONG decision.**

| Criterion | Stated Weight | Gap Contribution | Blind Spot? |
|---|---|---|---|
| Technical Score | 35% | 32.6% | No — matches weight |
| Experience (yrs) | 25% | 25.1% | No — well aligned |
| Communication | 10% | 20.2% | ⚠️ Yes — 2× its stated weight |
| Notice Period | 10% | 12.1% | Minor — slightly over-contributing |
| CTC Expected | 20% | 10.0% | ⚠️ Yes — under-contributing vs weight |

**Communication is contributing 20.2% of the ranking gap despite being assigned only 10% weight.** The hiring manager said CTC mattered twice as much as communication. In this result, communication did twice the work. The system flags this — not as an error, but as information.

This is the core value of the engine in one table. The math did not lie. The weights did not lie. But the interaction between them produced an outcome the hiring manager could not have predicted from their stated priorities alone.

---

## Final Reflection

**It is:** a transparent, explainable, mathematically rigorous scoring engine that surfaces conflicts between stated priorities and actual outcomes. Every number can be verified manually. Every result comes with a confidence level. Every conflict is shown without judgment.

**It is not:** a replacement for human judgment. It never tells you who to hire. It tells you whether you are hiring for what you said you cared about.

That distinction was the north star of every decision in this project — from choosing min-max over z-scores, to replacing the confrontational blind spot message with a quiet note, to choosing not to ship a half-built constraint filter. Every one of those choices was the same choice expressed differently: transparency over convenience, honesty over completeness.

The hardest part of any decision is not calculating the answer. It is being honest about what you actually want. Most tools give you the answer and stop. This one asks the harder question: is the answer you got the one you actually intended?

> *"The best systems do not just solve problems. They make you see the problem more clearly than you did before you started."*

---
