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
| M6 Payments, receipts, dues | IN REVIEW | feat/m6-payments (merged into `dev`) | Resident screens in M7 |
| M7 Resident PWA core | IN PROGRESS (feat/m7-resident) | | |
| M8 Complaints | IN REVIEW | feat/m8-complaints (merged into `dev`) | Phone camera upload not yet tried on a real phone |
| M9 Notices and email | NOT STARTED | | |
| M10 Committee home and compliance | IN REVIEW | feat/m10-compliance | Then M11 |
| M11 Analytics and admin tools | IN PROGRESS (feat/m11-admin) | | |
| M12 Vendor bills, AI, alerts | NOT STARTED | | |
| M13 Quote comparison | NOT STARTED | | |
| M14 Minutes drafting | NOT STARTED | | |

Statuses: NOT STARTED · IN PROGRESS (branch) · IN REVIEW (PR link) · DONE · BLOCKED (question ID)

## Log

Newest first. One entry per merged PR: date, milestone, what was built, how to try it, known gaps.

- 2026-10-24 — M10 — Committee home and compliance tracker.
  Calc (pure, 100% covered, in the CI coverage gate): `app/calc/compliance.py` — status per docs/06 §9 (Overdue before today, Due soon within 30 days, else OK), next due = date done + repeat months (same day, clamped to month end), reminder days 90/60/30/7/0 then weekly while overdue.
  Backend: migration `0005_compliance` (revision id `0005_compliance`, on top of `0006_payments`): `vendors`, `compliance_items`, `compliance_events` (history, append-only), `compliance_reminders` (new, see DECISIONS) with forced RLS. Endpoints: compliance items (list, add, get with history, change, mark done), vendors (list, add, change), committee home `GET /societies/{id}/home` (cards, next bill date, latest run, "What needs your attention"). Roles per docs/02 §2 (admin, treasurer, committee, consultant manage; auditor views). Audit rows for every vendor and item change and every "done". Scheduled job `POST /api/v1/internal/jobs/compliance-reminders` (token; idempotent; logs to `job_runs`) and a daily step in `.github/workflows/jobs.yml`. Seed adds the docs/02 §12 compliance items and vendors for all three societies (14 items; due dates relative to the seed day).
  Front end (committee): Home with six cards (collected this month and count, outstanding and flats with dues, payments waiting for confirmation, all from M6; open complaints (open + in progress) from M8; compliance due soon with overdue count; next bill date and last run status) and the attention list; Compliance list (status in words + icon), item page (details, mark done with confirmation, history, change), add/change form, Vendors. Five languages (non-English drafts).
  Acceptance: Shanti Sadan seed → Generator service Overdue (−5 days), Water tank cleaning Due soon (12 days), checked by test and on the live API; marking done on D with 3-month repeat → next due D + 3 months (test).
  Tests: backend 221 (12 new M10 incl. acceptance, roles, vendor isolation, job idempotency; 9 new routes in the isolation list), front end 96 (2 new: home and compliance with axe).
  How to try: `uv run alembic upgrade head`, `uv run python -m app.seed`, sign in as `demo-admin@example.com`, Home; Detailed view → Compliance.
  Known gaps: reminders are recorded but not emailed until M9; no attached document per item (Q-041); statutory audit intervals not seeded (Q-040); `App.test.tsx` shell tests now render `/preview` because `/` needs the API; not checked in a real browser (no Playwright on this machine) — component tests with axe only.

- 2026-10-24 — M6 — Payments, receipts and dues.
  Calc: `app/calc/payments.py` (oldest-first allocation, dues buckets per docs/06 §6, opening-balance months, amount in words in the Indian system; 100% covered).
  Backend: migration `0006_payments` (`payments`, `payment_allocations` with `reversed_at`, `receipts`; `ledger_entries.months_pending`). Record cash/cheque/UPI/NEFT (cash and seen transfers can be confirmed in one tap; cheques only when cleared), confirm (payment ledger entry, receipt `R/2026-27/000001`, allocation, audit, one transaction), cheque bounced, reverse with reason (reversal row and ledger entry, allocations undone, receipt cancelled). Allocation is a reconciliation step after any confirm, reversal or new bill, so advances settle the next bill. Dues with buckets and suggested steps; flat ledger with running balance; statement export as PDF and Excel with the resolutions behind the charges. Residents report "I have paid" for their own flat (tenants only if `tenant_can_pay`). Receipt PDF with amount in words. Optional "Opening balance months pending" import column; the seed sets months from docs/02 §12. Interest now runs only on unpaid charges.
  Front end (committee): Payments (waiting for you / all), record a payment (amount pre-filled with what the flat owes), payment page (confirm / cleared / bounced / reverse, what it paid, receipt), Dues (totals, bucket filters, suggested step), flat account statement with exports.
  Acceptance: docs/06 §4 example end to end (₹10,000 → two bills paid, third ₹1,600, ₹19,400 left); no receipt for an unconfirmed payment; reversal restores ₹29,400 exactly; audit rows for record, confirm, bounce, reverse.
  Known gaps: no bounce charge (Q-004); no bank matching (v1.5); reminders are M9's notices; resident screens in M7.

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
