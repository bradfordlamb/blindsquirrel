#!/usr/bin/env python3
"""Refresh plans.json from Power to Choose (PUCT).

Pulls every plan for the ZIP codes below, keeps the fields the site uses,
merges in hand-verified EFL pricing from data/verified.json, and writes
plans.json + meta.json at the repo root.

Usage:  python3 scripts/update_plans.py
"""
import json, datetime, pathlib, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://www.powertochoose.org/en-us/service/v1/"
# One ZIP per competitive utility area. 77584 (Pearland) returns both CenterPoint and TNMP.
ZIPS = ["77584",   # CenterPoint + TNMP
        "75201",   # Oncor (Dallas)
        "78401",   # AEP Texas Central (Corpus Christi)
        "79601",   # AEP Texas North (Abilene)
        "79401"]   # Lubbock Power & Light

def fetch(zip_code):
    body = json.dumps({
        "method": "plans", "zip_code": zip_code, "estimated_use": 1000,
        "include_details": True, "min_usage_plan": "", "plan_type": "1,0",
        "renewable": "", "timeofuse": "", "company": "", "price_from": "",
        "price_to": "", "plan_mo_from": "", "plan_mo_to": "", "prepaid": "",
    }).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (BlindSquirrelEnergy plan refresh)",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8-sig"))

def tdu_code(name):
    n = name.upper()
    if "CENTERPOINT" in n: return "CNP"
    if "TEXAS-NEW MEXICO" in n: return "TNMP"
    if "ONCOR" in n: return "ONCOR"
    if "AEP" in n and "NORTH" in n: return "AEPN"
    if "AEP" in n: return "AEPC"
    if "LUBBOCK" in n: return "LPL"
    return n[:12]

def slim(p):
    def num(x):
        try: return float(x)
        except (TypeError, ValueError): return None
    ren = "".join(ch for ch in (p.get("renewable_energy_description") or "") if ch.isdigit())
    return {
        "id": p["plan_id"], "tdu": tdu_code(p.get("company_tdu_name", "")),
        "co": (p.get("company_name") or "").strip(), "plan": (p.get("plan_name") or "").strip(),
        "fixed": p.get("rate_type") == "Fixed", "term": p.get("term_value"),
        "p": [num(p.get("price_kwh500")), num(p.get("price_kwh1000")), num(p.get("price_kwh2000"))],
        "tou": bool(p.get("timeofuse")), "minU": bool(p.get("minimum_usage")),
        "newc": bool(p.get("new_customer")),
        "etf": (p.get("pricing_details") or "").replace("Cancellation Fee:", "").strip(),
        "ren": int(ren[:3]) if ren else 0,
        "efl": p.get("fact_sheet") or "", "go": p.get("go_to_plan") or p.get("website") or "",
    }

CNP_TDU = (4.90, 6.5611)  # $/month, cents/kWh — CenterPoint delivery charges

def verified_matches(r, v):
    """True if the verified EFL details still reproduce today's average prices."""
    base_tdu, kwh_tdu = CNP_TDU
    for k, avg in zip((500, 1000, 2000), r["p"]):
        if v["kind"] == "flat":
            cost = k * (v["e"] + kwh_tdu) / 100 + v["base"] + base_tdu
            if v.get("credit") and k >= v["credit"][0]:
                cost -= v["credit"][1]
        elif v["kind"] == "tou":  # EFL averages assume 35% of use in the free hours
            cost = v["base"] + base_tdu + k * kwh_tdu / 100 + k * 0.65 * v["day"] / 100 + k * 0.35 * v["night"] / 100
        else:
            return False
        if abs(cost / k * 100 - avg) > 0.11:
            return False
    return True

def main():
    verified = json.loads((ROOT / "data" / "verified.json").read_text())
    seen, rows, stale = set(), [], []
    for z in ZIPS:
        for p in fetch(z):
            if p.get("prepaid") or p["plan_id"] in seen: continue
            r = slim(p)
            if None in r["p"]: continue
            seen.add(p["plan_id"])
            v = verified.get(str(r["id"]))
            if v and r["tdu"] == "CNP":
                if verified_matches(r, v):
                    r["v"] = v
                else:
                    stale.append(f'{r["co"]} {r["plan"]} ({r["id"]})')
            rows.append(r)
    if len(rows) < 300:
        raise SystemExit(f"Only {len(rows)} plans came back; not overwriting plans.json")
    (ROOT / "plans.json").write_text("[\n" + ",\n".join(json.dumps(r, separators=(",", ":")) for r in rows) + "\n]\n")
    today = datetime.date.today()
    (ROOT / "meta.json").write_text(json.dumps({"updated": f"{today:%B} {today.day}, {today.year}", "zip": ",".join(ZIPS)}) + "\n")
    print(f"Wrote {len(rows)} plans")
    if stale:
        print("::warning::Verified pricing no longer matches Power to Choose for: " + "; ".join(stale)
              + ". Using estimates; re-check their EFLs and update data/verified.json.")

if __name__ == "__main__":
    main()
