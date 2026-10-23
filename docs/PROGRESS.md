# PROGRESS

What is built, what is in progress, and what is next. Every Claude Code session updates this file in the same pull request as its work.

## Status

| Milestone | Status | Branch / PR | Notes |
|---|---|---|---|
| M0 Repository and tooling | IN REVIEW | feat/m0-scaffold (not yet committed or pushed) | CI not yet run on GitHub |
| M1 Design system and app shells | NOT STARTED | | |
| M2 Database base, auth, isolation | NOT STARTED | | |
| M3 Flats, members, import | NOT STARTED | | |
| M4 Charge setup and calculation engine | NOT STARTED | | |
| M5 Billing runs, bills, PDFs | NOT STARTED | | |
| M6 Payments, receipts, dues | NOT STARTED | | |
| M7 Resident PWA core | NOT STARTED | | |
| M8 Complaints | NOT STARTED | | |
| M9 Notices and email | NOT STARTED | | |
| M10 Committee home and compliance | NOT STARTED | | |
| M11 Analytics and admin tools | NOT STARTED | | |
| M12 Vendor bills, AI, alerts | NOT STARTED | | |
| M13 Quote comparison | NOT STARTED | | |
| M14 Minutes drafting | NOT STARTED | | |

Statuses: NOT STARTED · IN PROGRESS (branch) · IN REVIEW (PR link) · DONE · BLOCKED (question ID)

## Log

Newest first. One entry per merged PR: date, milestone, what was built, how to try it, known gaps.

- 2026-10-23 — M0 — Monorepo per docs/04 §2. Backend: uv project (Python 3.12), FastAPI with `GET /api/v1/health`, pydantic-settings, ruff, pytest; docstring-only stubs for every domain in docs/04 §3 (router, service, schema) and for calc, ai, pdf, notify, jobs, i18n, seed, models, db, auth, deps; no domain router mounted. Front end: pnpm workspace, `committee-web` and `resident-pwa` (Vite 8, React 18, TypeScript 5.9 strict, Tailwind 4) showing the logo and "Coming soon"; `packages/shared` with English strings. `.env.example` for backend and both apps; CI in `.github/workflows/ci.yml`.
  How to try: README "How to run".
  Known gaps: CI not yet run on GitHub (acceptance check open); no `alembic.ini` (comes with M2); only English strings (i18n in M1); GitHub Action versions (`checkout@v4` etc.) not checked against latest; Starlette warns that `httpx` with TestClient is deprecated.

- 2026-10-23 — Docs pack created (CLAUDE.md and docs/). No code yet.

## Restore tests

Record each monthly backup restore test here: date, who, result.
