# PROGRESS

What is built, what is in progress, and what is next. Every Claude Code session updates this file in the same pull request as its work.

## Status

| Milestone | Status | Branch / PR | Notes |
|---|---|---|---|
| M0 Repository and tooling | IN REVIEW | feat/m0-scaffold (not yet committed or pushed) | CI not yet run on GitHub |
| M1 Design system and app shells | IN REVIEW | feat/m0-scaffold (shipped together with M0) | Axe check and Android PWA install not yet verified |
| M2 Database base, auth, isolation | IN REVIEW | feat/m2-auth-isolation (merged into `dev` locally) | Needs a Supabase project for real sign-in; CI not yet run |
| M3 Flats, members, import | IN REVIEW | feat/m3-flats-members (merged into `dev` locally) | Supabase Storage path untested |
| M4 Charge setup and calculation engine | IN REVIEW | feat/m4-charges (merged into `dev` locally) | Legal values unverified until the consultant checks them |
| M5 Billing runs, bills, PDFs | IN REVIEW | feat/m5-billing (merged into `dev` locally) | Email to residents is M9 |
| M6 Payments, receipts, dues | IN PROGRESS (feat/m6-payments) | | Then M7 |
| M7 Resident PWA core | NOT STARTED | | |
| M8 Complaints | IN REVIEW | feat/m8-complaints (merged into `dev`) | Phone camera upload not yet tried on a real phone |
| M9 Notices and email | NOT STARTED | | |
| M10 Committee home and compliance | IN PROGRESS (feat/m10-compliance) | | Then M11 in the same session |
| M11 Analytics and admin tools | NOT STARTED | | |
| M12 Vendor bills, AI, alerts | NOT STARTED | | |
| M13 Quote comparison | NOT STARTED | | |
| M14 Minutes drafting | NOT STARTED | | |

Statuses: NOT STARTED · IN PROGRESS (branch) · IN REVIEW (PR link) · DONE · BLOCKED (question ID)

## Log

Newest first. One entry per merged PR: date, milestone, what was built, how to try it, known gaps.

- 2026-10-24 — M8 — Complaints.
  Backend: migration `0005_complaints` (`complaints`, append-only `complaint_updates`, forced RLS). Endpoints under `/societies/{id}/complaints`: list (filter `?status=`), raise, detail, post an update (optionally change status, optionally committee-only), assign to a person or vendor, resident feedback (Fixed / Not fixed, only after Resolved), add photo (JPEG/PNG/WebP checked by content, max 3), get photo. Admin, treasurer and committee manage; owners, tenants and delegates raise and see their flat's complaints (others' are 404); consultant and auditor get 403. Committee raising for a flat is recorded as "on behalf". Create, assign, status and feedback write `audit_log`.
  Front end: shared `packages/shared/src/complaints` (hooks, category icons, status pill, raise form with photo shrink, photo viewer, history). Committee: Complaints list (Open first, filter by status), raise for a flat, complaint page (assign, update with status change, committee-only notes). Resident: Report a problem (category icons, my flat / common area, photo from camera or gallery, optional text, one Send), My complaints, complaint page with Fixed / Not fixed. Five languages (non-English drafts).
  Acceptance: photo upload tested by API and UI test (real phone camera not yet tried); residents see only their own (test); committee list filters by status (API and UI tests).
  Tests: backend 152 (7 new complaint tests + 8 isolation-checked routes), front end: 4 new.
  How to try: sign in to the committee app as `demo-admin@example.com` → Complaints; resident app as `resident.b207@example.com` → Report a problem.
  Known gaps: residents linked to several flats cannot pick one in the PWA yet (API asks for `flat_id`; flat picker comes with M7 flat linking); no demo complaints in the seed (docs/02 §12 lists none); Q-080 and Q-081 use placeholders; complaint emails/notifications wait for M9.

