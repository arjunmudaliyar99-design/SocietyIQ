# 02 — Product spec

What to build. Modules are grouped by release. Each module lists screens, flows and rules. Money rules live in `06_RULES_AND_CALCULATIONS.md`; tables in `05_DATABASE.md`.

Tags: **[v1]** core, build first. **[v1.5]** next after core. **[Later]** do not build until the build plan says so.

---

## 1. Products

1. **Committee web** (`apps/committee-web`): desktop-first, works on phones. For admin, treasurer, committee, consultant, auditor.
2. **Resident PWA** (`apps/resident-pwa`): mobile-first, installable from the browser. For owners, tenants and family delegates.
3. Both use one FastAPI backend and one PostgreSQL database.

Rules:

- Residents see only what the committee approves or publishes.
- Residents never edit the society's books.
- Money always goes to the society's own bank account.

## 2. Roles and permissions [v1]

| Action | Admin | Treasurer | Committee | Consultant | Auditor | Owner | Tenant | Delegate |
|---|---|---|---|---|---|---|---|---|
| Society settings, roles, invites | ✅ | | | ✅ (if invited as admin) | | | | |
| Flats, members, import | ✅ | ✅ | view | ✅ | view | | | |
| Charge setup | ✅ | ✅ | view | ✅ | view | | | |
| Create and approve billing run | ✅ | ✅ | view | create only | view | | | |
| Record payments, reverse with reason | ✅ | ✅ | | ✅ | view | | | |
| View all dues and ledger | ✅ | ✅ | ✅ | ✅ | ✅ | own flat | own flat if allowed | linked flat |
| Complaints: manage | ✅ | ✅ | ✅ | | | raise, view own | raise, view own | raise for flat |
| Notices: draft and publish | ✅ | | draft | draft | | read | read | read |
| Compliance items | ✅ | ✅ | ✅ | ✅ | view | | | |
| Vendor bills (expenses) | ✅ | ✅ | upload, view | ✅ | view | | | |
| Audit log | ✅ | view | | | ✅ | | | |
| Export data | ✅ | ✅ | | | ✅ | own receipts | | |

A person can hold different roles in different societies (for example a consultant). Permissions are checked in the backend for every request; the UI only hides buttons.

## 3. Module: Sign-in and society setup [v1]

**Sign-in**

- Committee web: email + password, or email one-time code. Phone OTP later (needs a paid SMS provider; see `10_OPEN_QUESTIONS.md`).
- Resident PWA: email one-time code first; phone OTP later. Large single input, one button.
- After sign-in, if the person belongs to more than one society, show a simple society picker.

**Create a society** (done by us or the admin), one screen, steps shown 1 of 3, 2 of 3, 3 of 3:

1. Society details: name, registration number (optional), address, city, state (default Maharashtra), PIN code, financial year start month (default April).
2. Billing settings: billing frequency (monthly or quarterly), bill date (day of month), due date (days after bill date), society UPI ID and payee name (for QR codes), bank name and account last 4 digits (display only).
3. Invite the committee: name, email or phone, role.

**Invitations:** invited person gets an email link; on first sign-in they accept and pick their language.

## 4. Module: Flats, members and import [v1]

**Flats:** wing/building (does it have a lift?), flat number, carpet area in sq ft, flat type (display only, e.g. 1RK, 2BHK), usage (residential/commercial), certified construction cost, number of water taps/inlets, municipal property account number, occupancy: owner-occupied / family-occupied / let out / vacant.

**Members:** linked to a flat. Name, phone, email (optional), type: owner / joint owner / tenant / family delegate, from date, to date. A member does not need a login. A member can be linked to a user account later.

**Import from Excel (done-for-you setup):**

1. Download our template (`.xlsx`) with columns: Wing, Wing has lift (Y/N), Flat number, Carpet area sq ft, Flat type, Usage, Certified construction cost (₹), Water taps, Municipal account no., Occupancy, Owner name, Owner phone, Owner email, Tenant name, Tenant phone, Opening balance (₹, positive = flat owes).
2. Upload the filled file.
3. Preview screen: every row with a status: OK / warning / error, in plain words ("Row 14: phone number has 9 digits").
4. Fix in the file and re-upload, or import only the OK rows.
5. Confirm. Opening balances become ledger entries of type `opening_balance` with the import as the source.

Never import silently. Always preview, always confirm.

## 5. Module: Charges and automatic billing [v1]

**Charge heads** (set up once, approved by the committee, based on general body resolutions):

