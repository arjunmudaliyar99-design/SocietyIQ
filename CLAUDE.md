# CLAUDE.md — SocietyIQ build instructions

You are building **SocietyIQ**: committee software (web) plus a resident app (PWA) for Indian cooperative housing societies, starting in Mumbai and Thane, Maharashtra.

**Read this whole file before doing anything.** Then read the docs listed in "Where the truth lives". This file is short on purpose; details are in `docs/`.

---

## 1. The one rule above all: do not invent

Several people and several Claude Code sessions work on this repo. Invented details spread and become bugs. So:

1. **The docs in `docs/` are the source of truth.** If something is not written there, it is not decided.
2. **Never invent business rules, legal values, rates, caps, prices, bye-law rules, Maharashtra law, GST rules or tax rules.** Legal limits (12% interest cap, 10% non-occupancy, fund minimums) come only from the `legal_parameters` table, seeded from `docs/08` §3. If you need one, add a question to `docs/10_OPEN_QUESTIONS.md`, put a clearly marked placeholder in code (`# TODO(confirm): <question id>`), make the value configurable, and keep going.
3. **Never invent library APIs.** Check the installed version (`uv pip show`, `pnpm list`) and its docs before using a function you are unsure of. If a command fails, read the error; do not guess a different API.
4. **Never say "done" without running it.** Run the tests, run the linter, start the app if it has a UI. Report what you ran and the result. If you could not run something, say so plainly.
5. **Never use fake data that looks real.** Seed data uses the fictional societies in `docs/02_PRODUCT_SPEC.md` §12. No real names, phone numbers or bank details.
6. **When docs conflict, stop and ask.** Do not pick one silently. Note it in `docs/10_OPEN_QUESTIONS.md`.
7. **Ignore Claude artifact runtime files.** Files like `user.d.ts`, `db.d.ts`, `sample.d.ts`, `room.d.ts`, `*.js.json` and anything calling `claude.use(...)` or `window.claude` belong to the old claude.ai prototype runtime. They are NOT part of this product. Do not copy their APIs.

## 2. Where the truth lives

| Need | Read |
|---|---|
| Why we build it, market, competitors, team | `docs/01_BUSINESS_CONTEXT.md` |
| What to build: modules, screens, flows | `docs/02_PRODUCT_SPEC.md` |
| How it looks and feels (elderly-first, brand, languages) | `docs/03_DESIGN_SYSTEM.md` |
| Stack, folders, security, AI, hosting | `docs/04_ARCHITECTURE.md` |
| Tables and columns | `docs/05_DATABASE.md` |
| Money rules, billing, dues, alerts, AI guardrails | `docs/06_RULES_AND_CALCULATIONS.md` |
| What to build next, in order, with acceptance checks | `docs/07_BUILD_PLAN.md` |
| Legal rules the software must follow | `docs/08_LEGAL_AND_COMPLIANCE.md` |
| Full legal reference (Acts, sources) | `docs/legal/LEGAL_REFERENCE.md` |
| Marketing plan and brand book (for content, not code) | `docs/marketing/MARKETING_AND_BRAND.md` |
| Human setup: GitHub, tools, hosting, how to run many sessions | `docs/09_SETUP_GUIDE.md` |
| Undecided things | `docs/10_OPEN_QUESTIONS.md` |
| What is already built | `docs/PROGRESS.md` |
| Decisions made during the build | `docs/DECISIONS.md` |
| Raw inputs from advisors | `docs/inputs/` |
| Brand files, old decks, old prototype | `reference/` (look, do not copy code) |

## 3. Stack (decided)

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, Pydantic v2, pytest. Package manager: `uv`.
- **Database:** PostgreSQL 16, hosted on Supabase (region: Mumbai). Supabase also provides Auth and private file Storage.
- **Frontend:** React 18 + TypeScript + Vite, Tailwind CSS, React Router, TanStack Query, react-i18next. Package manager: `pnpm` workspaces.
- **Two front-end apps:** `apps/committee-web` (desktop-first) and `apps/resident-pwa` (mobile-first, installable PWA). Shared UI and translations in `packages/shared`.
- **Hosting:** demo on Vercel (front ends) + Render (FastAPI) + Supabase. See `docs/04_ARCHITECTURE.md` §9.

Do not add other frameworks, databases, queues or microservices without a decision recorded in `docs/DECISIONS.md` and agreed by the Founder or the Co-founder (Engineering).

## 4. Non-negotiable product rules