- 2026-10-24 — M5 — Billing runs, bills and PDFs.
  Calc: `app/calc/bills.py` (arrears, advance, total due per docs/06 §3; simple interest per §5 from the later of due date + grace and the last run's bill date, so never charged twice; 100% covered).
  Backend: migration `0004` (`billing_runs`, `bills`, `bill_lines`, `number_sequences`, `job_runs`, scheduler read policy). Draft run freezes every flat's lines; approve re-checks the setup, reserves a gap-free block of numbers (`B/2026-27/000001`) under a row lock, writes bills, lines, `bill` and `interest` ledger entries and audit rows in one transaction (batched: ~1.7 s for 64 flats locally). Cancel a bill with a reason (reversal entries), reissue a corrected bill (`replaces_bill_id`). Bill PDF and "print all" PDF: Jinja2 + WeasyPrint, Noto fonts bundled, English plus the society's language, UPI QR (`upi://pay?...&am=29400.00`); rendered on first request and stored; 503 `PDF_UNAVAILABLE` where Pango is missing. Scheduled job `POST /api/v1/internal/jobs/create-draft-billing-runs` (token; idempotent; auto-approves when the setup is unchanged and the society turned it on) and `.github/workflows/jobs.yml` (daily 06:00 IST). Backend `Dockerfile` with Pango for hosting.
  Front end (committee): Bills (create bills for a month), run page (warnings, every flat's amount, approve with confirmation, cancel draft, print all), bill page (lines, arrears, advance, interest, PDF, cancel with reason, issue corrected bill), bills list on each flat page. Five languages.
  Acceptance: Shanti Sadan run → 120 bills numbered B/2026-27/000001–000120 in flat order; B-207 arrears ₹29,400 + ₹4,200 = ₹33,600 and ledger balance ₹33,600 (test and live); job run twice → one draft. Visual check: Marathi, Gujarati and Tamil bills rendered in the Linux image (`docker build -t societyiq-backend backend`), conjuncts shaped correctly (screenshots checked in this session).
  Tests: backend 144, front end 90.
  Known gaps: bills are not emailed yet (M9); PDFs cannot be made on Windows without Pango (use the Docker image or Linux); interest start date follows a placeholder rule (Q-002); quarterly runs start only in a quarter month of the financial year (Q-007); paid bills cannot be cancelled until payments exist (M6).

- 2026-10-24 — M4 — Charge setup and the calculation engine.
  Calc (pure, 100% covered, enforced in CI): `app/calc/charges.py` implements every apportionment method of docs/06 §2 with the remainder-paise rule in flat-number order, overrides, one-time heads, monthly and quarterly periods, bill rounding; flats missing an input a head needs are left out of the run with the reason, never billed a silent zero. `app/calc/legal.py`: statutory method per head; blocks interest above the cap, non-occupancy other than the fixed percent / base / let-out; warns below fund minimums and on method deviation (reason, and GB resolution for deviation, required). All limits come from `legal_parameters`, with the source shown in messages. Tests cover both worked examples (₹4,545 and the seed ₹4,200 / ₹4,540).
  Backend: migration `0003` (`charge_heads`, `flat_charge_overrides`, `parking_allotments`, append-only `property_tax_assessments`; import jobs gain `property_tax`). Endpoints for society billing and interest settings (admin), charge heads, standard heads with today's legal percents, per-flat overrides / parking / property tax, property tax Excel import (template, preview, confirm), and the per-flat preview for a period with missing-data counts. Seed now adds the docs/02 §12 charge setup.
  Front end (committee): Charges list, add/change charge starting from the statutory head (legal percent from the API, problems shown with their rule), preview table per flat with left-out flats and missing data, billing and interest settings, property tax import, and on each flat page: parking, property tax and special amounts.
  Tests: backend 122 (incl. 34 isolation-checked society routes), front end 89.
  How to try: run the seed again (`uv run python -m app.seed`), sign in as `demo-admin@example.com`, Detailed view → Charges → "See what each flat pays".
  Known gaps: legal values are unverified (docs/08 §3); common-area property tax by carpet area is entered as a separate per-carpet-area head; education fund collected monthly (annual collection setting not built); welfare fund opt-in is via a per-flat special amount; Q-003 (vacant flats) defaults to no non-occupancy charge.

- 2026-10-24 — M3 — Flats, members, Excel import, demo seed.
  Backend: migration `0002` adds `flats`, `members`, `attachments`, `import_jobs`, `ledger_entries` (append-only, one opening balance per flat) with forced RLS, and the FK from memberships to flats. CRUD for wings (with lift), flats and members (no deletes; "moved out" sets `to_date`); flat list and detail show the main member and ledger balance. Import: template download (`.xlsx` with dropdowns and a "How to fill" sheet), upload → per-row OK / warning / error with i18n keys ("Row 14: owner phone has 9 digits"), confirm re-checks and imports OK + warning rows in one transaction, opening balances become `opening_balance` ledger entries sourced to the import. Money parsed to paise without floats (Indian commas, ₹, Excel float noise). File storage: local folder or Supabase Storage (`STORAGE_BACKEND`). Owners, tenants and delegates can now be invited for a flat; their links open the resident app. Seed: `uv run python -m app.seed` loads the three fictional societies (226 flats, listed dues as opening balances, A-305 let out) plus demo logins `demo-admin@example.com` (admin of all three) and `resident.b207@example.com` (owner of B-207); running it again adds nothing.
  Tests: backend 77 (30 pure import-row tests incl. money parsing; acceptance test with 3 wrong rows → exactly 3 errors, confirm imports the rest, ledger = opening balances; seed idempotent; isolation now covers all 17 society routes plus B's ids under A's path; guard that every table with `society_id` has forced RLS). Front end 86, incl. an import-preview screen test with axe.
  Front end (committee): Flats and members (grouped by wing, search, balances), flat page (details, edit, people, add person, mark moved out), add flat, wings and lifts, 3-step Excel import with preview and confirm; people page can invite residents to a flat. All text in 5 languages (non-English drafts).
  How to try: docs/09 §6a, then `uv run python -m app.seed`, sign in at http://localhost:5173 as `demo-admin@example.com`, choose Shanti Sadan CHS, open Flats and members (Detailed view in Account).
  Known gaps: Supabase Storage upload untested (no project yet); seeded flats have no carpet area (docs/02 §12 gives none); resident app does not show flat data yet (M7); no Playwright end-to-end test yet.

- 2026-10-24 — M2 — Database base, sign-in and society isolation.
  Backend: Alembic set up; migration `0001` creates `users`, `societies`, `wings`, `society_memberships`, `audit_log`, `consents`, `legal_parameters` (seeded from docs/08 §3, unverified), the `app_backend` role (no BYPASSRLS, no DELETE, audit log insert-only) and forced RLS on every table with user or society data. Supabase JWT check (HS256 secret or JWKS), per-request transaction with `set_config(..., true)` tenant context, `require_role` (404 for non-members, 403 for wrong role), error format `{error: {code, message_key}}`. Endpoints: `GET /me`, `PATCH /me/preferences`, `GET/POST /me/consents`, `GET /me/societies`, `POST /societies` (3 steps in one call; creator becomes admin; default wing), `GET /societies/{id}`, `GET /societies/{id}/memberships`, `POST /societies/{id}/invites`, `POST /societies/{id}/invites/accept`. Audit rows for society create, membership create, invite, accept and preference changes. Local-only `POST /dev/token`.
  Tests: 33 backend tests against real PostgreSQL, including the two-society fixture, "user of A gets 404 on every B route" (a guard test fails if a new society route is not listed), raw-SQL RLS tests (no cross-society reads, writes or updates; no deletes; audit log append-only; legal parameters read-only).
  Front end: shared `AuthProvider` (Supabase email code and password; local dev sign-in), `AppGate` (sign-in → consent → invite → society picker), TanStack Query hooks, generated API types, `SelectField`. Committee: setup wizard (3 steps, invite links shown once), People and invites page under Society settings (admin only), account menu with sign out and change society. Resident: email-code sign-in, consent, sign out. Language, text size and Simple view now saved to the user's profile. All new text in 5 languages (non-English drafts).
  How to try: docs/09 §6a (Docker Postgres + `VITE_DEV_SIGN_IN=true`), then open http://localhost:5173, sign in as any `@example.com` email, accept consent, set up a society.
  Known gaps: no Supabase project yet, so real email-code and password sign-in is untested; invite emails wait for M9 (links are copied by hand); owner/tenant invites wait for flats (M3); terms and privacy texts not written (Q-034); open questions Q-030 to Q-034 use placeholders; Playwright end-to-end tests not added yet; Android install and full axe audit of M1 still open; bundle-size warning from supabase-js.

- 2026-10-23 — M1 — Built in the same session as M0 and committed on `feat/m0-scaffold`: shared UI components (Button, Card, Dialog, Field, MoneyText, Small, StatusPill, Toast), Indian money/date utils, contrast util, i18n in en/mr/hi/gu/ta, committee shell with nav and preview page, resident PWA with install banner and service worker.
  Known gaps: axe check and Android Chrome install not yet verified; non-English strings are drafts.

- 2026-10-23 — M0 — Monorepo per docs/04 §2. Backend: uv project (Python 3.12), FastAPI with `GET /api/v1/health`, pydantic-settings, ruff, pytest; docstring-only stubs for every domain in docs/04 §3 (router, service, schema) and for calc, ai, pdf, notify, jobs, i18n, seed, models, db, auth, deps; no domain router mounted. Front end: pnpm workspace, `committee-web` and `resident-pwa` (Vite 8, React 18, TypeScript 5.9 strict, Tailwind 4) showing the logo and "Coming soon"; `packages/shared` with English strings. `.env.example` for backend and both apps; CI in `.github/workflows/ci.yml`.
  How to try: README "How to run".
  Known gaps: CI not yet run on GitHub (acceptance check open); no `alembic.ini` (comes with M2); only English strings (i18n in M1); GitHub Action versions (`checkout@v4` etc.) not checked against latest; Starlette warns that `httpx` with TestClient is deprecated.

- 2026-10-23 — Docs pack created (CLAUDE.md and docs/). No code yet.

## Restore tests

Record each monthly backup restore test here: date, who, result.
