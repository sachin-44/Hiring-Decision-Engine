# RESEARCH LOG
### Decision Companion System — Hiring Edition

## Overview

This log documents every AI prompt used, every Google search made, every academic reference consulted, and every decision made about what to accept, reject, or modify from AI output.

The ideas in this project are mine. AI was used to check if things were implementable, to get explanations of concepts, and to confirm I was not missing something. Every architectural decision was mine.

**82 prompts · 13 searches · 9 references · 22 decisions evaluated**

---

## Section 1 — Ideation and Research Prompts

These are the prompts used to think through the problem before writing any code. Written exactly as asked — in plain language, not polished for presentation.

### Part A — Problem Framing (Prompts 1–13)

| No. | Prompt |
|-----|--------|
| 1 | i want to build a decision system for hiring. the idea is the user enters actual raw data like salary numbers experience in years notice period days test scores. not ratings 1 to 10. actual numbers. is this a good idea or will it cause problems |
| 2 | ok so what is normalization exactly. i know the word but not how it works mathematically. can you explain it simply |
| 3 | wait but for things like CTC and notice period lower is better right. so if i normalize normally the candidate with the highest salary expectation gets a 1.0 which means best. that is wrong. how do i fix the direction |
| 4 | i want to normalize weights too. like if someone puts 8 and 2 vs 80 and 20 the proportion should be the same and results should be identical. is there a formula for this |
| 5 | what if two candidates have the exact same value on a criterion. like both have 3 years experience. then max minus min is zero and i get divide by zero in the normalization. what do i do |
| 6 | i want to show the user not just who ranked first but also how confident the result is. like if first and second place are very close that feels different from first place winning by a lot. is there a way to measure this |
| 7 | also what if someone changes one weight slightly would the ranking change. is there a way to test if the result is sensitive to weight changes |
| 8 | when i tested my system i set communication as weight 9 out of 10 meaning most important. but the top ranked candidate had the lowest communication score. the math is technically correct but the result contradicts what i said i care about. how do i detect this situation and show it to the user |
| 9 | after showing the blind spot note i want to also show the user what the ranking would look like if their stated weights were fully honored. like a what-if view. is this implementable |
| 10 | i want to add a hard constraint filter before scoring. like if a candidate wants more salary than the budget or has more notice period than acceptable they should be eliminated before scoring even starts. is this how real hiring tools work |
| 11 | for the scoring formula should i just do weighted sum or is there a better method. i heard of something called TOPSIS is that better |
| 12 | i also heard of AHP analytic hierarchy process for setting weights. where the user compares criteria in pairs instead of assigning numbers directly. is that more accurate and should i use it |
| 13 | how should i structure the code. like should normalization and scoring be in the same function or separate |

> **Note on Prompt 8:** This prompt came from a real moment during testing — not from planning. I had built the scoring engine correctly. I ran it with Communication as the top weight. The result showed a candidate with the lowest communication score ranked first. The math was right. The result contradicted stated intent. I asked Claude for the math to detect and surface this conflict. Claude gave me the formula. Claude also suggested confronting the user with a direct question: *"Are you optimising for budget over quality?"* I rejected that entirely and replaced it with a quiet factual note. That call was mine — it came from thinking about the user, not from the AI.

---

### Part B — Deeper Conceptual Prompts (Prompts 14–44)