1. **Code calculates, AI only reads and writes words.** Totals, GST sums, dues, interest, averages, percentages and alerts are computed by tested Python code. An AI model never computes or "fixes" a number.
2. **A person confirms anything AI extracts** before it becomes a record. AI never overwrites a value a person confirmed.
3. **Money is stored as integer paise** (`BIGINT`). Never floats. Use `Decimal` in Python only when a rate is involved, and round with the rule in `docs/06`.
4. **Society A must never see Society B's data.** Every table with society data has `society_id`. Every query is scoped by it in the API layer, AND PostgreSQL row-level security enforces it (see `docs/04` §6). Every new endpoint gets an isolation test.
5. **Never delete financial records.** Reverse them with a reason. Every change to money or member data writes to `audit_log`.
6. **SocietyIQ never holds residents' money.** Payments go to the society's own bank account.
7. **Collect minimum personal data.** No Aadhaar, no PAN.
8. **Elderly-first UI.** Big text, big buttons, few choices per screen, plain words. Follow `docs/03_DESIGN_SYSTEM.md` exactly. If a screen needs more than 5 primary actions, split it.
9. **English is the main language** of code, docs and the default UI. Every user-facing string goes through i18n with keys in `en`, `mr`, `hi`, `gu`, `ta`. Never hard-code UI text.
10. **WhatsApp features show "Coming soon".** Do not build WhatsApp integration until the build plan says so.
11. **AI wording is advisory, never accusing.** "22% higher than last contract, review before approval", never "overcharging" or "fraud". See `docs/06` §12.

## 4a. Company identity (applies to all code, UI, PDFs, emails, seed data and comments)

SocietyIQ is a company product. It must look and read like one.

1. **No personal names of founders, team members, advisors, mentors or referrals** anywhere in the software, the PWA, PDFs, notification templates, seed data, test data, code comments or commit messages. Use roles in docs ("the Founder", "the advisor") and nothing at all in the product.
2. **The only brand in the product is "SocietyIQ"**, with the logo files in `reference/brand/`.
3. **Support contact** shown in the apps comes only from configuration: `SUPPORT_EMAIL`, `SUPPORT_PHONE`, `SUPPORT_HOURS`, `COMPANY_LEGAL_NAME`, `COMPANY_ADDRESS`. Never hard-code a person's phone number or email. Until real values exist, use clearly fake placeholders such as `support@example.com`.
4. Old decks, videos and the prototype in `reference/` contain a personal phone and email. **Never copy them.**
5. Footer and legal pages say "© SocietyIQ" plus `COMPANY_LEGAL_NAME` from configuration once the business is registered.
6. People inside each society (members, champion, committee) are the society's own data entered by the society; that is fine.

## 5. How to work in this repo (every session)

1. `git pull` on `main`. Read `docs/PROGRESS.md` to see what exists and what is in progress.
2. Pick **one** task from `docs/07_BUILD_PLAN.md` that is not marked in progress. Mark it `IN PROGRESS (<your branch>)` in `docs/PROGRESS.md` and commit that first, so other sessions see it.
3. Create a branch: `feat/<milestone>-<short-name>`, for example `feat/m4-billing-run`.
4. Build the smallest version that meets the task's acceptance checks. Write tests first for money logic.
5. Database changes: only through a new Alembic migration. One migration per task. Never edit an old migration that is already on `main`.
6. Run: backend `uv run pytest` and `uv run ruff check`; front end `pnpm -r lint` and `pnpm -r test` and `pnpm -r build`.
7. Update `docs/PROGRESS.md` (what you built, how to try it, known gaps) and, if you made a decision, `docs/DECISIONS.md`.
8. Open a pull request. Describe what changed, what you ran, and anything unfinished.

**Do not** edit files that another in-progress task owns. If you must, note it in the PR.

## 6. Commands (fill in as the repo grows; keep accurate)

```bash
# backend
cd backend
cp .env.example .env               # first time only
uv sync
uv run alembic upgrade head        # needs MIGRATIONS_DATABASE_URL; see docs/09 §6a
uv run python -m app.seed           # fictional demo data (idempotent; never in production)
uv run uvicorn app.main:app --reload --port 8000
uv run ruff check . && uv run ruff format --check .
uv run pytest                      # DB tests need local Postgres on :54329 (docs/09 §6a)
uv run python scripts/export_openapi.py ../packages/shared/openapi.json   # after API changes

# front ends (repo root)
pnpm install
pnpm --filter committee-web dev     # http://localhost:5173
pnpm --filter resident-pwa dev      # http://localhost:5174
pnpm -r lint && pnpm -r typecheck && pnpm -r test && pnpm -r build
pnpm --filter @societyiq/shared api:generate   # regenerate API types from openapi.json
```

If a command here is wrong, fix this section in the same PR.

## 7. Style

- Python: type hints everywhere, `ruff` for lint and format, small modules per domain (`billing`, `payments`, ...). Business logic in `services/`, not in route handlers.
- TypeScript: `strict` mode, no `any`, components small, data fetching through TanStack Query hooks in `api/`.
- Names in English. Comments explain *why*, not *what*.
- Indian number and date formats in the UI: `₹1,31,000`, `25 Sep 2026` (see `docs/03` §6).

## 8. When unsure

Ask the human in the chat, or add a question to `docs/10_OPEN_QUESTIONS.md` with an ID (`Q-<number>`), and continue with a safe, configurable placeholder. Never block silently and never guess silently.
