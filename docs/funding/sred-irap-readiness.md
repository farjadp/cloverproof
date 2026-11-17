# SR&ED and IRAP readiness notes (CloverProof)

Prepared by the grants specialist, 2026-11-17. Not a lawyer, accountant or SR&ED consultant. **Every tax position here: confirm with the accountant / SR&ED preparer.** Companion to `docs/funding/grants-radar.md`. Access date for all citations: 2026-11-17.

Entity note: which corporation owns CloverProof is open (Ashavid Inc. vs a new corporation). SR&ED belongs to the corporation that incurs the expenditure, so the records below must name the paying entity from day one.

---

## 1. The CRA test (official wording)

Source: CRA, "What work is eligible for SR&ED tax incentives", https://www.canada.ca/en/revenue-agency/services/scientific-research-experimental-development-tax-incentive-program/sred-eligibility.html (2026-11-17), and CRA "Guidelines on the eligibility of work for SR&ED tax incentives", .../sred-policies-guidelines/guidelines-eligibility-work-sred-tax-incentives.html (2026-11-17).

Work must be carried out in Canada and meet both of these:

1. **Technological advancement / uncertainty.** The work is done to advance scientific knowledge or achieve a technological advancement, which CRA describes as "generation or discovery of new knowledge". New knowledge is needed when it is unknown or uncertain whether a result can be achieved. The guidelines page: uncertainty "is needed when it is unknown (or uncertain) whether a given result or objective can be achieved", arising "due to an insufficiency in the available scientific or technological knowledge". You do not have to reach the goal.
2. **Systematic investigation.** A systematic investigation or search in a field of science or technology, through experiment or analysis, that includes: (1) defining a problem, (2) advancing a hypothesis to resolve it, (3) planning and testing the hypothesis by experiment or analysis, (4) developing logical conclusions from the results. The guidelines add that evidence is kept and a systematic approach alone does not make work eligible.

Eligible work types: basic research, applied research, experimental development, and support work that directly supports and is commensurate with those (engineering, design, operations research, mathematical analysis, computer programming, data collection, testing, psychological research). Computer programming is eligible only as support work for the R&D itself.

Excluded: market research or sales promotion; quality control or routine testing; commercial production of a new or improved product; style changes; routine data collection; training and on-the-job learning; hiring experts to apply existing knowledge; purchasing proprietary knowledge.

The CRA eligibility and guidelines pages I read have no dedicated software section. For software questions CRA points to its Self-Assessment and Learning Tool (SALT): https://www.canada.ca/en/revenue-agency/services/scientific-research-experimental-development-tax-incentive-program/self-assessment-learning-tool.html (linked from the eligibility page; not opened).

Money facts used below: ITC 15 percent basic, 35 percent enhanced for CCPCs up to a $6 million limit (tax years beginning after 15 Dec 2024); CCPC refund 100 percent on current expenditures for qualifying CCPCs; non-CCPC corporations get a non-refundable credit; associated corporations share one limit and file T2SCH49 (CRA ITC policy page, .../investment-tax-credit-policy.html). Other government assistance (IRAP, for example) reduces the ITC and provincial credits reduce claimable expenditures ("What are SR&ED tax incentives", .../what-are-sred-tax-incentives.html). Reporting deadline for corporations: 12 months after the T2 due date, about 18 months after year-end (.../sred-claim/get-ready.html).

Unknown to me (from `company-facts.md`): CCPC status, who is on payroll, whether the founder is paid by T4, fiscal year-end, first T2 status. Without eligible salaries or contractor payments there is little to claim.

---

## 2. What could plausibly qualify, and what probably will not

Sources for what the code does: `CLAUDE.md` (hard rules, stack, sprint scope) in this repo.

### 2.1 Possibly eligible (needs a written uncertainty first)

