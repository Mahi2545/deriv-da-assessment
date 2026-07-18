# Deriv Data Analyst Assessment — Submission

**Candidate analysis date:** 18 July 2026  
**Data sources:** `client_signup.json`, `client_profile.json`, `client_deposit.json`, `client_trades.json`  
**Method:** Python cross-table joins (`analysis.py`) validating referential integrity, compliance gates, funnel metrics, and field-level consistency.

> **Note on Q2 placeholders:** The brief uses `[STAKEHOLDER_ROLE]` and `[BUSINESS_FOCUS_AREA]`. This submission uses **Head of Growth** and **signup → first-deposit → first-trade conversion**. Replace these if your assessment portal assigned different values.

---

## Prompts Used

### Prompt 1 (Data Exploration)
> Load all four JSON tables, join on `client_id`, and systematically check: (1) referential integrity orphans, (2) schema/field mismatches, (3) KYC/compliance gate violations (deposits/trades when `kyc_status` ≠ approved), (4) account-status vs trading activity, (5) PnL vs price consistency, (6) implausible DOB ages, (7) trades before first deposit, (8) funnel conversion by `referral_source` and `promo_code`.

### Prompt 2 (Dashboard Design)
> Using funnel metrics from the data (63.3% deposit rate, 60% trade rate, 0% social_media conversion, orphan deposit CL031, KYC breach CL012), design a Monday executive dashboard for Head of Growth with three actionable items grounded in specific table fields, measurable KPIs, % improvement estimates with reasoning, and blockers.

### Prompt 3 (Alerting Design)
> Design at least four automated alerts referencing specific fields and cross-table relationships, with frequency, notify role, delivery channel, scheduled query tool, and state-tracking for deduplication.

---

# 1. Data Exploration & Anomaly Detection

## How we investigated

1. Loaded all four JSON files into Python dictionaries keyed by `client_id`.
2. Ran referential-integrity checks: every `client_deposit.client_id` and `client_trades.client_id` must exist in `client_signup`.
3. Cross-joined signup `kyc_status` and profile `account_status` against deposits and trades chronologically.
4. Validated business rules: no trading without funding, no activity on rejected KYC or non-active accounts, PnL consistent with price movement.
5. Aggregated funnel metrics by `referral_source` and `promo_code`.

**Key population stats discovered:**
| Metric | Value |
|--------|-------|
| Total signups | 30 |
| KYC approved | 28 (93.3%) |
| Clients with ≥1 completed deposit | 19 (63.3%) |
| Clients with ≥1 trade | 18 (60.0%) |
| Never deposited | 11 clients |

---

## 1a. Three Anomalies

### Anomaly 1 — Orphan deposit (broken foreign key)

- **What you found:** In `client_deposit.json`, row `DEP020` has `client_id = "CL031"`, but `CL031` does not exist in `client_signup.json` (signup table ends at `CL030`). Deposit amount: `$1,200.00`, status `completed`.
- **Why it's a problem:** This breaks the declared one-to-many relationship (`client_signup` → `client_deposit`). Revenue is attributed to a non-existent client, corrupting CAC/LTV reporting, reconciliation, and audit trails. Payment ops cannot link this funds movement to a real identity.
- **What you'd do about it:** Immediately quarantine `DEP020` in the payments ledger, trace the payment gateway reference to find the true account, and either back-fill a missing signup record or reverse/correct the deposit. Add a DB foreign-key constraint: `client_deposit.client_id` → `client_signup.client_id`.

---

### Anomaly 2 — Deposit accepted after KYC rejection (compliance gate failure)

- **What you found:** `client_signup.json` row `CL012` has `kyc_status = "rejected"`. Despite this, `client_deposit.json` row `DEP008` shows a **completed** deposit of `$350.00` on `2024-02-25` for the same `client_id`. Profile shows `account_status = "suspended"`.
- **Why it's a problem:** Regulated trading platforms must block funding until KYC is approved. Accepting a deposit for a rejected client is a compliance violation — it exposes the firm to AML/sanctions risk, potential regulator fines, and chargeback disputes. The downstream suspended status confirms the account should never have been funded.
- **What you'd do about it:** Escalate to Compliance for a SAR review, freeze remaining funds, and audit all deposits where `kyc_status IN ('rejected','pending')`. Implement an upstream gate: reject deposit API calls unless `kyc_status = 'approved'`.

---

### Anomaly 3 — Trade executed on an inactive account (operational control failure)

