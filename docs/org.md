# CloverProof agent organisation

Farjad Iranmehr talks to **one** agent: `product-manager` (CPO / VP Product), in a Claude desktop chat.
The CPO briefs group heads → heads brief specialists → results flow back up → every head sends a standard report to `documentation-manager`, which keeps Notion.

```
Farjad Iranmehr
 └─ product-manager (CPO) ──────────────────────────────────────┐
     ├─ cto             Engineering (website, web app, platform) │
     │   └─ cloverproof-lead  web-app delivery (cp-* chain)      │
     ├─ head-of-mobile  Mobile app (after the web app)           │ every head →
     ├─ cro             Revenue & Growth                         │ documentation-manager
     ├─ coo             Operations                               │ → Notion
     ├─ head-of-data    Data & AI                                │
     ├─ cso             Strategy & BD                            │
     └─ ciso            Security                                 ┘
```

**Where agents live.** `P` = CloverProof project agent in `.claude/agents/` (only this repo). `G` = global agent in `~/.claude/agents/`, shared with Farjad Iranmehr's other projects; it is told to follow this repo's `CLAUDE.md` over its own defaults. A project agent with the same name as a global one overrides it here.

## Roster (every requested role → agent)

### Product — CPO: `product-manager` (P)
| Role | Agent |
|---|---|
| Product Manager | `cp-product-manager` (P) |
| Product Owner | `agile-manager` (G) |
| UX Researcher | `ux-researcher` (G) |
| UX/UI Designer (web & mobile) | `product-designer` (G) + `cp-design` (P) |
| Product Designer | `product-designer` (G) |
| Product Analyst | `data-analyst` (G) |
| Product Operations | `project-manager` (G) |

### Engineering — CTO / VP Engineering: `cto` (P)
| Role | Agent |
|---|---|
| Tech Lead / Software Architect | `tech-lead` (G), `system-architect` (G) |
| Backend Developer / API Engineer | `cp-concierge-app` (P) for `app/`, `cp-engine` (P) for `engine/`, `backend-developer` (G) elsewhere |
| Database Architect / Engineer | `cp-database` (P) |
| Frontend Developer (web) | `cp-website` (P) for `website/`, `frontend-developer` (G) elsewhere |
| Mobile Developer | via `head-of-mobile` |
| QA / Test Automation | `cp-qa` (P) |
| DevOps / Cloud Infrastructure | `devops-engineer` (G), `cp-platform` (P) for repo tooling/CI |
| Security Engineer | `security-engineer` (G) |
| Web-app delivery lead | `cloverproof-lead` (P) |
| Agronomy integrity reviewer | `cp-agronomy-guard` (P) |
| AI agronomist (stand-in, `ai_reviewed` only) | `cp-agronomist` (P) |
| Proof PDF | `cp-pdf` (P) |
| MVP auditor | `cp-auditor` (P) |
| Git, PRs, merges, releases, CI, Dependabot | `release-manager` (P) — merge policy in `.claude/agents/release-manager.md` |

### Mobile Engineering — Head of Mobile: `head-of-mobile` (P)
| Role | Agent |
|---|---|
| Mobile Tech Lead / Architect | `mobile-architect` (G) |
| iOS Developer | `ios-developer` (G) |
| Android Developer | `android-developer` (G) |
| Mobile UI/UX Designer | `mobile-ui-designer` (G) + `cp-design` (P) |
| Mobile QA / Automation | `mobile-qa-engineer` (G) |
| Mobile Backend / API Integration | `mobile-integration-engineer` (G) |
| Mobile DevOps / Release | `release-manager` (G) |
| Mobile Performance | `mobile-performance-engineer` (G) |