| No. | Prompt |
|-----|--------|
| 14 | what problem does a decision making tool actually solve |
| 15 | is weighted scoring the right model for comparing job candidates |
| 16 | why does multiplying weight by score not always give a fair result |
| 17 | when does adding more criteria make the result worse not better |
| 18 | can two completely different weight sets produce the same ranking |
| 19 | what does it mean when the top option scores high on weight but low on raw value |
| 20 | if i remove the least important criteria does the ranking change |
| 21 | at what point is a scoring tool making the decision instead of supporting it |
| 22 | what if i add a new candidate later — does it change the scores of existing ones |
| 23 | can normalization create bias when the user sets the min and max themselves |
| 24 | should i show users their normalized values or just the raw numbers they entered |
| 25 | if user gives weights 1 1 1 1 is that equal importance or confusion |
| 26 | if one criteria has weight 90 and five others share 10 is it still multi-criteria |
| 27 | how do i warn the user when one criteria is dominating the entire result |
| 28 | can i suggest weights automatically based on how spread the option values are |
| 29 | what is the smallest weight change that flips the top ranked option |
| 30 | if i tested 1000 random weight combinations and the same option wins every time what does that mean |
| 31 | how do i decide when a decision is stable versus when it could easily go the other way |
| 32 | what does it mean when the user said salary matters 40 percent but it only drove 12 percent of the score |
| 33 | how do i show the user what actually drove their decision versus what they thought mattered |
| 34 | how do i tell the user one criteria dominated the result without making them feel they did something wrong |
| 35 | is this tool objective or does it just reflect whatever bias the user put in through their weights |
| 36 | should i tell the user when their weights make the result almost certain no matter what the options are |
| 37 | what is the risk of showing a bar chart when two scores are very close together |
| 38 | if two options score exactly the same what should the tool do |
| 39 | should the tool let the user change weights after seeing the result or is that gaming the system |
| 40 | how do i explain to a non-technical user that two close scores are not the same as a tie |
| 41 | what is the minimum output the results page needs to make the decision auditable |
| 42 | should sensitivity results be shown to the user or kept in the background |
| 43 | what does a decision report need to include to be genuinely useful |
| 44 | how do i handle the case where all candidates are eliminated by the hard constraint filter and nothing is passed to the scoring engine |

---

## Section 2 — Development Prompts

These are the prompts used while building — writing functions, fixing bugs, structuring views and templates. Each prompt was asked after the architectural decision had already been made. These are implementation requests, not design requests.

| No. | Prompt |
|-----|--------|
| 1 | write a python function that takes candidate values and criteria with min max bounds and direction and returns normalized scores using min max normalization with direction awareness |
| 2 | now write a function that takes normalized scores and criteria weights and calculates a weighted sum score for each candidate and returns them sorted highest to lowest |
| 3 | how do i calculate the stability margin between the top two candidates and return a label like strong moderate or fragile based on the gap |
| 4 | write the perturbation test function. it should take the candidates criteria and normalized scores increase the highest weight by 5 percent recalculate and return whether the winner changed |
| 5 | write the blind spot detection function. for each criterion calculate stated importance as weight divided by total weight and actual influence as the criterion contribution to the gap between rank 1 and rank 2. flag if actual influence is more than 40 percent |
| 6 | i want to show a breakdown per candidate showing how much each criterion contributed to their final score as a percentage. write a function that returns this breakdown |
| 7 | write the what if recalculation function. it takes updated weights from the sliders and recalculates all scores and returns the new ranking as json |
| 8 | write the final recommendation object builder. it should include the top candidate name total score breakdown stability label sensitivity result and any blind spot notes |
| 9 | i have a table element in html that shows candidate scores. how do i highlight the winning row and also color code each cell based on how high or low the normalized score is |
| 10 | write the input validation function. it should check that at least 2 candidates are entered at least 1 criterion is defined all score values are numbers and all weights are positive numbers and return an error message for each violation |
| 11 | the what if section is showing even when there is no blind spot detected. how do i conditionally render it only when a flag exists |
| 12 | i want the breakdown bar chart per candidate to animate when results are first shown. how do i do a simple css width animation that triggers on load |
| 13 | how do i recalculate scores when the user adjusts a weight without reloading the whole page |
| 14 | how do i return ranked results as json from a django view for a fetch request |
| 15 | how do i guard the results view so it does not render with incomplete session input |
| 16 | how do i build a table in django template that shows each criteria score per option |
| 17 | how do i show the stated versus actual weight comparison table without extra database calls |
| 18 | how do i show a stability warning only when the sensitivity check found a rank flip |
| 19 | how do i format a decimal score as a percentage in a django template |
| 20 | how do i build a weight slider in html that sends updated weights to django and refreshes scores without reloading |
| 21 | how do i draw score bars using only css without a chart library |
| 22 | how do i build a print version of the results page that hides navigation and buttons |
| 23 | how do i write a unit test for the normalization function covering the edge case where max equals min |
| 24 | how do i test that the ranking output is correct for a known set of inputs |
| 25 | how do i test that the sensitivity function correctly flags a rank flip |
| 26 | how do i test the scoring function without hitting the database |
| 27 | how do i check that contribution percentages always add up to 100 for any input |
| 28 | the best per criteria section on the results page is showing all zeros. no error no crash just wrong data. the scoring function output is correct. what could cause this |
| 29 | django session serializes data to json. could that be converting integer dictionary keys to strings on roundtrip. if so how do i write a lookup that handles both integer and string versions of the same key |
| 30 | write a csv upload view that reads candidate rows maps column headers to criteria names flags mismatched headers before processing and passes valid candidates to the scoring engine |
| 31 | how do i add smart keyword detection for common hiring criteria patterns so the system auto-applies realistic scale bounds when it recognises the criterion type |
| 32 | how do i implement a shortlist size input so the results page focuses on the top n candidates but the full ranked list is still available in the export |
| 33 | the landing page url is routing to step 1 instead. there are two urls.py files in the project. which one controls the root url and how do i debug which file django is reading |
| 34 | after a csv upload completing a new manual session still shows all the csv candidates. how do i clear the session state when the user starts a fresh manual entry |
| 35 | how do i export the full results including all candidates scores weights breakdown stability and blind spot notes as a pdf from django |
| 36 | how do i keep scoring configuration like weight delta and blind spot threshold out of the code and in environment variables |
| 37 | how do i avoid extra database queries on the results page |
| 38 | write requirements.txt for this django project and explain how to deploy it to a linux server |