- SocietyIQ offers the **statutory charge heads** from Rule 106C-12 (service charges, property tax, water, lift, parking, interest, non-occupancy, insurance, lease rent, major repair fund, sinking fund, repair and maintenance fund, election fund, education fund, welfare fund, other GB-approved charges). Each comes pre-set with its **legal apportionment method** (see `06` §2): for example service charges split equally per flat, insurance by carpet area, water by number of taps.
- The committee enters only the amounts the general body approved (budget totals or rates) and the resolution date.
- Non-occupancy charges are fixed at **10% of the flat's service charges**, only for flats marked "let out". The screen explains this in one line and does not allow another percentage.
- Interest on late dues is optional and **cannot exceed 12% simple interest per annum**.
- Sinking fund and repair fund show the legal minimum (0.25% and 0.75% per annum of the certified construction cost) and warn if lower.
- Parking: allot slots to flats (open, stilt, covered, mechanical; two- or four-wheeler) at the general body rate. Parking is an allotment, never a sale.
- Property tax: enter or import each flat's amount from the municipal bill; exempt flats (e.g. Mumbai residential ≤500 sq ft carpet) show ₹0 with the reason. SocietyIQ never calculates municipal tax itself.
- Setup wizard asks only for what is needed: carpet area per flat, certified construction cost, number of taps, which wings have lifts. Missing data is listed plainly ("12 flats have no carpet area yet").
- Per-flat override possible only with a recorded reason.
- Any deviation from the statutory method needs a reason and a general body resolution reference, and is flagged in the audit log.

**Billing run** (the heart of automation):

1. On the bill date, the system creates a **draft billing run** for the period (a scheduled job; also a "Create bills now" button).
2. Draft shows: number of flats, total amount, any flats with warnings (no members, zero amount).
3. The treasurer or admin reviews and taps **Approve and send**.
4. On approval: bills get numbers, PDFs are generated, ledger entries are written, residents are notified (email now; SMS and WhatsApp later).
5. Option in settings: **auto-approve** future runs if the charges have not changed since the last approved run. Default: off.

**Bill contents:** society name and address, bill number, flat, member name, period, bill date, due date, each charge line, previous arrears, interest (only if enabled), total due, payment instructions with UPI QR, "Pay online" link to the resident PWA.

**Printed bills:** one button produces a single PDF with every flat's bill (one per page) for the watchman to hand out. Each page has the UPI QR with the flat's amount.

**Corrections:** a sent bill is never edited. Cancel it with a reason (writes a reversal) and issue a corrected bill.

## 6. Module: Payments and receipts [v1]

**Ways a payment is recorded:**

| Method | Who records | Status flow |
|---|---|---|
| Cash | Treasurer or office | `recorded` → resident confirms (optional, one tap in PWA or link) → `confirmed` by treasurer |
| Cheque | Treasurer or office, with cheque number, bank, date | `recorded` → `confirmed` when cleared (treasurer taps "Cleared") or `bounced` |
| UPI / NEFT to society account | Resident reports it in PWA with reference, or treasurer records it | `pending` → `confirmed` by treasurer (bank matching later [v1.5]) |
| Payment gateway | Automatic | [Later] |

Rules:

- **A receipt is issued only when a payment is `confirmed`.** Until then the resident sees "Received, waiting for confirmation".
- One tap to record: amount pre-filled with the flat's outstanding; the treasurer can change it.
- Payments are allocated to the oldest unpaid bill first (see `06` §4).
- A wrong payment is reversed with a reason, never deleted.
- Bounced cheque: reverses the payment; optional bounce charge only if the committee configured one (Q-004).

**Receipt:** receipt number, date, flat, member, amount in figures and words, method and reference, bills it was allocated to, "This is a computer-generated receipt". PDF, downloadable, shown in the PWA.

## 7. Module: Dues and defaulters [v1]

- **Dues screen:** list of flats with outstanding amount and months pending, sorted by amount. Filters: all / 1–2 months / 3–5 months / 6+ months.
- **Flat ledger:** every bill, payment, adjustment and reversal for one flat with a running balance.
- **Reminder ladder** (messages are drafts the committee can edit; send needs one approval per batch):
  - 0 months: Paid up.
  - 1–2 months: Friendly reminder.
  - 3–5 months: Formal reminder notice.
  - 6+ months: show "Committee may consider a recovery application under section 154B-29 of the MCS Act. Consult your legal adviser." Do not generate legal notices in v1 (Q-005).
- **Ledger export for recovery:** one button exports a flat's certified-style ledger (PDF and Excel) with every bill, payment, interest line and the general body resolution references, because a recovery application under Rule 106C-14 needs it.
- Show flat numbers in lists; personal details only on the flat page.