### Revenue & Growth — CRO / VP Growth: `cro` (P)
| Role | Agent |
|---|---|
| Growth Marketing | `growth-marketer` (G) |
| Digital / Performance Marketing | `performance-marketer` (G) |
| SEO & ASO | `content-seo-strategist` (G), `aso-specialist` (G) |
| Content / Social Media | `content-social-marketer` (G) |
| Email marketing | `email-marketing-specialist` (G) |
| Sales / BD Representative | `sales-development-rep` (G) |
| Account Executive / Sales Manager | `account-executive` (G) |
| Partnership & BD Manager | `partnerships-manager` (G) |
| Revenue Operations / CRM | `revops-specialist` (G) |

### Operations — COO: `coo` (P)
| Role | Agent |
|---|---|
| Operations Manager | `operations-manager` (G) |
| Customer Success Manager | `customer-success-manager` (G) |
| Customer Support Specialist | `customer-support-specialist` (P) |
| Customer Onboarding Specialist | `customer-onboarding-specialist` (P) |
| Finance & Accounting | `finance-accounting-specialist` (G) |
| HR / People Operations | `hr-people-specialist` (G) |
| Legal & Compliance | `legal-compliance-specialist` (G) |
| Administrative Coordinator | `admin-coordinator` (G) |
| Grants & funding | `grants-specialist` (G) |

### Data & AI — Head of Data: `head-of-data` (P)
| Role | Agent |
|---|---|
| Data Engineer | `data-engineer` (G) |
| Data Analyst / BI | `data-analyst` (G) |
| AI / ML Engineer | `ml-engineer` (G) |
| LLM / AI Application Engineer | `llm-engineer` (G) |
| MLOps Engineer | `mlops-engineer` (G) |
| Data Scientist | `data-scientist` (P) |
| Data Governance & Quality | `data-governance-specialist` (P) |

### Strategy & BD — CSO: `cso` (P)
| Role | Agent |
|---|---|
| Business Strategy Manager | `business-strategist` (G) |
| Market Research / Competitive Intelligence | `market-research-analyst` (G) |
| Strategic Partnerships Manager | `partnerships-manager` (G) |
| Business Model & Monetization | `business-strategist` (G) |
| Fundraising / Investor Relations | `investor-relations-manager` (G) |

### Cybersecurity — CISO: `ciso` (P)
| Role | Agent |
|---|---|
| Security Engineer | `security-engineer` (G) |
| Privacy & compliance | `legal-compliance-specialist` (G) |
| Infrastructure hardening | `devops-engineer` (G) |

### Documentation: `documentation-manager` (P)
Single writer of the CloverProof Notion space. Structure in `.claude/agents/documentation-manager.md`.

## Cascade protocol
1. **Farjad Iranmehr → product-manager.** The CPO clarifies, decides which groups are involved, shows a plan for anything non-trivial.
2. **CPO → heads.** Long workstreams run as visible sessions in the Claude desktop app (name = head or owner agent); quick lookups as subagents.
3. **Head → specialists** with the `Agent` tool (parallel when independent). Heads never do specialist work.
4. **Cross-group** goes head → CPO → head, never specialist → specialist. A session may message another running session it was told about.
5. **Up-reporting.** Specialist → head (its Deliver format). Head → CPO: decision, evidence, trade-offs, open questions, next. Head → `documentation-manager`: the standard report.
6. **Integration.** Code-writing work happens on its own branch/worktree; `release-manager` alone pushes, opens PRs and merges, one at a time. Nothing reaches `main`, production, DNS, billing, customers or investors without Farjad Iranmehr's explicit go.

## Standard report (to documentation-manager)
```
Task:        <one line>
Group/agent: <head> via <specialists>
Outcome:     <what is now true>
Evidence:    <PR/commit/URL/doc path>
Decisions:   <decision — why — alternatives rejected>
Open items:  <owner — item — due>
Next:        <one action>
```
Send it to a running session named `documentation` if one exists (`mcp__ccd_session_mgmt__send_message`), otherwise spawn `documentation-manager` with the report as its prompt. Facts only; never secrets or personal data.

## Group output folders
`docs/product/`, `docs/engineering/` (+ `docs/adr/`), `docs/mobile/`, `docs/growth/`, `docs/operations/`, `docs/data/`, `docs/strategy/`, `docs/security/`, `docs/design/`.
