# Deriv Data Analyst Assessment — Submission

## Overview

This repo contains my analysis of Deriv's client signup, profile, deposit, and trade data, covering three parts: anomaly detection, executive dashboard design, and automated alerting design. Full write-up with all prompts used is in `Deriv_DA_Assessment_Submission_Final.pdf`.

## Repo Structure

```
.
├── analysis.py                                   # Core analysis script: joins, integrity checks, funnel metrics
├── funnel_channel_chart.png                       # Funnel + referral-source conversion chart (dashboard sample)
├── Deriv_DA_Assessment_Submission_Final.pdf        # Final submission (all 3 sections + prompts)
└── README.md
```

## Methodology

`analysis.py` loads all four JSON tables and joins them on `client_id` to check:
- Referential integrity (orphan records across tables)
- Schema consistency (field-name drift between records)
- Compliance gate violations (deposits/trades against non-approved KYC status)
- Account-status vs. trading-activity conflicts
- PnL vs. price-movement consistency
- Implausible dates of birth
- Trade-before-funding sequencing
- Funnel conversion by `referral_source` and `promo_code`

## Key Findings (summary)

- **1 orphan deposit** (`DEP020` → non-existent client `CL031`)
- **1 KYC-gate breach** — a completed deposit for a client with `kyc_status = rejected`
- **1 inactive-account trade** — a trade executed 8 months after the account went inactive
- **Funnel:** 30 signups → 93.3% KYC approved → 63.3% deposited → 60.0% traded
- **Channel insight:** `social_media` referrals converted at 0% (5 signups, $0 deposited) while `referral` converted at 83.3% with an average deposit of $19,720 — an 8x value gap that isn't visible from signup volume alone

Full detail, reasoning, and business recommendations for each finding are in the PDF.

## How to Run

```bash
python3 analysis.py
```

Requires `pandas` (see script header for full dependency list). Outputs the population stats, anomaly detail, and funnel tables referenced in the submission.

## Notes for Reviewers

- All AI prompts used during this analysis (data exploration, dashboard design, alerting design) are documented in full at the top of the PDF, per the assessment's disclosure requirement.
- The `[STAKEHOLDER_ROLE]` / `[BUSINESS_FOCUS_AREA]` placeholders in Question 2 were filled in as **Head of Growth** / **signup → first-deposit → first-trade conversion funnel**, as noted in the PDF.