## 8. Module: Complaints and requests [v1]

- **Raise (PWA):** big button "Report a problem". Pick a category with icons (Water/leak, Lift, Electricity, Cleaning, Security, Parking, Other), optional photo (camera or gallery), short text (optional; voice input later), location (my flat / common area). One "Send" button.
- **Raise on behalf:** committee members can raise a complaint for a flat (for residents without phones).
- **Committee view:** list with status: Open → In progress → Resolved → Closed. Assign to a person or vendor name. Add an update; the resident sees updates.
- Resident can mark "Fixed" or "Not fixed" after Resolved.
- QR codes on the lift or pump [v1.5]: each asset gets a QR that opens a pre-filled complaint.

## 9. Module: Notices [v1]

- Committee drafts a notice: title, message, audience (all / owners / tenants / a wing), optional attachment.
- **AI helper [v1, if an AI key is configured]:** "Help me write" turns rough notes into a clear notice and offers translations into the other four languages. The draft is always shown for editing; it is never sent automatically.
- Publish: residents see it in the PWA; email to members with email. WhatsApp: "Coming soon".
- Read receipts: count of residents who opened it.

## 10. Module: Committee home (dashboard) [v1]

One screen, at most six cards, each tappable:

1. Collected this month (₹) and number of payments.
2. Total outstanding (₹) and number of flats with dues.
3. Payments waiting for confirmation (number) → confirm list.
4. Open complaints (number).
5. Due soon: compliance items in the next 30 days [v1 once M10 is built].
6. Next billing run date and status.

Below the cards: "What needs your attention" list in plain words, e.g. "3 cheques waiting to be marked cleared".

## 11. Resident PWA screens [v1]

Home screen in **Simple mode** (default) has three big buttons plus a dues banner:

- Banner: "Flat B-207 · Due this month ₹4,200 · Due by 10 Nov".
- **Pay** → shows the amount, UPI QR and "Open UPI app" button (UPI deep link), and "I have paid" form (reference number, optional screenshot). Explains that the treasurer will confirm.
- **Notices** → list, newest first, unread in bold.
- **Report a problem** → complaint flow above.

Other screens (reachable from a simple menu): My bills, My receipts, My complaints, Language, Text size, Help (champion's and SocietyIQ's contact), Sign out.

Detailed mode (optional toggle) shows the ledger and more filters.

## 12. Demo seed data (fictional — use exactly these)

From the earlier prototype. All names fictional. Do not add real people.

**Shanti Sadan CHS**, Chembur, Mumbai, 120 flats, monthly maintenance ₹4,200.

- Dues by flat (₹, months): A-101 0; A-204 4,200 (1); A-305 12,600 (3); B-102 0; B-207 29,400 (7); B-401 8,400 (2); C-103 0; C-302 16,800 (4); C-404 4,200 (1); D-201 0.
- Monthly spend for 5 months (₹): Electricity 91,000 / 94,000 / 96,500 / 97,300 / 1,31,000. Security 85,000 each month. Housekeeping 52,000 ×4 then 60,300. Water 38,000 / 41,000 / 39,500 / 40,200 / 42,000. Repairs 12,000 / 8,500 / 22,000 / 9,500 / 31,000. Lift 16,000 each month. Pest control 4,500 / 0 / 4,500 / 0 / 4,500. Administrative 9,000 / 8,800 / 9,400 / 9,100 / 9,300.
- Compliance (days from today): Generator service −5 (Powergen Services); Water tank cleaning 12 (AquaClean); Lift AMC renewal 25 (ABC Elevators; renewal quote ₹2,34,000 vs ₹1,92,000 now); Fire safety audit (Form B) 40 (SafeFire Consultants); Building insurance 75; Structural audit 150; CCTV AMC 210 (SecureVision).

**Gulmohar Heights CHS**, Thane West, 64 flats, monthly maintenance ₹3,600.

- Dues: 1-01 0; 1-04 3,600 (1); 2-02 10,800 (3); 2-03 0; 3-01 0; 3-04 25,200 (7); 4-02 7,200 (2).
- Spend: Electricity 48,000 / 47,500 / 49,200 / 48,800 / 50,100. Security 56,000 each. Housekeeping 31,000 each. Water 22,000 / 22,500 / 21,800 / 22,100 / 22,600. Water tanker 0 / 0 / 18,000 / 24,000 / 36,000. Repairs 6,000 / 4,500 / 7,000 / 5,200 / 6,800. Lift 9,500 each. Administrative 6,200 / 6,100 / 6,400 / 6,000 / 6,300.
- Compliance: Fire safety audit −18; Pump service 20 (Jal Pumps); Lift AMC renewal 55 (Skyline Lifts); Building insurance 160.

