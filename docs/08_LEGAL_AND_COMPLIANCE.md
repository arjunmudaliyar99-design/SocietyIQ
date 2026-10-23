# 08 — Legal and compliance (for the build)

What the law requires **of the software**. The full human-readable reference (Acts, sources, books, people, company registration) is `docs/legal/LEGAL_REFERENCE.md`.

**Status:** researched 23 Oct 2026 from secondary sources (professional newsletters, law-firm and consultant articles, news). **Not legal advice.** Every value here must be checked by the society consultant or a lawyer before the first pilot, then marked verified in `legal_parameters` (`verified_by`, `verified_on`). The Legal & Society Advisor's further legal points will be added to `docs/inputs/ADVISOR_NOTES.md` and merged here.

---

## 1. Which law applies (Maharashtra cooperative housing societies)

| Layer | Status | What it means for us |
|---|---|---|
| Maharashtra Co-operative Societies Act, 1960 — **Chapter XIII-B** (sections 154B to 154B-31, housing societies) | In force (inserted 2019) | Definitions of dues and defaulter, funds, charges, nomination, recovery (154B-29) |
| MCS Rules, 1961 — **Chapter XI-B, Rules 106C-1 to 106C-14** (Amendment Rules 2026) | In force from 18 June 2026 | Binding rules on funds (106C-11), levy and apportionment of charges (106C-12), meetings (106C-13), recovery (106C-14) |
| Society's registered bye-laws (usually Model Bye-laws 2014) | In force for each society | Apply where not inconsistent with the Act and Rules |
| Revised Model Bye-laws 2026 | **Draft** (objections closed 27 Aug 2026; not confirmed notified as of 23 Oct 2026) | Do not depend on draft-only provisions; watch for notification |
| Municipal law (e.g. Mumbai Municipal Corporation Act, 1888 for MCGM) | In force | Property tax is fixed by the municipal body, not the society |
| Digital Personal Data Protection Act, 2023 and its Rules | Phasing in (verify dates) | Consent, minimum data, security, breach notice, user rights |

v1 supports **cooperative housing societies (tenant ownership / tenant co-partnership) in Maharashtra only**. Condominiums under the Maharashtra Apartment Ownership Act, premises societies and other states are out of scope until a decision says otherwise.

## 2. Charges and billing (Rule 106C-12, 106C-11)

Implemented in `06_RULES_AND_CALCULATIONS.md` §2. Summary of legal constraints the software enforces:

1. Service charges split **equally per flat**.
2. Property tax **as fixed by the local authority** per flat; common-area tax by carpet area.
3. Water by **number/size of taps or inlets** per sanctioned plan.
4. Lift costs **equally among flats in the building that has the lift**.
5. Parking at the **general body rate**; parking is allotted, not sold.
6. Interest on defaults at the general body rate, **max 12% simple per annum**.
7. Non-occupancy charges **10% of service charges**, only when the flat is not occupied by the member or family.
8. Insurance, lease rent and major repairs **by carpet area**.
9. Sinking fund **≥ 0.25% p.a.** and repair and maintenance fund **≥ 0.75% p.a.** of the architect-certified construction cost of each flat.
10. Election fund equal; welfare fund voluntary; education and training contribution **₹10 per member per month** (Rule 106C-7).

## 3. Seed values for `legal_parameters` (all `verified_by = NULL` until checked)

| code | value | source |
|---|---|---|
| `interest_max_annual_pct` | 12 | MCS Rules 106C-12 (2026) |
| `non_occupancy_pct_of_service` | 10 | MCS Rules 106C-12 (2026); earlier Govt order of Aug 2001 under s.79A |
| `sinking_fund_min_annual_pct` | 0.25 | MCS Rules 106C-11 (2026) |
| `repair_fund_min_annual_pct` | 0.75 | MCS Rules 106C-11 (2026) |
| `education_fund_per_member_month_paise` | 1000 | MCS Rules 106C-7 (2026) |
| `committee_repair_limit_paise` (≤25 members) | 10000000 (₹1 lakh) | MCS Rules 106C-13 (2026) |
| same (26–50) | ₹2 lakh | same |
| same (51–100) | ₹3 lakh | same |
| same (101–1,000) | ₹4 lakh | same |
| same (1,001+) | ₹5 lakh | same |