> **Note on Prompts 28 and 29:** Prompt 28 came after forty minutes of finding nothing. The scoring function was correct. The template was reading the right variable. Print statements showed the right data in the terminal. The results page showed zeros — no error, no crash, confidently wrong. I described the symptom to Claude. Prompt 29 was the follow-up once Claude identified JSON serialization as the likely cause. Two prompts. Forty minutes of prior searching. The fix was a two-line helper function. The lesson: describe the symptom precisely, including what you have already ruled out.

---

## Section 3 — Google and Google Scholar Searches

Used to verify AI answers independently, find academic sources, and validate decisions against existing literature. AI was never the only source for a consequential decision.

| No. | Query | Platform | What It Confirmed or Changed |
|-----|-------|----------|------------------------------|
| 1 | weighted scoring model decision making research | Google Scholar | Found Hwang & Yoon (1981) and Belton & Stewart (2002) as foundational MCDM references — confirmed additive aggregation was the right model |
| 2 | min max normalization formula | Google | Confirmed the formula and verified edge case behaviour with identical values |
| 3 | min max normalization problems with small datasets | Google Scholar | Confirmed sensitivity issues with fewer than 4 options — informed the stability warning design |
| 4 | TOPSIS method explained simply | Google Scholar | Reviewed the full method. More rigorous but users cannot verify results without understanding the algorithm. Transparency won. |
| 5 | AHP analytic hierarchy process pairwise comparison weights | Google | Confirmed AHP is more precise but requires n(n−1)/2 questions before a candidate is entered. Too much friction for first use. Deferred. |
| 6 | rank reversal multi criteria decision making | Google | Found research on rank reversal — shaped the user-defined scale bounds feature and the warning about adding new candidates |
| 7 | stated preference vs actual behaviour decision bias | Google Scholar | Led to Kahneman (2011). Directly informed the blind spot detector philosophy. |
| 8 | how does applicant tracking system filter candidates | Google | Confirmed real ATS tools use hard elimination before scoring. Validated the constraint filter as a planned feature. |
| 9 | Kahneman decision making stated preferences actual behavior | Google Scholar | Found the specific research on the preference-behaviour gap. Shaped the framing of the blind spot detector. |
| 10 | weighted sum vs TOPSIS hiring decision | Google Scholar | Confirmed weighted sum is standard for interpretable hiring tools. TOPSIS is used in academic research but not practitioner tools. |
| 11 | division by zero normalization same values fix | Google | Multiple approaches found. Returning 0.5 (neutral) confirmed as most honest for the hiring context. |
| 12 | sensitivity analysis 10 percent threshold literature | Google Scholar | Found academic basis for 10% perturbation as standard sensitivity delta — consistent with Saltelli et al. (2008). |
| 13 | anchoring bias decision interface design | Google Scholar | Confirmed separating weight input from score results reduces anchoring. Shaped the wizard step order. |

