#!/usr/bin/env python3
"""Comprehensive data quality and anomaly analysis for deriv DA assessment."""
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DATA_DIR = Path(__file__).parent / "data"

def load(name):
    with open(DATA_DIR / name) as f:
        return json.load(f)

signup = load("client_signup.json")
profile = load("client_profile.json")
deposits = load("client_deposit.json")
trades = load("client_trades.json")

signup_ids = {r["client_id"] for r in signup}
profile_ids = {r["client_id"] for r in profile}
deposit_ids = {r["client_id"] for r in deposits}
trade_ids = {r["client_id"] for r in trades}

signup_by_id = {r["client_id"]: r for r in signup}
profile_by_id = {r["client_id"]: r for r in profile}

print("=" * 70)
print("1. REFERENTIAL INTEGRITY")
print("=" * 70)
orphan_deposits = [d for d in deposits if d["client_id"] not in signup_ids]
orphan_trades = [t for t in trades if t["client_id"] not in signup_ids]
missing_profile = signup_ids - profile_ids
missing_signup_profile = profile_ids - signup_ids
print(f"Deposits with unknown client_id: {orphan_deposits}")
print(f"Trades with unknown client_id: {orphan_trades}")
print(f"Signup without profile: {sorted(missing_profile)}")
print(f"Profile without signup: {sorted(missing_signup_profile)}")

print("\n" + "=" * 70)
print("2. SCHEMA / FIELD ANOMALIES IN DEPOSITS")
print("=" * 70)
for d in deposits:
    keys = set(d.keys())
    if "payment_method" not in d:
        print(f"Missing payment_method: {d['deposit_id']} keys={keys}")
    extra = keys - {"deposit_id","client_id","deposit_date","amount_usd","payment_method",
                    "currency_original","exchange_rate","status","processing_days","fee_usd"}
    if extra:
        print(f"{d['deposit_id']} extra/wrong keys: {extra} -> {d}")

print("\n" + "=" * 70)
print("3. KYC / COMPLIANCE VIOLATIONS")
print("=" * 70)
for d in deposits:
    cid = d["client_id"]
    if cid in signup_by_id:
        kyc = signup_by_id[cid]["kyc_status"]
        if kyc != "approved":
            print(f"Deposit {d['deposit_id']} for {cid} with kyc_status={kyc}, amount={d['amount_usd']}")

for t in trades:
    cid = t["client_id"]
    if cid in signup_by_id:
        kyc = signup_by_id[cid]["kyc_status"]
        if kyc != "approved":
            print(f"Trade {t['trade_id']} for {cid} with kyc_status={kyc}")

print("\n" + "=" * 70)
print("4. ACCOUNT STATUS vs TRADING")
print("=" * 70)
for t in trades:
    cid = t["client_id"]
    if cid in profile_by_id:
        status = profile_by_id[cid]["account_status"]
        if status != "active":
            print(f"Trade {t['trade_id']} on {t['trade_date']} for {cid} account_status={status}")

print("\n" + "=" * 70)
print("5. PNL vs PRICE CONSISTENCY (Gold TRD012)")
print("=" * 70)
for t in trades:
    if t["instrument"] == "Gold" and t["open_price"] == t["close_price"]:
        print(f"{t['trade_id']}: open=close={t['open_price']}, pnl={t['pnl_usd']}, vol={t['volume_lots']}, dir={t['direction']}")

print("\n" + "=" * 70)
print("6. DOB / AGE ANOMALIES")
print("=" * 70)
today = datetime(2024, 11, 23)
for p in profile:
    dob = datetime.strptime(p["date_of_birth"], "%Y-%m-%d")
    age = (today - dob).days / 365.25
    if age > 100 or age < 18:
        print(f"{p['client_id']} DOB={p['date_of_birth']} age~{age:.0f}")

print("\n" + "=" * 70)
print("7. TIMING: DEPOSIT BEFORE SIGNUP / TRADE BEFORE DEPOSIT")
print("=" * 70)
for d in deposits:
    cid = d["client_id"]
    if cid in signup_by_id:
        sd = signup_by_id[cid]["signup_date"]
        if d["deposit_date"] < sd:
            print(f"Deposit {d['deposit_id']} date {d['deposit_date']} before signup {sd}")

client_first_deposit = {}
for d in sorted(deposits, key=lambda x: x["deposit_date"]):
    cid = d["client_id"]
    if cid not in client_first_deposit and d["status"] == "completed":
        client_first_deposit[cid] = d["deposit_date"]