**Sagar Darshan CHS**, Sion, Mumbai, 42 flats, monthly maintenance ₹3,000.

- Dues: 101 0; 102 3,000 (1); 201 0; 202 0; 301 6,000 (2).
- Spend: Electricity 36,000 / 35,200 / 36,800 / 37,100 / 36,500. Security 38,000 each. Housekeeping 24,000 each. Water 15,000 / 15,400 / 14,800 / 15,200 / 15,100. Repairs 3,000 / 2,500 / 4,200 / 3,800 / 3,500. Administrative 4,800 / 4,600 / 5,000 / 4,700 / 4,900.
- Compliance: Water tank cleaning 45 (AquaClean); Fire safety audit 120 (SafeFire Consultants); Structural audit 300.

**Seed charge setup** (fictional, but consistent with the statutory methods in `06` §2; every flat owner-occupied unless stated, no lift charge, property tax and water not seeded):

| Society | Service charges (equal per flat) | Repair and maintenance fund (0.75% p.a.) | Sinking fund (0.25% p.a.) | Certified cost per flat | Monthly total |
|---|---|---|---|---|---|
| Shanti Sadan CHS | ₹3,400 | ₹600 | ₹200 | ₹9,60,000 | ₹4,200 |
| Gulmohar Heights CHS | ₹2,900 | ₹525 | ₹175 | ₹8,40,000 | ₹3,600 |
| Sagar Darshan CHS | ₹2,400 | ₹450 | ₹150 | ₹7,20,000 | ₹3,000 |

Mark flat A-305 (Shanti Sadan) as let out to demonstrate non-occupancy: +₹340 (10% of ₹3,400) on bills from the seed date onward; its seeded arrears stay as listed.

Seed only the flats listed; generate the remaining flats with zero dues and fictional names like "Member A-102". Demo login accounts use `@example.com` emails.

## 13. Module: Compliance and AMC tracker [v1, milestone M10]

- Items: fire safety audit (Form B), structural audit, lift AMC, pump AMC, generator service, water tank cleaning, CCTV AMC, building insurance, pest control, other.
- Fields: title, type, vendor, last done date, next due date, repeats every N months, notes, attached document.
- Reminders at 90, 60, 30 and 7 days before, on the due date, and weekly while overdue (to committee only).
- Status: OK / Due soon (≤30 days) / Overdue.
- Mark done: enter the date done; next due date is calculated from the repeat interval.

## 14. Module: Vendor bills and spending alerts [v1.5, milestones M11–M12]

- Upload a vendor bill (PDF, JPG, PNG; max 10 MB).
- AI reads: vendor, invoice number, invoice date, due date, billing period, category (one of the fixed list in `06` §7), subtotal, GST, total, description. Each field has confidence "high" or "review".
- Review screen: fields needing review are highlighted; the person confirms or edits; "Confirm and save".
- Code checks: subtotal + GST = total (±₹1), duplicate invoice number for the same vendor, same vendor and amount within 7 days.
- Spending alerts per `06` §8, shown on the committee home and a monthly summary.

## 15. Module: Quote comparison [v1.5, milestone M13]

- A "comparison" (e.g. "Building waterproofing 2026") with 2 to 5 quotes uploaded.
- AI extracts: vendor, price, GST included or extra and rate, warranty, completion time, advance %, payment milestones, exclusions.
- Code computes: GST amount, total payable, advance amount, cost per warranty year.
- Table side by side; AI may write a neutral summary from the computed figures only, ending with "The final decision rests with the managing committee."

## 16. Module: Meeting minutes [v1.5, milestone M14]

- Inputs: meeting type (Managing committee / AGM / SGM), date, members present, language, rough notes.
- AI draft: heading, attendance, numbered items each with "Discussion" and "Resolved / Action", next meeting, signature lines. Marked "DRAFT — for secretary's review". Writes "[to be confirmed]" where unclear. Never invents facts.

## 17. Later modules (do not build yet)

Payment gateway per society (Razorpay or Cashfree with direct settlement); bank statement upload and matching; bank statement auto-fetch (Account Aggregator, to verify); WhatsApp notifications and bill forwarding; assets and repair history; registers, share certificates, nominations and NOCs; rental NOC and agreement expiry reminders; rent tracker between owner and tenant (records only); facility booking; record search over minutes and bye-laws; consultant multi-society console; monthly society report; health score; gate, visitors and parcels.