---

## Section 4 — References That Influenced the Approach

Each reference changed something — either confirming a direction or ruling one out.

| No. | Reference | How It Influenced the Project |
|-----|-----------|-------------------------------|
| 1 | Hwang, C.L. & Yoon, K. (1981). *Multiple Attribute Decision Making*. Springer. | Core theoretical foundation. Justified the additive weighted sum model and direction-aware normalization. TOPSIS was also documented here — reviewed and rejected in favour of transparency. |
| 2 | Belton, V. & Stewart, T. (2002). *Multiple Criteria Decision Analysis*. Kluwer. | Helped define scope boundaries. Confirmed compensatory models are right for hiring. Confirmed threshold elimination belongs as a pre-filter, not the main engine. |
| 3 | Saltelli, A. et al. (2008). *Global Sensitivity Analysis*. Wiley. | Informed the sensitivity analysis design. Confirmed 10% weight perturbation as standard. The binary stable/unstable output is a simplification — documented as a planned improvement. |
| 4 | Kahneman, D. (2011). *Thinking, Fast and Slow*. Farrar, Straus and Giroux. | The preference-behaviour gap described here is exactly what the blind spot detector surfaces. Anchoring bias research informed separating weight input from score display. |
| 5 | Saaty, T.L. (1980). *The Analytic Hierarchy Process*. McGraw-Hill. | Showed direct weight assignment is less reliable than pairwise comparison. Not implemented but shaped the AHP entry in the improvement roadmap. |
| 6 | Molnar, C. (2022). *Interpretable Machine Learning*. Online. | Used to evaluate SHAP and LIME. Both rejected — they require probabilistic or ML models. The deterministic scoring engine needs no post-hoc explainability. |
| 7 | Workday / Greenhouse ATS Documentation | Confirmed real hiring software uses hard elimination before scoring. Directly shaped the constraint filter as a deliberate deferral rather than an oversight. |
| 8 | Django Official Documentation — docs.djangoproject.com | Primary reference for session management, ORM, formsets, and testing throughout development. |
| 9 | Two Scoops of Django — Greenfeld & Roy (2022) | Informed project structure and separation of business logic from views. The pure Python scoring engine separate from Django ORM came partly from this. |

---

## Section 5 — What I Accepted, Rejected, and Modified

Every AI suggestion was evaluated against the project needs and the actual user. The reason column is the important one.