for t in trades:
    cid = t["client_id"]
    if cid in client_first_deposit and t["trade_date"] < client_first_deposit[cid]:
        print(f"Trade {t['trade_id']} {t['trade_date']} before first deposit {client_first_deposit[cid]}")

print("\n" + "=" * 70)
print("8. CLIENTS WITH NO DEPOSIT BUT TRADES")
print("=" * 70)
for t in trades:
    cid = t["client_id"]
    if cid not in client_first_deposit and cid in signup_ids:
        print(f"{t['trade_id']} {cid} traded without completed deposit")

print("\n" + "=" * 70)
print("9. FUNNEL METRICS BY REFERRAL SOURCE")
print("=" * 70)
funnel = defaultdict(lambda: {"signups": 0, "deposited": 0, "traded": 0, "deposit_usd": 0})
deposited_clients = set(d["client_id"] for d in deposits if d["status"]=="completed" and d["client_id"] in signup_ids)
traded_clients = set(t["client_id"] for t in trades if t["client_id"] in signup_ids)

for s in signup:
    src = s["referral_source"]
    funnel[src]["signups"] += 1
    cid = s["client_id"]
    if cid in deposited_clients:
        funnel[src]["deposited"] += 1
    if cid in traded_clients:
        funnel[src]["traded"] += 1

for d in deposits:
    if d["client_id"] in signup_by_id and d["status"] == "completed":
        funnel[signup_by_id[d["client_id"]]["referral_source"]]["deposit_usd"] += d["amount_usd"]

for src, m in sorted(funnel.items()):
    dep_rate = m["deposited"]/m["signups"]*100 if m["signups"] else 0
    trade_rate = m["traded"]/m["signups"]*100 if m["signups"] else 0
    avg_dep = m["deposit_usd"]/m["deposited"] if m["deposited"] else 0
    print(f"{src:15} signups={m['signups']:2} deposit_rate={dep_rate:5.1f}% trade_rate={trade_rate:5.1f}% avg_deposit=${avg_dep:,.0f}")

print("\n" + "=" * 70)
print("10. OVERALL FUNNEL")
print("=" * 70)
total_signups = len(signup)
approved = sum(1 for s in signup if s["kyc_status"]=="approved")
with_deposit = len(deposited_clients & signup_ids)
with_trade = len(traded_clients & signup_ids)
no_deposit = signup_ids - deposited_clients
print(f"Signups: {total_signups}, KYC approved: {approved}")
print(f"Ever deposited: {with_deposit} ({with_deposit/total_signups*100:.1f}%)")
print(f"Ever traded: {with_trade} ({with_trade/total_signups*100:.1f}%)")
print(f"Signed up, never deposited: {len(no_deposit)} clients -> {sorted(no_deposit)}")

print("\n" + "=" * 70)
print("11. PROMO CODE EFFECTIVENESS")
print("=" * 70)
promo = defaultdict(lambda: {"signups": 0, "deposited": 0})
for s in signup:
    code = s["promo_code"] or "none"
    promo[code]["signups"] += 1
    if s["client_id"] in deposited_clients:
        promo[code]["deposited"] += 1
for code, m in sorted(promo.items()):
    print(f"{code:10} signups={m['signups']} deposit_conv={m['deposited']/m['signups']*100:.1f}%")

print("\n" + "=" * 70)
print("12. NULL RATES")
print("=" * 70)
for name, rows in [("signup", signup), ("profile", profile), ("deposits", deposits), ("trades", trades)]:
    if not rows:
        continue
    fields = set().union(*(r.keys() for r in rows))
    print(f"\n{name}:")
    for field in sorted(fields):
        nulls = sum(1 for r in rows if field not in r or r[field] is None)
        print(f"  {field}: {nulls}/{len(rows)} ({nulls/len(rows)*100:.1f}%)")

print("\n" + "=" * 70)
print("13. INACTIVE BUT RECENT LOGIN / TRADE")
print("=" * 70)
for p in profile:
    if p["account_status"] == "inactive":
        cid = p["client_id"]
        trades_c = [t for t in trades if t["client_id"]==cid]
        print(f"{cid} inactive, last_login={p['last_login_date']}, trades={[(t['trade_id'],t['trade_date']) for t in trades_c]}")

print("\n" + "=" * 70)
print("14. VIP / HIGH VALUE WITHOUT RELATIONSHIP MANAGER FOLLOW-UP")
print("=" * 70)
for s in signup:
    if s["account_type"] == "vip":
        cid = s["client_id"]
        p = profile_by_id.get(cid, {})
        print(f"{cid} vip balance={p.get('account_balance_usd')} manager={s['assigned_manager']} last_login={p.get('last_login_date')}")
