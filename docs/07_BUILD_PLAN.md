# 07 — Build plan

Build in this order. Each milestone is small enough for one or two Claude Code sessions. Do not start a milestone until the previous one's acceptance checks pass, except where "can run in parallel" is noted. Mark progress in `PROGRESS.md`.

No dates: we go at a steady pace and finish each step properly.

---

## M0 — Repository and tooling

Tasks:
1. Create the monorepo layout from `04_ARCHITECTURE.md` §2 with empty `backend/`, `apps/committee-web/`, `apps/resident-pwa/`, `packages/shared/`.
2. Backend: `uv init`, FastAPI, ruff, pytest, pydantic-settings; `GET /api/v1/health` returns `{ "status": "ok" }`.
3. Front end: pnpm workspace; Vite + React + TypeScript + Tailwind in both apps; shared package builds.
4. `.env.example` files listing every variable (no values). `.gitignore` covers `.env*`, `node_modules`, `.venv`, `dist`, build output, `reference/videos/`.
5. CI workflow: lint, type-check, tests, build on every pull request.

Acceptance: `uv run pytest` passes; `pnpm -r build` passes; CI green on a test PR; README explains how to run both.

## M1 — Design system and app shells (can run in parallel with M2)

Tasks:
1. Tailwind theme from `03_DESIGN_SYSTEM.md` §3–4 (colours, Noto fonts, sizes); text-size setting via a root CSS variable.
2. Shared components from `03` §5 with tests and a simple preview page.
3. i18n setup: react-i18next, five languages, English complete, others as drafts with `_status: "draft"`.
4. Committee shell: top bar (logo, society name, language, help, account), left menu (Simple mode shows 5 items), home placeholder.
5. Resident PWA shell: dues banner placeholder and three big buttons; manifest and service worker; installable.

Acceptance: both apps run; language switch changes all visible text; Extra large text does not break layout at 360 px width; axe check has no serious issues; PWA installs on Android Chrome.

## M2 — Database base, auth and society isolation

Tasks:
1. Supabase projects for `local`/`demo`; Alembic configured; `app_backend` role without BYPASSRLS (`04` §6).
2. Tables: `users`, `societies`, `society_memberships`, `wings`, `audit_log`, `consents`, `legal_parameters` (seeded from `08` §3).
3. JWT verification, `current_user`, `require_role`, `SET LOCAL` tenant context per request.
4. RLS policies on every society table; the two-society isolation test fixture.
5. Endpoints: create society (3-step), invite member, accept invite, list my societies, update my preferences (language, text size, simple mode).
6. Consent screen on first sign-in; record in `consents`.
7. Front ends: sign-in (email + password and email code), society picker, society setup wizard, invite screen.

Acceptance: a user of Society A gets 404 on every Society B route; a raw SQL test proves RLS blocks cross-society reads; audit log rows written for society create and invites.

## M3 — Flats, members and Excel import

Tasks:
1. Tables: `flats`, `members`, `attachments`, `import_jobs` (fields per `05`).
2. CRUD screens for wings (with "has lift"), flats and members; flat page shows members.
3. Excel template download; upload → preview with row statuses in plain words → confirm import.
4. Opening balances: import creates `ledger_entries` of type `opening_balance` (needs the `ledger_entries` table, create it here).
5. Demo seed command loading the three fictional societies from `02` §12.

Acceptance: importing the template with 3 deliberately wrong rows shows exactly those 3 errors; confirming imports the rest; ledger balances equal the opening balances; seed command is idempotent.

## M4 — Charge setup and the calculation engine

Tasks:
1. Pure functions in `app/calc/charges.py` for every apportionment method in `06` §2, including the remainder-paise rule.
2. Unit tests: every worked example in `06` §2–3, plus edge cases (missing carpet area, wing without lift, let-out flat, rounding).
3. Validation against `legal_parameters`: block interest > 12%, block non-occupancy other than 10% of service charges, warn on fund minimums, warn on method deviation.
4. Tables: `charge_heads`, `flat_charge_overrides`, `parking_allotments`, `property_tax_assessments`.
5. Charge setup wizard: statutory heads pre-listed with their methods; committee enters GB-approved totals or rates and the resolution date; preview of every flat's monthly amount before saving.
6. Property tax entry: per-flat amounts and exemptions, with Excel import.

