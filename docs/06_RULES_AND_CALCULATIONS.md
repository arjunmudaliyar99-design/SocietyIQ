# 06 — Rules and calculations

All money and alert logic. Implement these as **pure functions in `backend/app/calc/`** with unit tests that use the worked examples below. Where a rule depends on bye-laws or law, it is configurable and marked with an open question; never hard-code a legal value.

---

## 1. Money basics

- All amounts are integers in **paise**. ₹4,200 = `420000`.
- Rounding half-up (`ROUND_HALF_UP`) whenever a rate produces fractions of a paisa.
- Bill rounding (`societies.rounding_rule`, Q-006): `nearest_rupee` (default) rounds the bill's **charges total** to the nearest rupee and adds a visible line "Rounding off" (positive or negative) so lines always add up to the total. `none` keeps exact paise.
- Never mix rounded and unrounded figures in one total.

## 2. Charges for one flat in one period (statutory apportionment)

**Legal basis:** Maharashtra Co-operative Societies Act, 1960, Chapter XIII-B (sections 154B to 154B-31, housing societies), and the Maharashtra Co-operative Societies (Amendment) Rules, 2026, **Rule 106C-12 (levy and apportionment)** and **Rule 106C-11 (funds)**, in force from 18 June 2026. Summary source: ICAI WIRC newsletter, July 2026. Full details and verification status: `08_LEGAL_AND_COMPLIANCE.md` and `docs/legal/LEGAL_REFERENCE.md`.

The Rule fixes **how** each charge is split between flats. The society's general body still fixes **how much** (budget, rates). The billing engine must therefore support these apportionment methods, and each standard head must default to its statutory method:

| Charge head (standard code) | Statutory apportionment | `calc_type` | Inputs needed |
|---|---|---|---|
| Service charges (`service`) | Equally by number of units/flats | `equal_per_flat` | Total service budget for the period |
| Property tax (`property_tax`) | As fixed by the local authority for each flat; common-area tax by carpet area | `as_assessed_per_flat` (+ `per_carpet_area` for common area) | Per-flat amounts from the municipal bill/assessment |
| Water (`water`) | By number/size of inlets or taps in the sanctioned plan | `per_water_point` | `flats.water_points` (Q-011 on weighting by size) |
| Lift (`lift`) | Equally among flats in the building/wing that has the lift | `equal_per_flat_with_lift` | `wings.has_lift` |
| Parking (`parking`) | At the rate fixed by the general body | `per_parking_allotment` | `parking_allotments` |
| Interest on defaults (`interest`) | At the general body rate, **max 12% simple interest per annum** | see §5 | Society rate |
| Non-occupancy (`non_occupancy`) | **10% of service charges**, only for flats not occupied by the member or family | `pct_of_head` (10% of `service`) | `flats.occupancy` |
| Insurance, lease rent (`insurance`, `lease_rent`) | By carpet area | `per_carpet_area` | `flats.carpet_area_sqft` |
| Major repair fund (`major_repair`) | By carpet area, as approved by the general body | `per_carpet_area` | GB-approved total |
| Sinking fund (`sinking_fund`) | **At least 0.25% per annum** of the architect-certified original construction cost of each flat | `pct_of_construction_cost` | `flats.certified_construction_cost_paise` |
| Repair and maintenance fund (`repair_fund`) | **At least 0.75% per annum** of the same cost | `pct_of_construction_cost` | as above |
| Election fund (`election_fund`) | Equally | `equal_per_flat` | |
| Education and training (`education_fund`) | ₹10 per member per month (collected annually, Rule 106C-7) | `per_member_fixed` | members count |
| Welfare fund (`welfare_fund`) | Voluntary | `voluntary` (not on the bill by default) | opt-in per flat |
| Loan instalment and interest, NA tax, other GB-approved charges | As approved by general body, consistent with the Act and Rules | `fixed_per_flat` or `custom_per_flat` with a recorded basis | GB resolution reference |

**Calculation per method** (all results rounded half-up to whole paise):