| No. | AI Output / Suggestion | Decision | Reason |
|-----|------------------------|----------|--------|
| 1 | Raw inputs instead of 1–10 ratings | ✅ Accepted | Preserves real data. Pre-summarizing loses information at the input stage — the worst moment for it. |
| 2 | Min-max normalization as standard approach | ✅ Accepted | Right fit for bounded user-input data. Output is always 0–1, verifiable manually, direction-aware. |
| 3 | Z-score normalization for scale removal | ❌ Rejected | Produces negative numbers. A hiring manager cannot interpret −0.73. Interpretability is non-negotiable. |
| 4 | Return 0 when max equals min in normalization | ✏️ Modified | Changed to return 0.5. Zero unfairly penalises a criterion where all candidates are equal. Neutral is honest. |
| 5 | TOPSIS as a more rigorous scoring method | ❌ Rejected | Users cannot verify results without understanding the algorithm. Transparency wins over rigour. |
| 6 | AHP as primary weight method | ❌ Rejected | Requires n(n−1)/2 questions before a candidate is entered. Too much friction for first use. Deferred. |
| 7 | Entropy weighting to auto-suggest weights | ❌ Rejected | The tool's purpose is to let users express their own priorities. Auto-weighting defeats that purpose. |
| 8 | 10% weight shift as sensitivity test delta | ✅ Accepted | Consistent with Saltelli et al. (2008). Applied as default perturbation value. |
| 9 | Label stability output as "Confidence Score" | ✏️ Modified | Renamed to Stability Level. Confidence implies probability — this system is deterministic. Misleading label. |
| 10 | Show full numeric sensitivity output to user | ✏️ Modified | Reduced to plain language flag. Raw numbers computed but not shown — the label is more actionable. |
| 11 | Confrontational blind spot message — *"Are you optimising for budget over quality?"* | ❌ Rejected | Triggered defensiveness in testing. A good companion informs. It does not interrogate. |
| 12 | Quiet factual note for blind spot instead | ✅ Accepted | Same information, no challenge. The decision-maker draws their own conclusion. |
| 13 | What-if recalculation as automatic display | ✏️ Modified | Made into an optional interactive button. Forcing it after every result was intrusive. |
| 14 | Hard constraint pre-filter — implement in v1 | ✏️ Modified | Architecture accepted. Implementation deferred. A filter without clear elimination feedback is worse than no filter. |
| 15 | Additive weighted sum as aggregation method | ✅ Accepted | Multiplicative rejected — a zero score wipes out all other criteria. Additive is compensatory. |
| 16 | Store normalized scores in the database | ❌ Rejected | Creates staleness risk if values change. Recalculating from raw inputs on each request is safer. |
| 17 | Class-based views for all pages | ✏️ Modified | Used function-based views for calculation-heavy pages — clearer flow control for complex context. |
| 18 | Session storage for multi-step form state | ✅ Accepted | Correct pattern for holding partial input before committing to database. No half-written records. |
| 19 | Dark editorial landing page design | ❌ Rejected | Wrong for the audience. The user is a hiring manager with a browser, not a developer. Fully redesigned. |
| 20 | SHAP or LIME for explainability | ❌ Rejected | Both require a probabilistic or ML model. Incorrect for a deterministic scoring system. |
| 21 | Machine learning to improve accuracy | ❌ Rejected | Adds opacity with no real benefit. Deterministic scoring is more transparent and requires no historical data. |
| 22 | Mock ORM aggregates in unit tests | ✅ Accepted | Correct isolation strategy. Lets the scoring engine be tested independently of database state. |

---

## Final Note on AI Usage

Eighty-two prompts. Thirteen searches. Nine references. Twenty-two decisions evaluated.

AI was useful for four things: confirming that an approach was mathematically correct before committing to it, generating implementation code for decisions already made architecturally, diagnosing bugs when I had already ruled out four possible causes, and surfacing the names of methods — TOPSIS, AHP, Saltelli — that I then researched independently before deciding whether to use them.

AI was wrong about two things. The landing page design was dark and editorial — completely mismatched to a hiring manager opening a browser. The blind spot message was confrontational — it challenged the user's judgment rather than informing it. Both required complete rewrites. The gap between the first AI output and the final version of both those features is the clearest illustration of where human judgment was irreplaceable.

The most significant moment was Prompt 8. I noticed the blind spot problem myself during testing. Claude gave me the math to formalize it. Claude also suggested challenging the user with a direct question. I rejected that and replaced it with a quiet note. That call came from thinking about the user. Not from the AI.

That is how AI was used in this project — as a tool to check, confirm, and implement. Not to decide.

---