- **What you found:** `client_profile.json` row `CL008` has `account_status = "inactive"` and `last_login_date = "2024-03-01"`. Yet `client_trades.json` row `TRD006` records a **closed** Gold trade on `2024-11-05` (8 months later) with `pnl_usd = 75.00` and `volume_lots = 0.5`.
- **Why it's a problem:** Inactive accounts should be blocked from opening new positions. This indicates the trading engine is not enforcing account-status checks — creating operational risk (stale KYC, dormant fraud, unreconciled exposure) and unreliable client-activity reporting for the Monday executive review.
- **What you'd do about it:** Reverse or manually review `TRD006`, patch the order-management system to hard-block trades when `account_status ≠ 'active'`, and run a historical backfill query joining `client_trades` ↔ `client_profile` to find other violations.

---

## 1b. Non-Obvious Insight (cross-table pattern)

**Finding:** Referral channel quality is extremely polarised — `referral_source` predicts both conversion *and* deposit value, but not in the way marketing spend would suggest.

| referral_source | Signups | Deposit rate | Trade rate | Avg deposit (USD) |
|-----------------|---------|--------------|------------|-------------------|
| organic | 7 | **100%** | **100%** | $2,243 |
| paid_search | 6 | **100%** | 83.3% | $1,208 |
| referral | 6 | 83.3% | 83.3% | **$19,720** |
| affiliate | 6 | **16.7%** | 16.7% | $250 |
| social_media | 5 | **0%** | **0%** | $0 |

**Methodology:** Joined `client_signup.referral_source` to deposit/trade flags per `client_id` using Python (`analysis.py`, Section 9). Calculated deposit-rate = clients with ≥1 completed deposit ÷ signups, and average first-deposit value per channel.