- `equal_per_flat`: `period_total ÷ number_of_active_flats`. Distribute the remainder paise one by one to flats in flat-number order so the parts add up exactly to the total.
- `equal_per_flat_with_lift`: same, over flats in wings where `has_lift = true`; flats in wings without a lift pay 0.
- `per_carpet_area`: `period_total × flat_carpet_area ÷ total_carpet_area`, same remainder rule. Missing carpet area → warning, flat excluded from the run until fixed.
- `per_water_point`: `period_total × flat_points ÷ total_points`.
- `as_assessed_per_flat`: the flat's municipal amount for the year ÷ billing periods per year (or billed once, per society setting). Exempt flats have amount 0 (see `08` §4 on the Mumbai 500 sq ft exemption).
- `pct_of_head`: `percent × the flat's amount for the referenced head` (non-occupancy: 10% × that flat's service charges).
- `pct_of_construction_cost`: `annual_pct × certified_cost ÷ periods_per_year`.
- `per_parking_allotment`: sum of the GB rates for the flat's active allotments.
- `per_member_fixed`: `rate × number of members on the flat × months in period` (or annually, per setting).

**Validation (block or warn, never silently change):**

- Interest rate above 12% p.a. → **block** with the reason and rule reference.
- Non-occupancy percent other than 10% → **block** (the Rule fixes it at 10% of service charges); non-occupancy on any base other than service charges → block.
- Sinking or repair fund below the minimum percent → **warn** "Below the legal minimum under Rule 106C-11", allow saving with a recorded reason (the general body may be phasing in).
- A head using a method different from its statutory method → **warn**, require a reason and a general body resolution reference.
- All legal numbers come from the `legal_parameters` table (see `05` §3), never from constants in code, so they can be updated when the law or final Model Bye-laws change.

**Example (statutory):** a wing with a lift, 10 flats. Monthly service budget ₹30,000 → ₹3,000 per flat. Flat 301 is let out → non-occupancy ₹300 (10% of ₹3,000). Lift AMC ₹9,500/month over 10 flats → ₹950 each. Flat 301 carpet area 450 sq ft of a 5,000 sq ft total; insurance ₹6,000/year billed monthly (₹500/month) → ₹45. Sinking fund: certified cost ₹12,00,000 × 0.25% = ₹3,000/year → ₹250/month. Total for 301 = 3,000 + 300 + 950 + 45 + 250 = ₹4,545 (property tax and water extra, per their methods).

Other rules:

- A `flat_charge_overrides` row valid for the period replaces the computed amount for that head, with a recorded reason (audit log).
- `one_time` heads apply only in the billing run whose period contains `one_time_period`.
- Quarterly billing: compute each method for the quarter's totals (Q-007).
- The society's registered bye-laws still apply where they do not conflict with the Act and Rules; where they conflict, the Rules prevail. The revised **Model Bye-laws 2026 are still a draft** (objections closed 27 Aug 2026); do not build features that depend only on the draft.

## 3. A bill

```
balance_before = SUM(ledger_entries.amount_paise) for the flat, up to the bill date
arrears        = max(balance_before, 0)
advance        = max(-balance_before, 0)
interest       = interest_on_arrears(...)   # 0 unless enabled, see §5
charges        = sum of charge lines (+ rounding line)
total_due      = max(charges + arrears + interest - advance, 0)
```

Ledger entries written when the run is approved: one `bill` entry of `+charges` (and one `interest` entry if interest > 0). Arrears are **not** posted again; they are already in the ledger.

Bill status after payments: `paid` when allocations cover `charges + interest`; `partially_paid` when some; otherwise `issued`.

**Example (Shanti Sadan, B-207):** balance before ₹25,200 (6 months), new charges ₹4,200, interest disabled → arrears ₹25,200, total due ₹29,400.

## 4. Payments and allocation

- A payment affects the ledger **only when `confirmed`**: write `payment` entry of `−amount`.
- Allocation: oldest bill with an unpaid amount first, then the next. Any remainder is an advance (the ledger balance goes negative). Whether interest is paid before charges within a bill is Q-008; until decided, allocate to the bill as a whole.
- Receipt is created in the same transaction as confirmation, with the next receipt number.
- **Reversal** (wrong entry, bounced cheque): new `payments` row with `status = 'reversed'`, `reversal_of` = original; a `reversal` ledger entry of `+amount`; allocations undone; receipt marked cancelled with the reason. The original row is never edited except its `status` to `reversed`.
- Bounce charges: only if the committee configured one (Q-004).

**Example:** B-207 owes ₹29,400 across 7 bills of ₹4,200. Cash ₹10,000 confirmed → oldest 2 bills paid (₹8,400), third bill partially paid ₹1,600; balance ₹19,400.

## 5. Interest on late dues (off by default)

- Only if `interest_enabled = true` and the rate is set from a **general body resolution** (record the resolution date).
- **Statutory cap: 12% per annum, simple interest** (Rule 106C-12, in force 18 June 2026; the earlier cap was 21%). Reject any rate above `legal_parameters.interest_max_annual_pct`.
- Simple interest on overdue charges only, never interest on interest:
  `interest = round_half_up(overdue_principal × rate/100 × days_overdue/365)`, where overdue principal is the unpaid charges of bills past `due_date + grace_days`.
- Grace period and the exact start date of "default" follow the Act's definition of defaulter and dues (section 154B-1(11), (12)) and the society's bye-laws (Q-002: confirm the exact counting rule with the consultant or lawyer).
- Show interest as its own line on the bill, never hidden in arrears.

## 6. Dues ageing and reminders

- `months_pending` for a flat = number of bills with any unpaid amount.
- Buckets and suggested step:

| Months pending | Bucket | Suggested step (shown to committee) |
|---|---|---|
| 0 | Paid up | — |
| 1–2 | Friendly reminder | Friendly reminder message |
| 3–5 | Formal reminder | Formal reminder notice |
| 6+ | Long pending | "Committee may consider a recovery application under section 154B-29 of the MCS Act (Form Y-6, Rule 106C-14). Consult your legal adviser." |

- For the recovery application the society needs an up-to-date certified ledger, the resolutions approving the charges and interest, and proof of the demand notice (Rule 106C-14). The flat ledger export [M6] must therefore show every bill, payment, interest line and the resolution references. SocietyIQ prepares records only; it never files or drafts legal applications in v1.
- Statutory demand and recovery notices have prescribed modes of service (hand, registered post A.D., or as the Rules say). Reminders sent by email, SMS or app are **reminders**, not statutory notices, unless the lawyer confirms otherwise (see `08` §5).

- Reminder messages are templates per language; sending a batch needs one approval unless auto-send is on.
- Never shame publicly: defaulter lists are visible to committee roles only.

**Seed check (Shanti Sadan):** A-305 ₹12,600 → 3 months → Formal reminder; B-207 ₹29,400 → 7 months → Long pending; C-302 ₹16,800 → 4 months → Formal reminder.

## 7. Expense categories (fixed list)

Electricity, Water, Water tanker, Security, Housekeeping, Lift, Repairs, Plumbing, Electrical, Generator, Pump, CCTV, Fire safety, Pest control, Insurance, Administrative, Other.

(The original plan also listed Cleaning and Landscaping; Q-009 decides whether to add them.) Keys in code: snake_case English (`water_tanker`). Labels via i18n.

## 8. Spending alerts [M12]

Computed per category per society on confirmed expense bills, grouped by **billing period month** (not upload date). A month is "incomplete" until its regular bills arrive; do not alert on incomplete months.

1. **Not enough history:** fewer than 3 previous months with data → no alert; show "Not enough history yet".
2. **Unusual increase:** latest ≥ 20% above the average of the previous 4 months **and** at least ₹5,000 higher.
3. **Rising trend:** three increases in a row **and** latest ≥ 50% above the value two months earlier.
4. **Fixed-rate change:** the previous 3 months were identical and the latest differs (for flat-rate contracts like security, lift, housekeeping).
5. **New regular expense:** present (> 0) in each of the last 2 months and zero in at least 2 of the 3 months before. (Fixes the earlier prototype bug where the rule never fired.)
6. **Seasonal check (later):** with 12+ months, compare with the same month last year.

Percentages are computed in code: `pct = (latest − avg) / avg × 100`, shown to one decimal.

**Worked examples (must be unit tests):**

- Shanti Sadan electricity: previous 4 months 91,000 / 94,000 / 96,500 / 97,300 → average ₹94,700; latest ₹1,31,000 → +38.3%, +₹36,300 → **Unusual increase**.
- Shanti Sadan housekeeping: 52,000 ×4 then 60,300 → +15.96% (below 20%) → not unusual; previous 3 identical and latest differs → **Fixed-rate change**, +₹8,300.
- Gulmohar water tanker: 0 / 0 / 18,000 / 24,000 / 36,000 → average of previous 4 = ₹10,500 → +242.9% → **Unusual increase**; 18,000 → 24,000 → 36,000 after a zero: increases in a row and 36,000 is +100% vs 18,000 → **Rising trend**; present last 2 months, zero in 2 of the 3 before → **New regular expense**.
- Sagar Darshan electricity: stable → no alert.

**Bill checks on upload:** subtotal + GST = total (±₹1, i.e. ±100 paise); same invoice number for the same vendor → "possible duplicate"; same vendor and same total within 7 days → "possible duplicate"; missing GSTIN on a bill showing GST → "please check".

## 9. Compliance status [M10]

- `Overdue`: `next_due_on < today`.
- `Due soon`: within 30 days.
- `OK`: otherwise.
- Reminder days: 90, 60, 30, 7, 0, then weekly while overdue.
- Mark done on date D with `repeat_months = n` → `next_due_on = D + n months` (same day, clamp to month end).

## 10. Quote comparison [M13]

Per quote, computed in code:

- `gst_paise` = 0 if GST included; else `round_half_up(price × gst_rate/100)`.
- `total_payable = price + gst` (if included, `total_payable = price`).
- `advance_paise = round_half_up(total_payable × advance_pct/100)` (base for advance is Q-010; default total payable).
- `cost_per_warranty_year = total_payable / warranty_years` (if warranty > 0).

**Worked example:**

| | Vendor A | Vendor B | Vendor C |
|---|---|---|---|
| Price | ₹4,20,000, GST extra 18% | ₹5,10,000 incl. GST | ₹4,55,000 incl. GST |
| GST | ₹75,600 | included | included |
| Total payable | ₹4,95,600 | ₹5,10,000 | ₹4,55,000 |
| Warranty | 2 years | 5 years | 5 years |
| Cost per warranty year | ₹2,47,800 | ₹1,02,000 | ₹91,000 |
| Completion | 14 days | 10 days | 12 days |
| Advance | 50% = ₹2,47,800 | 20% = ₹1,02,000 | 30% = ₹1,36,500 |
| Exclusions | Scaffolding, debris removal | None stated | Terrace tile replacement |

## 11. Health score (Later; documented so nobody invents one)

Start at 100, clamp 0–100. Overdue compliance −12 each (cap −36); open alerts −6 each (cap −24); compliance due within 30 days −3 each (cap −12); flats with 3+ months dues −2 each (cap −10). Bands: 80+ Healthy, 60–79 Needs attention, below 60 At risk. Always show the breakdown. Weights are guesses to tune in pilots.

## 12. AI guardrails (apply to every prompt)

AI **may**: read documents into fields with a confidence level; classify a document; draft notices, reminders and minutes; translate; write a neutral summary from numbers that code already computed.

AI **must never**: calculate or correct amounts, totals, GST, dues, averages or percentages; overwrite a confirmed value; send anything to residents without a person's approval; choose a vendor or approve a payment; give legal conclusions; accuse anyone of fraud or overcharging; invent facts.

**Wording examples:**

| Never | Write instead |
|---|---|
| "This vendor is overcharging you." | "This quotation is 22% higher than the previous contract. Review before approval." |
| "This invoice is fraudulent." | "This invoice looks similar to invoice #284 and may need a manual check." |
| "Replace the pump." | "Given repeated repair spending, comparing replacement cost with continued repair cost may be worthwhile." |
| "Vendor C is the best." | "Vendor C appears to offer stronger terms based on the uploaded quotations. The final decision rests with the managing committee." |

**Bill extraction prompt rules:** return JSON only, matching the schema; amounts as plain digits in rupees as printed (code converts to paise); never compute or infer an amount that is not printed; `category` must be one of §7; each field `{ "value": ..., "confidence": "high" | "review" }`; unreadable → `null` with `"review"`.

**Drafting prompt rules:** use only facts given in the input; write "[to be confirmed]" where unclear; mark drafts "DRAFT — for review"; minutes end with signature lines; quote summaries end with "The final decision rests with the managing committee."