| Work | Possible technological uncertainty | Why it might qualify | Risk it is routine |
|---|---|---|---|
| (a1) **Calibration loop: engine output vs human agronomist final numbers** (rules 4, 8, 11; calibration dataset, 90 percent agreement gate) | Whether a rule-based nutrient method can reproduce human agronomist decisions within a stated tolerance, and what rule changes close the gap | This is a hypothesis-test-conclude loop by design, with dated data per recommendation | **The dataset does not exist yet.** AI-agent reviews do not count toward calibration (rule 11). Evidence starts with the first human agronomist review (Feb-Apr 2027 pilot at the earliest, and no human agronomist is named). Until then there is a plan, not an investigation. A named human also raises "hiring experts to apply existing knowledge" if the agronomist only supplies known answers; the documented question must be about the system, not the agronomy. |
| (a2) **No-soil-test nitrogen estimate from an offline SoilGrids cache, max `medium` confidence** | Whether coarse modelled soil estimates can support an N-rate recommendation with a defensible confidence level, and how estimate uncertainty should propagate into the number and the confidence label | Plausible if the work tests several approaches against reference cases and records what failed | Implementing a published N method with published constants is routine. Constants are `PLACEHOLDER` until a human agronomist validates them (rule 9). The cache build itself (ADR 0006) is data engineering. Eligibility depends on the uncertainty being in how the estimate behaves, not in whether the code works. |
| (a3) **Confidence-rule design** (rule 2: high / medium / low, rule-based) | Whether a rule set can rank recommendations so that low-confidence ones are the ones agronomists change most | Testable against calibration data with a measurable result | Same dependency on real review data. Thresholds that are chosen by judgement and never tested are not R&D. |
| (a4) **GDD-based timing windows with NASA POWER weather (S4)** | Possibly: how gridded daily temperature bias affects timing-window accuracy for Ontario winter wheat | Only if a specific measurable unknown is written down | Growing degree days are a known method; fetch jobs and caching are routine. **Likely routine unless a concrete uncertainty is documented.** |
| (a5) **Future spikes: OCR/LLM soil-report extraction (S20 spike, S21), boundary pre-fill (S19)** | Whether extraction can hit an accuracy target before human confirmation | A spike with an explicit accuracy target and failure criteria is the classic shape | Product wiring around a model API is routine; only the accuracy experiments count. Not started. |

Honest summary: **today the engine work is at the planning stage. Engine v0 (wheat N only, published constants, golden tests) is mostly implementation. The strongest SR&ED candidates become real only when there are experiments with hypotheses and results (a1, a2, a3).** Whether any of it clears the technological-uncertainty test is the preparer's call after reading dated notes, not mine. The Ashavid products (Contivo LLM pipelines, Imedica ECG simulation) are a separate unassessed question in `company-facts.md`; do not mix them into CloverProof projects.

### 2.2 Likely routine (do not claim)

| Work | Why routine | Source |
|---|---|---|
| (b) **Postgres row-level security, org scoping, grants and triggers enforcing immutability and append-only records** (rules 4, 8; `cp_app` non-bypass role, `SET LOCAL app.*`, ADR 0008 pending) | Standard use of documented PostgreSQL features. The question "can we enforce this in the database" has a known answer. I would not claim it. Only if a specific unknown appears (for example a pooling or transaction behaviour that breaks the policy and cannot be solved with known techniques) and is documented, and even then the preparer decides. | `CLAUDE.md` stack and rules |
| (c) **Canadian data residency decision** (real farmer data in Canada; Railway has no Canadian region; ADR needed) | A hosting, compliance and vendor-selection decision. It is not a technological uncertainty about science or technology; the answer is a procurement choice. | `CLAUDE.md` |
| FastAPI, Jinja2, HTMX internal tool; auth (argon2id, sessions, CSRF); CLI account creation; Procrastinate jobs; WeasyPrint PDF; SHA-256 stored on documents; website in 9 locales; deployment; CRUD | Standard engineering with known solutions. CRA excludes commercial production of a product and quality control or routine testing. | `CLAUDE.md` |
| Writing golden tests as regression tests | Routine testing, unless the test is itself the experiment that answers a documented hypothesis | CRA exclusion list |

---

## 3. Records to start keeping now