The committee repair limit is used later (approvals feature) to warn when a repair spend needs general body approval.

## 4. Property tax (municipal)

- The society **does not calculate** municipal property tax. It passes on to each flat the amount the municipal corporation fixed for that flat (Rule 106C-12). Number of rooms (1RK, 2BHK) is **not** a basis; the municipal assessment is.
- **Mumbai (MCGM):** capital value system; tax = capital value × rate, capital value based on ready reckoner base value × carpet area × weightage factors. Residential properties with carpet area **up to 500 sq ft are exempt** from 1 January 2022. Sources disagree on whether the exemption covers all tax components or only the general tax, and on the status of a 60% concession for 501–700 sq ft. **Always use the amounts printed on the actual MCGM bill.**
- Example for the product: a 300 sq ft 1RK and a 500 sq ft flat (residential, carpet area) both show property tax ₹0, reason "MCGM ≤500 sq ft exemption", if the MCGM bill shows them exempt; a 650 sq ft flat shows its assessed amount.
- **Thane, Navi Mumbai, Pune** use their own municipal rules; do not apply MCGM rules there. Enter per-flat amounts from their bills.

## 5. Notices and communication

- The Legal & Society Advisor advised that notices can now be sent by SMS on phones. Research found: the 2026 Rules allow hybrid meetings and record-keeping of video proceedings; recovery proceedings have prescribed service modes (hand, registered post A.D., newspaper publication); some sources say email and messaging notices are valid where the society's bye-laws permit, with proof of delivery. **Exact rule for SMS/electronic service of general body notices is not yet verified** (Q-012).
- Product rule until verified:
  - App, email and SMS messages are labelled **reminders / information**.
  - For general body meeting notices, the app records delivery and read time per member (useful as proof) and also generates a printable notice and a dispatch register for hand delivery.
  - Never claim in the UI or marketing that an electronic message is a legally valid statutory notice until the lawyer confirms the exact provision.
- Meeting rules to build into the compliance calendar later: AGM within the period required after year end (commonly cited: by 30 September), 14 clear days' notice for general body meetings, SGM under section 76 with 5 clear days' notice, quorum two-thirds of members or 20 whichever is less (Rule 106C-13). Verify before use.

## 6. Membership, nomination, records (later modules)

Nomination (Rules 106C-8, 106C-9) by member or each joint member separately, recorded in the register; provisional membership for nominees (Rule 106C-6, Form Y-4 with indemnity bond); associate membership (Form Y-5A); deemed membership if an application is not decided in three months (s.22(2), per secondary source). These belong to the Registers module [Later]; the database must not block storing joint members and nominees.

## 7. Recovery of dues

Housing societies recover dues under **section 154B-29** (previously commonly done under section 101) by an application in **Form Y-6** with ₹100 court fee before the Registrar, supported by a certified ledger, resolutions approving charges and interest, and the demand notice (Rule 106C-14). SocietyIQ v1 provides the ledger export and resolution references only.

## 8. Personal data (DPDP Act 2023)

- The society is the data fiduciary for residents' data; SocietyIQ processes it on the society's behalf (state this in the subscription agreement).
- Collect minimum data: name, flat, phone, optional email. **No Aadhaar, no PAN.**
- Consent screen at first sign-in (terms, privacy, analytics opt-in) stored in `consents`.
- Rights: a resident can request a copy of their data and correction; deletion where no legal retention applies (financial records may need to be retained; Q-013 retention period).
- Breach: incident plan and notification duty; keep an incident log.
- AI providers: no real personal or financial data to any provider whose terms allow training on inputs.
- Privacy policy and terms reviewed by a lawyer before the first pilot.

## 9. Payments

- SocietyIQ **never holds money**; all payments settle to the society's bank account (avoids payment-aggregator licensing).
- Receipts only after confirmation (bank match, gateway confirmation or treasurer).
- GST on maintenance charges is the society's responsibility; widely cited thresholds are ₹7,500 per member per month and ₹20 lakh annual turnover (verify with the society's CA). v1 does not compute GST on members' bills; a `gst_applicable` society setting is Q-014.

## 10. Our own company and IP (not in the software)

See `docs/legal/LEGAL_REFERENCE.md` §6. Before charging any society: register the business, sign the founders' agreement with IP assignment to the business, check employment contracts, file a trademark search for "SocietyIQ".