**Business significance:** Five `social_media` signups (CL004, CL010, CL016, CL021, CL026) generated **zero deposits and zero trades** — pure acquisition cost with no return. Meanwhile, `referral` clients average **$19,720** per depositor (driven by CL019's $75,000 deposit), making referral the highest-value channel by 8× vs organic. A Head of Growth reviewing Monday metrics would misallocate budget if they only tracked signup volume without this cross-table funnel view. The firm should pause social_media spend and reallocate to referral programmes, while investigating why affiliate signups (6 clients, 1 depositor) stall after signup.

**Secondary insight (promo codes):** Cross-tab of `promo_code` × deposit conversion shows `WELCOME` converts at only **20%** (1/5) vs **80%** for `PROMO10` (4/5) and **70%** for no promo — suggesting the WELCOME offer may attract low-intent signups or has a broken redemption flow.

---

## (Optional) Data Health Map

| Check | Finding |
|-------|---------|
| FK orphans | 1 deposit (`DEP020` → `CL031`) |
| Schema drift | `DEP012` uses `credit_card` key instead of `payment_method` |
| Null `promo_code` | 66.7% of signups (expected — optional field) |
| Null `last_login_date` | 1/30 (CL026, pending account — logical) |
| PnL mismatch | `TRD012`: `open_price = close_price = 2320` but `pnl_usd = 245` |
| Impossible age | CL025 `date_of_birth = 1888-12-19` (~136 years old) |
| Trade without deposit | `TRD005` (CL007): traded with no completed deposit |
| KYC pending with profile | CL026: `kyc_status = pending`, `account_status = pending` — consistent |

Validation script: `analysis.py` in project root.

---

# 2. Dashboard Design

**Stakeholder:** Head of Growth  
**Business focus:** Signup → first-deposit → first-trade conversion funnel  
**Review cadence:** Every Monday morning

### Dashboard layout (conceptual)

| Row | Widget | Fields used |
|-----|--------|-------------|
| KPI strip | Weekly signups, deposit rate, trade rate, total deposit USD | `signup_date`, `client_id`, `amount_usd`, `status` |
| Funnel | Signup → KYC approved → First deposit → First trade | `kyc_status`, deposit/trade dates |
| Channel table | Conversion & avg deposit by `referral_source` | `referral_source`, joins |
| Risk flags | KYC breaches, orphan deposits, inactive trades | cross-table rules |
| Promo tracker | Conversion by `promo_code` | `promo_code`, deposit flag |

---

## 2a. Three Actionable Items

### Action 1 — Compliance: Close the KYC funding gate

| Element | Detail |
|---------|--------|
| **Department** | Compliance & Onboarding Operations |
| **Action** | Audit all deposits/trades for clients where `kyc_status ≠ 'approved'`; block future funding at API level. Immediate case: CL012 (`kyc_status = rejected`) + DEP008 ($350 completed). |
| **Monitoring KPI** | Count of completed deposits where joined `kyc_status` ≠ `'approved'` (current baseline: **1**) |
| **Success criteria** | KPI = **0** for 30 consecutive days; CL012 deposit refunded or escalated with case ID logged |

### Action 2 — Growth Marketing: Reallocate social_media budget

| Element | Detail |
|---------|--------|
| **Department** | Performance Marketing / Growth |
| **Action** | Pause paid social campaigns targeting the 5 `social_media` signups (CL004, CL010, CL016, CL021, CL026) until onboarding funnel is fixed. Launch retargeting to convert the 11 never-deposited clients. |
| **Monitoring KPI** | First-deposit conversion rate for `referral_source = 'social_media'` (current: **0%**, 0/5) |
| **Success criteria** | Social_media deposit rate ≥ **40%** (half of platform average 63.3%) within 8 weeks; at least **2 of 5** existing social signups complete first deposit |

### Action 3 — Treasury & Payments: Eliminate orphan deposits

| Element | Detail |
|---------|--------|
| **Department** | Treasury & Payments Operations |
| **Action** | Resolve DEP020 (`client_id = CL031`, $1,200) — trace, correct, or reverse. Fix DEP012 schema (`credit_card` → `payment_method`). |
| **Monitoring KPI** | % of deposits with valid FK to `client_signup` (current: **19/20 = 95%**) |
| **Success criteria** | FK match rate = **100%**; zero deposits with `payment_method` null (currently 1 — DEP012) |

---

## 2b. Improvement Estimates & Blockers

| Action | Est. improvement | Reasoning basis | Main blocker |
|--------|------------------|-----------------|--------------|
| KYC gate | **Risk reduction** (not revenue %) | 1 confirmed breach in 20 deposits = **5%** of deposit rows violate compliance. Eliminating this prevents regulatory fines that dwarf revenue gains. | Legacy payment API may not check KYC synchronously; requires eng sprint |
| Social media funnel | **+6–8% total deposit volume** | 5 social signups × platform avg deposit among converters (~$2,243 organic benchmark) ≈ **$11,200** potential vs $0 today. $11,200 / ~$123,000 total deposits ≈ **9%** | Broken mobile onboarding for social UTM links; no deposit prompt after signup |
| Orphan/schema fix | **+1% reporting accuracy** | $1,200 orphan = 1% of deposit volume misattributed; schema fix restores payment-method reporting for fee analysis on DEP012 ($9 fee) | Missing signup record may indicate pipeline sync lag between CRM and core banking |

---

# 3. Data Alerting Design

## Architecture overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  PostgreSQL │────▶│  dbt / SQL   │────▶│  Airflow    │────▶│  PagerDuty / │
│  (4 tables) │     │  alert models│     │  scheduler  │     │  Slack / Email│
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐
                    │ alert_state  │     │  Datadog /  │
                    │ (dedup log)  │     │  dashboard  │
                    └──────────────┘     └─────────────┘
```

**State tracking:** Each alert writes to an `alert_state` table (`alert_name`, `entity_id`, `first_seen`, `last_seen`, `status`). A alert fires only on **new** violations or **status change** (open → resolved), preventing duplicate Slack noise across hourly runs.

---

## 3a. Alert Definitions

### Alert 1 — ORPHAN_DEPOSIT_DETECTED

| Field | Specification |
|-------|---------------|
| **Trigger** | `SELECT d.* FROM client_deposit d LEFT JOIN client_signup s ON d.client_id = s.client_id WHERE s.client_id IS NULL AND d.status = 'completed'` — fires when any completed deposit references a `client_id` absent from signup (currently DEP020/CL031). |
| **Frequency** | Every **15 minutes** — orphan deposits affect real-time reconciliation and must be caught before end-of-day settlement. |
| **Notified** | Treasury & Payments Operations team |
| **Method** | **PagerDuty** (high urgency) + Slack `#payments-alerts` — funds movement requires immediate human action. |
| **Tooling** | **Apache Airflow** DAG queries PostgreSQL replica via scheduled SQL; on match, Airflow triggers PagerDuty Events API v2. State table stores `deposit_id`; re-alert only if new orphan appears. |

---

### Alert 2 — KYC_GATE_BREACH

| Field | Specification |
|-------|---------------|
| **Trigger** | Deposit: `JOIN client_signup s ON d.client_id = s.client_id WHERE d.status = 'completed' AND s.kyc_status != 'approved'`. Trade: same join on `client_trades` where `trade_status = 'closed'`. Either match fires (currently CL012/DEP008). |
| **Frequency** | **Real-time** (CDC/stream) or every **5 minutes** — compliance violations have regulatory time sensitivity. |
| **Notified** | Compliance Officer + Onboarding Operations Lead |
| **Method** | **Email** (audit trail) + **SMS** to on-call Compliance — regulatory events need documented delivery. |
| **Tooling** | **dbt test** (`relationships` + custom `kyc_gate_test`) on hourly run; failures push to **Monte Carlo** or **Great Expectations** validation store. Compare current failure set to `alert_state`; notify only on new `(client_id, event_type)` pairs. |

---

### Alert 3 — INACTIVE_ACCOUNT_TRADE

| Field | Specification |
|-------|---------------|
| **Trigger** | `SELECT t.* FROM client_trades t JOIN client_profile p ON t.client_id = p.client_id WHERE p.account_status != 'active' AND t.trade_date >= CURRENT_DATE - INTERVAL '1 day'` — catches trades on inactive/suspended/pending accounts (currently CL008/TRD006 pattern). |
| **Frequency** | **Hourly** — trading control failures are urgent but not sub-minute; hourly balances noise vs coverage. |
| **Notified** | Risk Management & Trading Operations desk |
| **Method** | **Slack** `#risk-alerts` with trade details + **dashboard flag** in internal ops BI tool (Metabase/Looker). |
| **Tooling** | **Airflow** hourly SQL → if rows returned, post to Slack via webhook. `alert_state` keyed on `trade_id`; auto-resolve when trade is reversed and status updated. |

---

### Alert 4 — TRADE_WITHOUT_FUNDING

| Field | Specification |
|-------|---------------|
| **Trigger** | For each trade: `MIN(deposit_date WHERE status='completed')` per `client_id` must be ≤ `trade_date`. Fire when `trade_date < first_deposit_date` OR no completed deposit exists (currently CL007/TRD005 — trade on 2024-02-20, no deposit ever). |
| **Frequency** | **Daily at 06:00 UTC** (pre-market) — batch check sufficient for funding sequencing; catches overnight backfills. |
| **Notified** | Finance Reconciliation team + Client Funds team |
| **Method** | **Email** daily digest listing violating `trade_id`, `client_id`, `trade_date`, `pnl_usd` — non-urgent but must be tracked for audit. |
| **Tooling** | **Python script** in Airflow using pandas merge (same logic as `analysis.py` §8); output to CSV attachment via SendGrid. State table tracks `(trade_id)` to avoid re-sending resolved trades. |

---

### Alert 5 — PNL_RECONCILIATION_MISMATCH *(bonus)*

| Field | Specification |
|-------|---------------|
| **Trigger** | Trades where `open_price = close_price` AND `pnl_usd != 0` AND `trade_status = 'closed'` (TRD012: Gold, 5.0 lots, pnl $245 with zero price movement). |
| **Frequency** | **Daily** after trade ledger ETL completes |
| **Notified** | Back-office Settlements team |
| **Method** | Slack + ticket auto-created in Jira |
| **Tooling** | dbt model `int_trade_pnl_validation` → Airflow → Jira REST API. State keyed on `trade_id`. |

---

### Alert 6 — IMPOSSIBLE_CLIENT_AGE *(bonus)*

| Field | Specification |
|-------|---------------|
| **Trigger** | `client_profile.date_of_birth` yields age < 18 or > 100 at current date (CL025: DOB 1888-12-19, age ~136). |
| **Frequency** | **Weekly** (Monday 07:00, aligned with exec review) |
| **Notified** | KYC/Identity Verification team |
| **Method** | Dashboard flag + email weekly summary |
| **Tooling** | Scheduled SQL in **Metabase pulse**; compare against prior week's alert_state to surface only new/changed records. |

---

## Appendix: Validation Script Output Summary

```
Referential integrity: 1 orphan deposit (DEP020 → CL031)
Schema anomaly: DEP012 missing payment_method
KYC breach: DEP008 for CL012 (rejected)
Inactive trade: TRD006 for CL008
PnL mismatch: TRD012
Trade without deposit: TRD005 for CL007
Impossible age: CL025 (1888-12-19)
Overall funnel: 63.3% deposit rate, 60.0% trade rate
Social media: 0% conversion (5 signups)
```

---

*End of submission*
