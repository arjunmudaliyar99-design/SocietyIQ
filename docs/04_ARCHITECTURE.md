# 04 — Architecture

How the system is put together. Keep it simple: one backend, one database, two front ends. No microservices, no message queues in v1.

Items marked **(verify)** depend on third-party products whose details change; check their current docs before relying on them.

---

## 1. Overview

```
 Committee web (React, Vite)      Resident PWA (React, Vite, installable)
            \                              /
             \        HTTPS, JSON         /
              ------>  FastAPI backend <--
                         |   |   |
        PostgreSQL 16 ---+   |   +--- AI provider (Groq or Gemini) for reading and drafting only
        (Supabase,           |
         row-level security) +--- Supabase Storage (private bucket: bills, photos, PDFs)
                             +--- Email provider (notifications)
                             +--- PostHog (usage analytics, masked)
 Scheduled jobs (GitHub Actions cron) --> protected /internal/jobs endpoints
```

## 2. Repository layout (monorepo)

```
societyiq/
  CLAUDE.md
  README.md
  .gitignore
  .github/workflows/        ci.yml, jobs.yml
  docs/                     all specs (this folder)
  reference/                brand, old decks, old prototype (read-only reference)
  backend/
    pyproject.toml
    alembic.ini
    alembic/versions/
    app/
      main.py               FastAPI app, routers, CORS
      config.py             settings from environment (pydantic-settings)
      db.py                 async engine, session, tenant context
      auth.py               verify Supabase JWT, load user and memberships
      deps.py               dependencies: current_user, current_society, require_role
      models/               SQLAlchemy models, one file per domain
      schemas/              Pydantic request/response models
      routers/              thin HTTP handlers, one file per domain
      services/             business logic (billing, payments, dues, ...)
      calc/                 pure functions for money and alerts (no DB, fully unit-tested)
      ai/                   provider interface, prompts, JSON schemas
      pdf/                  HTML templates + WeasyPrint rendering
      notify/               email (and later SMS, WhatsApp) senders
      jobs/                 scheduled tasks (billing runs, reminders)
      i18n/                 backend message files
      seed/                 demo seed data (fictional, from 02 §12)
    tests/
  apps/
    committee-web/          React app for the committee
    resident-pwa/           React PWA for residents
  packages/
    shared/
      ui/                   components from 03 §5
      i18n/                 translation JSON files (en, mr, hi, gu, ta)
      api/                  typed API client generated from FastAPI OpenAPI
      utils/                money and date formatting
  pnpm-workspace.yaml
  package.json
```

## 3. Backend

- **FastAPI** with routers per domain: `auth`, `societies`, `flats`, `members`, `imports`, `charges`, `billing`, `bills`, `payments`, `receipts`, `dues`, `complaints`, `notices`, `compliance`, `documents`, `expenses`, `audit`, `exports`, `internal_jobs`.
- **Layers:** router (HTTP only) → service (rules, transactions) → models. Pure calculations live in `app/calc/` and never touch the database.
- **API style:** REST, JSON, `/api/v1/...`. Every society-scoped route includes the society: `/api/v1/societies/{society_id}/bills`. Errors: `{ "error": { "code": "BILL_ALREADY_SENT", "message_key": "errors.billAlreadySent" } }` so the front end can translate.
- **OpenAPI:** generate the TypeScript client into `packages/shared/api` (e.g. `openapi-typescript`). Regenerate after API changes.
- **Validation:** Pydantic v2 models; money fields are integers in paise in the API.
- **Transactions:** every money operation (approve billing run, record payment, reverse) runs in one database transaction and writes its ledger entries and audit log in the same transaction.

## 4. Database

PostgreSQL 16 on **Supabase**, region **Mumbai (ap-south-1)** (verify available regions when creating the project). Schema in `05_DATABASE.md`.

