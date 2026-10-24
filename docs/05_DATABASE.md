# 05 — Database (PostgreSQL 16)

The schema for v1 and v1.5. Build tables only when their milestone needs them (`07_BUILD_PLAN.md`). Change this document in the same pull request as the migration.

## Conventions

- Primary keys: `id UUID DEFAULT gen_random_uuid()`.
- Every society-owned table has `society_id UUID NOT NULL REFERENCES societies(id)` and RLS (see `04` §6).
- Money: `BIGINT` in **paise**, column names end in `_paise`. Never `NUMERIC` or `FLOAT` for amounts.
- Rates and percentages: `NUMERIC(7,4)` (e.g. 18.0000 for 18%).
- Timestamps: `TIMESTAMPTZ`, stored in UTC; display in `Asia/Kolkata`.
- Dates without time (bill date, due date): `DATE`.
- Every table: `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `created_by UUID NULL` (user id). Mutable tables also `updated_at`.
- Soft rules: financial rows are never deleted or updated in amount; they are reversed by new rows.
- Enums: PostgreSQL `TEXT` with a `CHECK` constraint (easier to migrate than native enums).

---

## 1. People and access

**`users`** — one row per person who can sign in. `id` = Supabase Auth user id.
`id UUID PK`, `full_name TEXT`, `email TEXT UNIQUE NULL`, `phone_e164 TEXT UNIQUE NULL`, `preferred_language TEXT CHECK IN ('en','mr','hi','gu','ta') DEFAULT 'en'`, `text_size TEXT CHECK IN ('normal','large','xlarge') DEFAULT 'normal'`, `simple_mode BOOLEAN DEFAULT true`, `analytics_opt_out BOOLEAN DEFAULT false`, `created_at`, `updated_at`.

**`societies`**
`id`, `name TEXT NOT NULL`, `registration_number TEXT NULL`, `address_line TEXT`, `city TEXT`, `state TEXT DEFAULT 'Maharashtra'`, `pincode TEXT`, `financial_year_start_month SMALLINT DEFAULT 4`, `default_language TEXT DEFAULT 'en'`, `billing_frequency TEXT CHECK IN ('monthly','quarterly') DEFAULT 'monthly'`, `bill_day SMALLINT CHECK 1..28`, `due_days SMALLINT DEFAULT 15`, `upi_id TEXT NULL`, `upi_payee_name TEXT NULL`, `bank_name TEXT NULL`, `bank_account_last4 TEXT NULL`, `interest_enabled BOOLEAN DEFAULT false`, `interest_rate_annual_pct NUMERIC(7,4) NULL` (general body rate, max per `legal_parameters`, currently 12%), `interest_gb_resolution_date DATE NULL`, `interest_grace_days SMALLINT NULL`, `rounding_rule TEXT CHECK IN ('none','nearest_rupee') DEFAULT 'nearest_rupee'` (Q-006), `auto_approve_billing BOOLEAN DEFAULT false`, `plan TEXT DEFAULT 'pilot'`, `champion_name TEXT NULL`, `champion_phone_e164 TEXT NULL`, `created_at`, `updated_at`.

**`society_memberships`** — a user's role in a society.
`id`, `society_id`, `user_id`, `role TEXT CHECK IN ('admin','treasurer','committee','consultant','auditor','owner','tenant','delegate')`, `flat_id UUID NULL` (required for owner, tenant, delegate), `status TEXT CHECK IN ('invited','active','removed')`, `invited_name TEXT NULL` (name typed in the invite; kept as the display name because `users` rows are private to each person), `invited_email TEXT NULL`, `invited_phone_e164 TEXT NULL`, `invite_token_hash TEXT NULL`, `invite_expires_at TIMESTAMPTZ NULL`, `created_at`, `created_by`, `updated_at`. `user_id` is NULL until the invite is accepted. Unique `(society_id, user_id, role, flat_id)` for accepted rows. Invite tokens are stored only as a SHA-256 hash. `flat_id` gets its foreign key in M3 when `flats` exists.

## 2. Flats and members

**`wings`** — `id`, `society_id`, `name TEXT` (e.g. "A"), `has_lift BOOLEAN DEFAULT false` (lift charges are shared only among flats in wings with a lift). Create one default wing when a society has no wings.

**`flats`**
`id`, `society_id`, `wing_id`, `flat_number TEXT NOT NULL`, `carpet_area_sqft NUMERIC(9,2) NULL` (carpet area as per the registered agreement; used for insurance, lease rent, major repairs, common-area tax), `flat_type TEXT NULL` (e.g. 1RK, 1BHK, 2BHK; display only, never a billing basis unless a GB resolution says so), `usage TEXT CHECK IN ('residential','commercial') DEFAULT 'residential'`, `certified_construction_cost_paise BIGINT NULL` (architect-certified original cost, for sinking and repair funds), `water_points NUMERIC(6,2) NULL` (inlets/taps per sanctioned plan, Q-011), `municipal_property_account TEXT NULL`, `occupancy TEXT CHECK IN ('owner_occupied','family_occupied','let_out','vacant') DEFAULT 'owner_occupied'` (non-occupancy charges apply only to `let_out`; `family_occupied` = occupied by the member's family as defined in the bye-laws, no non-occupancy charge; whether `vacant` attracts it is Q-003), `is_active BOOLEAN DEFAULT true`, `created_at`, `updated_at`. Unique `(society_id, wing_id, flat_number)`.

**`members`** — people linked to a flat; may have no login.
`id`, `society_id`, `flat_id`, `full_name TEXT NOT NULL`, `phone_e164 TEXT NULL`, `email TEXT NULL`, `member_type TEXT CHECK IN ('owner','joint_owner','tenant','delegate')`, `is_primary BOOLEAN DEFAULT false`, `user_id UUID NULL`, `from_date DATE NULL`, `to_date DATE NULL`, `tenant_can_pay BOOLEAN DEFAULT false`, `created_at`, `updated_at`.

## 3. Charges and billing

**`charge_heads`**
`id`, `society_id`, `name TEXT`, `code TEXT`, `standard_code TEXT NULL` (one of the statutory heads in `06` §2: service, property_tax, water, lift, parking, non_occupancy, insurance, lease_rent, major_repair, sinking_fund, repair_fund, election_fund, education_fund, welfare_fund, other), `calc_type TEXT CHECK IN ('equal_per_flat','equal_per_flat_with_lift','per_carpet_area','per_water_point','as_assessed_per_flat','pct_of_head','pct_of_construction_cost','per_parking_allotment','per_member_fixed','fixed_per_flat','custom_per_flat','voluntary')`, `period_total_paise BIGINT NULL` (for methods that split a total), `fixed_amount_paise BIGINT NULL`, `percent NUMERIC(7,4) NULL`, `percent_of_head_id UUID NULL`, `applies_to TEXT CHECK IN ('all','let_out_only') DEFAULT 'all'`, `gb_resolution_ref TEXT NULL`, `gb_resolution_date DATE NULL`, `method_deviation_reason TEXT NULL`, `frequency TEXT CHECK IN ('every_bill','one_time')`, `one_time_period DATE NULL`, `sort_order SMALLINT`, `is_active BOOLEAN`, `approved_by UUID NULL`, `approved_at TIMESTAMPTZ NULL`, `created_at`, `updated_at`.

**`parking_allotments`** — `id`, `society_id`, `flat_id`, `slot_label TEXT`, `slot_type TEXT CHECK IN ('open','stilt','covered','podium','mechanical','other')`, `vehicle_type TEXT CHECK IN ('two_wheeler','four_wheeler','other')`, `vehicle_number TEXT NULL`, `monthly_rate_paise BIGINT` (general body rate), `from_date DATE`, `to_date DATE NULL`, `gb_resolution_ref TEXT NULL`. Parking is allotted, not owned (the draft Model Bye-laws 2026 say open and stilt parking cannot ordinarily be sold; treat as allotment only).

**`property_tax_assessments`** — `id`, `society_id`, `flat_id NULL` (NULL = common area), `authority TEXT` (e.g. 'MCGM', 'TMC'), `financial_year TEXT`, `annual_amount_paise BIGINT`, `is_exempt BOOLEAN DEFAULT false`, `exemption_reason TEXT NULL` (e.g. 'MCGM residential ≤500 sq ft carpet'), `source_document_id UUID NULL`, `entered_by`, `created_at`. Amounts are copied from the authority's bill or assessment; SocietyIQ never computes municipal tax itself.

**`legal_parameters`** — versioned legal limits used by validation. `id`, `code TEXT` ('interest_max_annual_pct', 'non_occupancy_pct_of_service', 'sinking_fund_min_annual_pct', 'repair_fund_min_annual_pct', 'education_fund_per_member_month_paise', 'committee_repair_limit_paise'), `value NUMERIC`, `applies_when JSONB NULL` (e.g. member-count band), `state TEXT DEFAULT 'Maharashtra'`, `effective_from DATE`, `effective_to DATE NULL`, `source TEXT` (e.g. 'MCS Rules 106C-12, notified 18-06-2026'), `verified_by TEXT NULL`, `verified_on DATE NULL`. Not society-scoped (global, read-only for `app_backend`). Seed values in `08_LEGAL_AND_COMPLIANCE.md` §3.

**`flat_charge_overrides`** — `id`, `society_id`, `flat_id`, `charge_head_id`, `amount_paise BIGINT`, `reason TEXT`, `valid_from DATE`, `valid_to DATE NULL`.

**`billing_runs`**
`id`, `society_id`, `period_start DATE`, `period_end DATE`, `bill_date DATE`, `due_date DATE`, `status TEXT CHECK IN ('draft','approved','sent','cancelled')`, `flat_count INT`, `total_paise BIGINT`, `warnings JSONB DEFAULT '[]'`, `charges_snapshot JSONB` (charge setup used, for audit), `approved_by UUID NULL`, `approved_at NULL`, `sent_at NULL`, `created_at`. Unique `(society_id, period_start)` where status <> 'cancelled'.

**`bills`**
`id`, `society_id`, `billing_run_id`, `flat_id`, `bill_number TEXT` (unique per society), `period_start`, `period_end`, `bill_date`, `due_date`, `charges_paise BIGINT`, `arrears_paise BIGINT`, `interest_paise BIGINT DEFAULT 0`, `total_due_paise BIGINT`, `status TEXT CHECK IN ('issued','partially_paid','paid','cancelled')`, `cancelled_reason TEXT NULL`, `replaces_bill_id UUID NULL`, `pdf_path TEXT NULL`, `language TEXT`, `created_at`.

**`bill_lines`** — `id`, `bill_id`, `society_id`, `charge_head_id NULL`, `description TEXT`, `amount_paise BIGINT`, `sort_order`.

**`number_sequences`** — gap-free numbering. `society_id`, `kind TEXT CHECK IN ('bill','receipt')`, `financial_year TEXT` (e.g. "2026-27"), `next_value INT`. Primary key `(society_id, kind, financial_year)`. Increment with `SELECT ... FOR UPDATE` inside the money transaction. Format: `B/2026-27/000123`, `R/2026-27/000045`.

## 4. Payments, receipts and the ledger

**`payments`**
`id`, `society_id`, `flat_id`, `amount_paise BIGINT CHECK > 0`, `method TEXT CHECK IN ('cash','cheque','upi','neft','gateway','other')`, `status TEXT CHECK IN ('pending','recorded','confirmed','bounced','reversed')`, `received_on DATE`, `reference TEXT NULL` (UPI ref, NEFT UTR, cheque number), `cheque_bank TEXT NULL`, `cheque_date DATE NULL`, `reported_by_resident BOOLEAN DEFAULT false`, `proof_file_path TEXT NULL`, `recorded_by UUID`, `resident_confirmed_at NULL`, `confirmed_by UUID NULL`, `confirmed_at NULL`, `reversal_of UUID NULL`, `reason TEXT NULL`, `notes TEXT NULL`, `created_at`.

**`payment_allocations`** — `id`, `society_id`, `payment_id`, `bill_id`, `amount_paise BIGINT`.

**`receipts`** — `id`, `society_id`, `payment_id UNIQUE`, `receipt_number TEXT`, `issued_at TIMESTAMPTZ`, `pdf_path TEXT NULL`, `cancelled_at NULL`, `cancelled_reason NULL`.

**`ledger_entries`** — the flat's account. Append-only. Positive = flat owes more; negative = flat paid or was credited.
`id`, `society_id`, `flat_id`, `entry_date DATE`, `entry_type TEXT CHECK IN ('opening_balance','bill','interest','payment','adjustment','reversal')`, `amount_paise BIGINT` (signed), `source_type TEXT` (e.g. 'bill','payment','import'), `source_id UUID`, `reverses_entry_id UUID NULL`, `reason TEXT NULL`, `created_by`, `created_at`.
Balance of a flat = `SUM(amount_paise)`. Never update or delete rows; add a `reversal` row.

## 5. Complaints and notices

**`complaints`**
`id`, `society_id`, `flat_id NULL`, `raised_by_user_id NULL`, `raised_on_behalf BOOLEAN DEFAULT false`, `category TEXT CHECK IN ('water','lift','electricity','cleaning','security','parking','other')`, `location TEXT CHECK IN ('my_flat','common_area')`, `description TEXT NULL`, `status TEXT CHECK IN ('open','in_progress','resolved','closed')`, `assigned_to_text TEXT NULL`, `resident_feedback TEXT CHECK IN ('fixed','not_fixed') NULL`, `created_at`, `updated_at`, `resolved_at NULL`, `closed_at NULL`.

**`complaint_updates`** — `id`, `society_id`, `complaint_id`, `author_user_id`, `message TEXT`, `new_status TEXT NULL`, `visible_to_resident BOOLEAN DEFAULT true`, `created_at`.

**`attachments`** — generic files linked to records. `id`, `society_id`, `owner_type TEXT` ('complaint','notice','payment','compliance_item','expense_bill'), `owner_id UUID`, `storage_path TEXT`, `mime TEXT`, `size_bytes INT`, `sha256 TEXT`, `original_filename TEXT`, `uploaded_by`, `created_at`.

**`notices`** — `id`, `society_id`, `title TEXT`, `body TEXT`, `language TEXT`, `translations JSONB DEFAULT '{}'` (lang → {title, body, status: 'draft'|'reviewed'}), `audience TEXT CHECK IN ('all','owners','tenants','wing')`, `audience_wing_id NULL`, `status TEXT CHECK IN ('draft','published','archived')`, `ai_assisted BOOLEAN DEFAULT false`, `published_at NULL`, `published_by NULL`, `created_by`, `created_at`, `updated_at`.

**`notice_reads`** — `notice_id`, `user_id`, `read_at`. PK `(notice_id, user_id)`.

## 6. Compliance [M10]

**`vendors`** — `id`, `society_id`, `name`, `category TEXT NULL`, `phone_e164 NULL`, `email NULL`, `gstin TEXT NULL`, `notes NULL`.

**`compliance_items`** — `id`, `society_id`, `item_type TEXT CHECK IN ('fire_audit','structural_audit','lift_amc','pump_amc','generator_service','tank_cleaning','cctv_amc','insurance','pest_control','other')`, `title TEXT`, `vendor_id NULL`, `last_done_on DATE NULL`, `next_due_on DATE NOT NULL`, `repeat_months SMALLINT NULL`, `contract_value_paise BIGINT NULL`, `notes NULL`, `is_active BOOLEAN`, `created_at`, `updated_at`.

**`compliance_events`** — `id`, `society_id`, `compliance_item_id`, `done_on DATE`, `notes`, `recorded_by`, `created_at`.

## 7. Vendor bills and AI extraction [M11–M12]

**`expense_bills`** — `id`, `society_id`, `attachment_id`, `vendor_id NULL`, `vendor_name_raw TEXT NULL`, `invoice_number TEXT NULL`, `invoice_date DATE NULL`, `due_date DATE NULL`, `billing_period_month DATE NULL` (first day of month), `category TEXT NULL` (list in `06` §7), `subtotal_paise BIGINT NULL`, `gst_paise BIGINT NULL`, `total_paise BIGINT NULL`, `description TEXT NULL`, `status TEXT CHECK IN ('processing','needs_review','confirmed','rejected')`, `check_warnings JSONB DEFAULT '[]'`, `confirmed_by NULL`, `confirmed_at NULL`, `created_at`, `updated_at`.

**`extracted_fields`** — keeps AI and human values apart so AI never overwrites a person. `id`, `society_id`, `expense_bill_id`, `field_name TEXT`, `ai_value TEXT NULL`, `ai_confidence TEXT CHECK IN ('high','review') NULL`, `user_value TEXT NULL`, `user_confirmed BOOLEAN DEFAULT false`, `updated_at`. Re-running AI may change `ai_value` only where `user_confirmed = false`.

**`ai_runs`** — `id`, `society_id`, `purpose TEXT`, `provider TEXT`, `model TEXT`, `input_sha256 TEXT`, `prompt_version TEXT`, `status TEXT`, `output JSONB NULL`, `error TEXT NULL`, `created_at`. Used for caching and debugging.

**`alerts`** — `id`, `society_id`, `alert_type TEXT`, `severity TEXT CHECK IN ('info','attention','urgent')`, `title_key TEXT`, `data JSONB`, `status TEXT CHECK IN ('open','dismissed','resolved')`, `created_at`, `resolved_at NULL`.

## 8. System tables

**`audit_log`** — append-only. `id BIGSERIAL`, `society_id NULL`, `actor_user_id NULL`, `action TEXT` (e.g. 'payment.confirm'), `entity_type TEXT`, `entity_id UUID`, `before JSONB NULL`, `after JSONB NULL`, `reason TEXT NULL`, `ip INET NULL`, `created_at`. No UPDATE or DELETE grants for `app_backend`.

**`import_jobs`** — `id`, `society_id`, `kind TEXT` ('flats_members'), `attachment_id`, `status TEXT CHECK IN ('uploaded','previewed','imported','failed')`, `row_count INT`, `ok_count INT`, `error_count INT`, `preview JSONB`, `created_by`, `created_at`.

**`notification_log`** — `id`, `society_id`, `channel TEXT CHECK IN ('email','sms','whatsapp','in_app')`, `template TEXT`, `language TEXT`, `to_member_id NULL`, `to_address_masked TEXT`, `status TEXT`, `provider_message_id NULL`, `error NULL`, `created_at`.

**`consents`** — DPDP consent records. `id`, `user_id`, `society_id NULL`, `purpose TEXT` ('terms','privacy','analytics','notifications'), `policy_version TEXT`, `granted_at`, `withdrawn_at NULL`.

**`job_runs`** — `id`, `job_name`, `started_at`, `finished_at`, `status`, `details JSONB`.

## 9. Indexes (minimum)

- `(society_id, flat_id)` on bills, payments, ledger_entries, complaints.
- `(society_id, status)` on bills, payments, complaints, expense_bills.
- `(society_id, next_due_on)` on compliance_items.
- `(society_id, sha256)` on attachments.
- `(society_id, invoice_number, vendor_id)` on expense_bills (duplicate check).

## 10. RLS policy list

Enable and force RLS with the `society_isolation` policy (`04` §6) on every table above that has `society_id`. `users` and `consents`: policy `id = current_setting('app.current_user_id')::uuid` (and `user_id` respectively). `society_memberships`: readable where `user_id` = current user (for the society picker) or `society_id` = current society. `societies`: visible where `id` = current society, or where the current user has an active membership (the picker needs the names); writable only where `id` = current society. `audit_log`: rows of the current society, plus rows with no society written by the current user (e.g. preference changes). `legal_parameters`: no RLS; `app_backend` has SELECT only. The helper functions `app_current_society()` and `app_current_user()` read the settings and return NULL when unset (migration 0001).