Acceptance: `app/calc` coverage 100%; preview screen shows per-flat totals matching hand calculations for the seed society; blocked values show the rule reference in plain words.

## M5 — Billing runs, bills and PDFs

Tasks:
1. Tables: `billing_runs`, `bills`, `bill_lines`, `number_sequences`.
2. Service: create draft run (period, flats, warnings), approve (numbers, ledger entries, PDFs) in one transaction; cancel a bill with reason (reversal) and reissue.
3. Bill PDF (WeasyPrint, Noto fonts, bilingual labels, UPI QR) and "Print all bills" single PDF.
4. Committee screens: billing run list, draft review, approve with confirmation, bill view and download.
5. Scheduled job endpoint `create_draft_billing_runs` and the GitHub Actions workflow calling it.

Acceptance: approving a run for Shanti Sadan creates one bill per flat with gap-free numbers; ledger balance of B-207 equals the expected total; PDFs render Marathi and Gujarati text correctly (visual check recorded in PR); running the job twice does not create two drafts.

## M6 — Payments, receipts and dues

Tasks:
1. Tables: `payments`, `payment_allocations`, `receipts`.
2. Record cash, cheque, UPI/NEFT; statuses per `02` §6; confirm; cheque cleared or bounced; reversal with reason.
3. Allocation oldest-first; receipt number and PDF on confirmation.
4. Dues screen with buckets and suggested steps (`06` §6); flat ledger with running balance; ledger export (PDF and Excel) for recovery.
5. Resident "I have paid" report creates a `pending` payment for the treasurer to confirm.

Acceptance: the worked example in `06` §4 passes as an end-to-end API test; no receipt exists for any unconfirmed payment; reversal restores the balance exactly; every money action has an audit row.

## M7 — Resident PWA core

Tasks:
1. Resident sign-in and flat linking (owner, tenant with `tenant_can_pay`, delegate).
2. Home: dues banner, Pay, Notices, Report a problem.
3. Pay screen: amount, UPI QR, "Open UPI app" deep link, "I have paid" form.
4. My bills, my receipts (download PDFs).
5. Offline reading of last loaded dues, bills and notices.

Acceptance: a 360 px phone can complete "see dues → pay instructions → report payment" in under a minute in a hallway test; a tenant without `tenant_can_pay` sees no Pay button.

## M8 — Complaints

Tasks: tables `complaints`, `complaint_updates`; raise from PWA with category icons and optional photo; raise on behalf from committee; status flow; resident sees updates and marks fixed or not fixed.

Acceptance: photo upload works from a phone camera; residents see only their own complaints; committee list filters by status.

## M9 — Notices and email notifications

Tasks: tables `notices`, `notice_reads`, `notification_log`; draft, translate, publish; email sending through the chosen provider; read counts; optional AI "Help me write" behind the provider interface with `FakeProvider` in tests; WhatsApp shown as "Coming soon".

Acceptance: publishing sends one email per member with an email address and logs each; AI-drafted text is never published without a person pressing Publish.

## M10 — Committee home and compliance tracker

Tasks: home cards from `02` §10; tables `vendors`, `compliance_items`, `compliance_events`; status rules and reminders per `06` §9; reminder job.

Acceptance: seed society shows the generator service as Overdue and the tank cleaning as Due soon; marking done moves the next due date correctly.

**After M10:** the core is complete. Run an internal demo, then a dry run with one friendly society's real (anonymised) data, before any pilot.

## M11 — Usage analytics and admin tools

PostHog with masking (`04` §10); audit log viewer for admins; data export (all society data as Excel and PDF); monthly restore test procedure documented.

## M12 — Vendor bills with AI reading and spending alerts

Tables `expense_bills`, `extracted_fields`, `ai_runs`, `alerts`; upload, AI extraction with confidence, review screen, bill checks, spending alerts per `06` §8 with all worked examples as tests.

## M13 — Quote comparison

Per `02` §15 and `06` §10.

## M14 — Meeting minutes drafting

Per `02` §16.

## Later (needs a decision before starting)

Payment gateway per society; bank statement matching; WhatsApp; SMS OTP; registers and nominations; tenant register and rent tracker; facility booking; record search; consultant multi-society console; monthly report; health score; gate module.