- ORM: SQLAlchemy 2 async with `asyncpg`.
- Migrations: Alembic only. Migrations run with the database owner role; the app runs with a restricted role (§6).
- Supabase connection pooler in **transaction mode** works with `SET LOCAL`, but asyncpg prepared statements must be disabled for it (`statement_cache_size=0`) (verify against current Supabase docs).
- We use Supabase as plain PostgreSQL plus Auth plus Storage. No business logic in Supabase functions, so we can move to any PostgreSQL host later.

## 5. Authentication

- **Supabase Auth** handles sign-in (email + password, email one-time code; phone OTP later with a paid SMS provider).
- The front end signs in with the Supabase JS client and sends the access token as `Authorization: Bearer <jwt>` to FastAPI.
- FastAPI verifies the JWT signature (using the project's JWKS endpoint or JWT secret, whichever the project uses; verify current Supabase docs), reads `sub` as the user id, then loads the user's `society_memberships`.
- Authorisation is ours, not Supabase's: `require_role(society_id, roles=[...])` dependency on every society route.

## 6. Society data isolation (critical)

Two independent layers. Both are required.

1. **API layer:** every society route checks membership and role, and every query filters by `society_id`.
2. **Database layer, row-level security (RLS):**
   - The backend connects as a dedicated role `app_backend` that is **not** the table owner and does **not** have `BYPASSRLS`.
   - At the start of each request's transaction the backend runs `SET LOCAL app.current_society_id = '<uuid>'` and `SET LOCAL app.current_user_id = '<uuid>'`.
   - Every society table has RLS enabled with a policy like:
     ```sql
     ALTER TABLE bills ENABLE ROW LEVEL SECURITY;
     ALTER TABLE bills FORCE ROW LEVEL SECURITY;
     CREATE POLICY society_isolation ON bills
       USING (society_id = current_setting('app.current_society_id', true)::uuid)
       WITH CHECK (society_id = current_setting('app.current_society_id', true)::uuid);
     ```
   - Requests not tied to a society (sign-in, society picker) use a narrow set of tables with their own policies.
3. **Tests:** a shared test fixture creates two societies; every endpoint test also asserts that a user of Society A gets 404 for Society B's records, and a raw SQL test asserts RLS blocks cross-society reads even without the API filter.

Never expose the Supabase service-role key to front ends. Front ends never query tables directly; they only call FastAPI.

## 7. File storage

- Supabase Storage, one **private** bucket `society-files`, paths `/{society_id}/{kind}/{yyyy}/{mm}/{uuid}.{ext}`.
- Uploads go through FastAPI (validate type and size, compute SHA-256 to catch duplicates), then to Storage.
- Downloads: FastAPI checks permission, then returns a short-lived signed URL (e.g. 5 minutes).
- Allowed: PDF, JPG, PNG, HEIC (convert to JPG), XLSX for imports. Max 10 MB.

## 8. PDFs (bills, receipts, printed bill packs)

- HTML templates (Jinja2) rendered to PDF with **WeasyPrint**, which shapes Devanagari, Gujarati and Tamil text correctly with Noto fonts (ReportLab does not shape Indic scripts well).
- Fonts bundled in `backend/app/pdf/fonts/` (Noto Sans family, open licence).
- UPI QR: generated server-side with the `qrcode` library from a UPI payment link: `upi://pay?pa=<society UPI ID>&pn=<payee name>&am=<amount>&cu=INR&tn=<bill number>`. Amount in rupees with two decimals.
- PDFs are stored in Storage and linked to the bill or receipt; regenerate only on reissue.
- WeasyPrint needs system libraries (Pango); the backend Dockerfile must install them (verify on the host).

## 9. Hosting

**Demo and internal sharing (free tiers):**

| Part | Service | Notes (verify current limits) |
|---|---|---|
| Committee web, Resident PWA | Vercel (Hobby) | Free tier is for non-commercial use; fine for demos |
| FastAPI | Render (free web service, Docker) | Sleeps when idle, first request slow; Singapore is the nearest region |
| Database, Auth, Storage | Supabase (free) | Free projects pause after inactivity |
| Jobs | GitHub Actions scheduled workflow | Calls `/internal/jobs/*` with a secret token |

**Pilots and paying societies (low cost):**

| Part | Service | Approx. cost (verify) |
|---|---|---|
| Front ends | Cloudflare Pages (free, commercial use allowed) or Vercel Pro | ₹0 or about $20/month |
| FastAPI | Render paid instance (always on) | about $7/month |
| Database | Supabase Pro (daily backups, no pausing) | about $25/month |
| Domain | e.g. `societyiq.in` (check availability) | about ₹1,000/year |

Roughly ₹3,000 to ₹4,500 a month in total, in line with the earlier cost model. Revisit when there are more than 25 societies.

Environments: `local`, `demo`, `production`. Each has its own Supabase project and its own secrets. Never point the demo at production data.

## 10. Usage analytics

- **PostHog** (free tier), events and page views from both front ends; heatmaps and session recordings for admins only.
- Mask all inputs and any element showing money or personal data (`ph-no-capture` class or PostHog masking settings).
- Identify users by internal UUID only, never by phone or email.
- Disclosed in the privacy policy; residents can opt out in Settings.
- Disabled in `local`; configurable per environment.

## 11. AI service

- Interface in `app/ai/provider.py` with two methods: `extract(document, schema) -> dict` and `draft(prompt_name, inputs, language) -> str`.
- Implementations: `GroqProvider`, `GeminiProvider`, and `FakeProvider` for tests and demos without a key. Provider chosen by `AI_PROVIDER` env var.
- Before sending real society data to any provider, confirm its data terms do not allow training on inputs (DPDP). Record the decision in `DECISIONS.md`. Until then, use only demo data with free tiers.
- Every AI output is validated against a Pydantic schema; invalid output → mark the item "needs review", never crash, never guess.
- Cache results by file SHA-256 so a document is never read twice.
- AI is optional: every feature must work (manually) when no AI key is set.
- Prompts live in `app/ai/prompts/*.md`, versioned, with the guardrails in `06` §12.

## 12. Notifications

- v1: email only, through a transactional email provider (choose one with a free tier; record in `DECISIONS.md`). Templates per language.
- Every outgoing message is logged in `notification_log`.
- SMS and WhatsApp: interfaces stubbed, UI shows "Coming soon".

## 13. Scheduled jobs

- `create_draft_billing_runs`: daily; creates drafts for societies whose bill date is today.
- `send_due_reminders`: daily; queues reminder drafts per the ladder (sending still needs approval unless the society turned on auto-send).
- `compliance_reminders`: daily.
- Jobs are idempotent (safe to run twice) and log each run in `job_runs`.

## 14. Security checklist

- HTTPS everywhere. CORS limited to our front-end origins.
- Secrets only in environment variables; `.env` files never committed; `.env.example` lists names only.
- Rate-limit sign-in and upload endpoints.
- Validate every upload's type by content, not only extension.
- Audit log for every create, update, reversal of money and member data.
- Daily backups (Supabase Pro) plus a monthly restore test into a scratch project (record in `PROGRESS.md`).
- Dependencies pinned; Dependabot or similar alerts on.

## 15. Testing

- `app/calc/` (money rules): 100% unit-test coverage, including the worked examples in `06`.
- Services: tests against a real PostgreSQL (Docker or a test Supabase project), including RLS.
- API: tests for permissions and society isolation on every endpoint.
- Front end: component tests for shared UI; one end-to-end smoke test per main flow (Playwright) once flows exist.
- CI (`.github/workflows/ci.yml`): lint, type-check, tests, build on every pull request.

## 16. PWA specifics

- `vite-plugin-pwa`: manifest (name "SocietyIQ", icons from `reference/brand/mark.png`, theme colour `#2E6B5E`), service worker.
- Offline: cache the app shell and the last-loaded dues, bills and notices for reading; actions that change data require a connection and say so plainly.
- Install prompt: a simple banner "Add SocietyIQ to your home screen", shown once, with instructions for Android and iPhone.