CRA says records must show what work was done, who, when, and how expenditures were calculated; "Documentation that is dated, signed, and specific to the work performed is best"; keep them throughout the work, not reconstructed later (https://www.canada.ca/en/revenue-agency/services/scientific-research-experimental-development-tax-incentive-program/sred-claim/get-ready.html, 2026-11-17). Accepted types include project plans, lab notebooks, test data, design files, time sheets, payroll records and purchase invoices.

Suggested home: `docs/funding/records/` (create when you start; commit). Nothing here is a CRA form.

### 3.1 Weekly time log (one per person, per week)

| Person | Paid by (entity) | Employment status (T4 / contractor invoice) | Week starting | Date | Project ID | R&D or routine | Hours | Note (what was done, one line) | Where work was done |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | e.g. CP-R1 | R&D / routine | | | Canada? |

Rules: fill the same week, not later. Tag each block R&D or routine honestly; routine blocks are not claimed but still logged (CRA support-work rules require the support to be commensurate with the R&D). The `minutes_spent` metric on agronomist reviews is a different thing; do not use it as payroll evidence. Work done by AI agents is not a person's time; ask the accountant how AI tooling costs and the founder's directing time are treated.

### 3.2 Technological uncertainty note (write before the work; dated; committed)

```
Project ID:            CP-R1
Entity paying:         <Ashavid Inc. / new corp>
Date written:          YYYY-MM-DD   (before work starts)
Author:
Question:              What is unknown? Phrase as "Can X achieve Y under Z?"
Why existing knowledge
does not answer it:    what published methods, tools, or agronomy references
                       you checked (cite), and why they are insufficient
Hypothesis:            what you will try and what result you expect
Success / failure
criteria:              measurable (e.g. agreement within N kg/ha on M cases)
Plan:                  experiments, data, who does what, dates
```

Write one note per distinct question. If you cannot state what is unknown, it is probably routine.

### 3.3 Experiment log (one entry per attempt, including failures)

```
Experiment ID:   EXP-0001     Project: CP-R1     Date: YYYY-MM-DD
Hypothesis:
Method (what was tried; code ref: commit SHA / branch):
Inputs (data version, cases, golden-case IDs):
Result (numbers):
Conclusion (supported / not supported / partly) and why:
Next iteration (and which note it updates):
Time spent (hours, people):
```

Keep failed approaches. Link calibration exports (engine output vs human numbers and reason, per recommendation) as the evidence set.

### 3.4 Git conventions

- Experiment ID in every commit that belongs to an experiment: `EXP-0001: try offline-cache N estimate with soil-order prior`.
- Branches for experiments: `exp/EXP-0001-short-name`. Do not squash away failed attempts; keep branches or tag them (`exp-0001-final`).
- Routine work without an ID (or tagged `ROUTINE:`), so the split is visible in history.
- Commit the dated uncertainty note before the code that tests it. Do not edit old notes; add dated addenda.
- This matches the repo habits (small commits; golden test before engine change).

### 3.5 Contractors, collaborators and IP

- Written agreement for every contractor, including whoever might be the human agronomist and any Mitacs intern: scope, location of work, **who owns the IP (assignment to the paying Canadian corporation)**, confidentiality.
- Keep invoices; separate R&D from other work lines.
- Foreign contractors: work done outside Canada is not eligible (CRA page). Ask the accountant before engaging anyone abroad.
- Contract payments and assistance rules are in CRA's "Assistance and Contract Payments Policy" (named on the CRA "What are SR&ED" page; not read). Ask the accountant.
- University partner or Mitacs: agree IP terms before the intern starts; Mitacs partner funds must be private (Mitacs page).

### 3.6 Entity-paid-by trail

- One table: date, amount, payee, what it paid for, project ID, **which corporation's bank account paid**. No account numbers in files.
- Record every government assistance (IRAP, Mitacs partner top-ups, CSJ, tax credits) with date and amount; it reduces the claim.
- If CloverProof later moves to another corporation, keep the transfer agreement and a written split of work and costs.
- Keep the Ashavid / VisaRoads association facts for the T2SCH49 limit agreement (CRA ITC page).

### 3.7 Calendar

Fiscal year-end, T2 due date and SR&ED reporting deadline (about 18 months after year-end for corporations, CRA get-ready page). Confirm the real dates with the accountant.

### 3.8 Optional: pre-claim approval

CRA evaluates proposed work before you start; available to CCPCs and other Canadian corporations with gross business income under $25M in good standing; up to 3 projects, each valid up to 3 years; you must still file a claim; applied through My Business Account (Farjad does it). Cannot cover a project already in a prior claim. Page dated 2026-10-14. Source: https://www.canada.ca/en/revenue-agency/services/scientific-research-experimental-development-tax-incentive-program/apply-pre-claim-approval.html (2026-11-17). Ask the accountant whether the calibration and no-soil-test projects are good candidates once uncertainty notes exist.

---

## 4. NRC IRAP readiness

**Access limit:** nrc.canada.ca blocks machine access; I did not bypass it. IRAP facts below are from search excerpts of NRC pages on 2026-11-17 and are **unverified: Farjad to confirm.** Cited pages (all unreadable to me): https://nrc.canada.ca/en/support-technology-innovation/financial-support-technology-innovation and https://nrc.canada.ca/en/support-technology-innovation/nrc-irap-funding-hire-young-graduates.

What the excerpts say: minimum criteria are an incorporated, for-profit business operating in Canada with up to 500 FTE, developing and commercializing technology; NRC assesses technical aspects of the innovation, business, management and financial capacity, likelihood of results, commercialization plans and market potential; it does not fund day-to-day operating costs, purely commercial or non-technical work, or work outside Canada; meeting the minimums does not guarantee support. The route in is a phone call (1-877-994-4727), then a referral to an Industrial Technology Advisor (ITA) for a proposal. Funding is a contribution toward eligible costs, not full cost.

### 4.1 What an advisor will probably ask (my inference from the assessment areas above; not an official list)

1. **Team:** who does the technical work, their roles, hours, whether founder-only. Where each is located.
2. **Payroll:** employees on T4 and how many; contractors; whether the founder is paid by salary or dividends. (UNKNOWN in `company-facts.md`; likely decisive.)
3. **Technical plan:** the specific technical challenges (use the uncertainty notes), approach, milestones, risks, what is new versus existing. The advisor will ask what is unknown, not what you plan to build.
4. **Business plan:** customers, market, pilot results, pricing, route to revenue, competitors (positioning table).
5. **Financials:** statements or at least the last year's figures, bank account existence, burn, other funding sought or received (stacking). First fiscal year for Ashavid: UNKNOWN.
6. **Canadian IP ownership:** who owns the code, data, calibration dataset and rules; assignments from contractors and any university partner; open-source licence stance (repo bans GPL/AGPL/EUPL in production).
7. **Corporate structure:** entity, ownership, CCPC status, associated corporations (Ashavid and VisaRoads).
8. **Regulatory and data:** real farmer data stored in Canada (decision 2026-11-16); who reviews outputs (no named human agronomist yet).

### 4.2 Prepare before the call (Farjad calls; I never contact anyone)

- Decide the entity (grants-radar section 1) and be ready to name it.
- A one-page description: problem, approach, what is technically uncertain (use plain words), stage (internal concierge tool now; pilot Feb-Apr 2027; MVP gate May 2027).
- Numbers you know: employees, payroll, fiscal year, revenue, funding to date. If unknown, say so; do not estimate.
- Ask these questions: Does a company with no T4 employees qualify? Is there youth hiring support? Does work already done count? What does an ITA need first? How do IRAP funds interact with SR&ED, Mitacs and CSJ? Is a university partner required or useful?
- Wording rules for CloverProof (positioning D4): do not say "agronomist-reviewed" or imply endorsement; say reviews are currently AI-assisted until a named agronomist joins. Do not describe the rules engine as AI to fit a program.
- Have available but do not email in advance: certificate of incorporation, the uncertainty notes, the architecture and plan documents (`docs/plans/`), and a short budget for the technical work with salaries.

If the advisor says the company is too early, that is a finding, not a failure: use Mitacs and SR&ED records and return after the pilot.

---

## 5. Questions that decide this (answer into `~/Documents/Ashavid-Grants/company-facts.md`)

1. CCPC status of the owning corporation, and whether the new corp (if any) would be associated with Ashavid and VisaRoads.
2. T4 employees and contractor spend per company; is Farjad paid salary or dividends?
3. Fiscal year-end; has a first T2 been filed or planned; any financial statements?
4. Who has done or will do the engine and calibration work, in which entity, and where (Canada)?
5. Any government assistance already received.
6. Whether a human agronomist or academic partner will be engaged, and under what IP terms.
7. Whether the accountant has SR&ED experience with software and agri R&D (if not, a preparer is needed).
