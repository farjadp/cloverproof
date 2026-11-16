# Agent team

Farjad Iranmehr talks to one agent: **`cloverproof-lead`**. It plans, briefs the specialists, verifies their work and reports back.

```
Farjad Iranmehr ──▶ cloverproof-lead
                       ├── cp-auditor          read-only MVP audit
                       ├── cp-platform         monorepo, uv, CI, Makefile
                       ├── cp-engine           engine/ + packs/ (test-first)
                       │      └─▶ cp-agronomy-guard   reviews every engine/pack change
                       ├── cp-database         Supabase migrations, PostGIS, RLS
                       ├── cp-concierge-app    FastAPI + Jinja2 + HTMX internal tool
                       ├── cp-pdf              WeasyPrint proof PDF + SHA-256
                       ├── cp-qa               go / no-go per sprint step
                       ├── cp-website          website/ (Next.js, i18n, Railway)
                       └── cp-design           Stitch + ChatGPT images, brand
```

## Sessions
Each workstream runs in its own session in the Claude desktop app, started by the lead: **website** (`cp-website`), **web app** (`cloverproof-lead` → `cp-*` engine/db/app/pdf), **mobile** (later). The lead's chat only plans, routes and checks.

## How to talk to the lead
- **Claude desktop app (default):** open a chat in this folder and write normally, in Persian or English. The chat itself acts as `cloverproof-lead`: it plans, briefs the `cp-*` specialists in the background and reports back in the same chat. No terminal needed.
- `.claude/settings.json` sets `"agent": "cloverproof-lead"`, so new sessions in this folder start as the lead.
- Optional, terminal: `claude --agent cloverproof-lead`.

Example: *"Start Sprint 1 Step 1. The old MVP is at ~/path/to/rootwise."*

## Design source
UI designs live in the Google Stitch project: https://stitch.google.com/projects/16684636636144399285 — `cp-concierge-app`, `cp-pdf` and any future website/mobile work start from it. Agents read it through the browser; they never edit it without asking.

Definitions live in `.claude/agents/*.md`. They override global agents with the same name.
