#!/usr/bin/env python3
"""Round 1 ledger + drafts + /for/ pages from outreach/round1/{candidates,verified}.json. Sends nothing.

  python3 scripts/outreach_drafts.py

A/B (one variable, pooled across the seven shelf products): A states the price in the email,
B leaves it to the page. Alternated within each segment. The variant rides in
site/public/data/for/<token>.json, never in the URL.
"""
import csv, json, secrets, subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R1 = ROOT / "outreach/round1"
FOR = ROOT / "site/public/data/for"
OFFER = json.loads((ROOT / "site/offer.json").read_text())
SITE, PRICE = OFFER["site"], OFFER["price_usd"]
SUBSTACK = "https://randomaidan.substack.com/p/business-prototypes"
TODAY = date.today().isoformat()
COUNTY = {"ramsey": "Ramsey", "anoka": "Anoka", "dakota": "Dakota", "scott": "Scott", "washington": "Washington", "hennepin": "Hennepin"}
COLS = ["token", "variant", "segment", "company", "name", "email", "email_source", "email_source_date", "own_record", "status",
        "hold_reason", "drafted_on", "sent_on", "reply_kind", "reply_on", "for_url", "pk", "zip"]
APPEAL_SERVICES = [  # read 2026-10-19 (web search); no home of their own in the data -> hold
    ("Fredrikson & Byron (property tax group)", "https://www.fredlaw.com/lets-talk-about-tax/minnesota-property-tax-appeals-what-property-owners-need-to-know"),
    ("AppealDesk", "https://www.appealdesk.com/compare/best-minnesota-property-tax-appeal-services"),
    ("Ownwell", "https://www.appealdesk.com/compare/best-minnesota-property-tax-appeal-services"),
    ("O'Connor & Associates", "https://www.appealdesk.com/compare/best-minnesota-property-tax-appeal-services"),
    ("Meridian Property Tax Advisors", "https://jobs.ctbar.org/profile/meridian-property-tax-advisors/2041754/"),
]

tidy = lambda s: " ".join(w.upper() if w.upper() in ("LLC", "LP", "LLP") else w.capitalize() for w in s.split())
money = lambda n: f"${int(round(n)):,}"

def mx_ok(email):
    dom = email.split("@")[1]
    try:
        return bool(subprocess.run(["dig", "+short", "MX", dom], capture_output=True, text=True, timeout=10).stdout.strip())
    except Exception:
        return False

def shard(addr):
    return addr[0] if addr[:1].isdigit() else "0"

def pick():
    cand = json.load(open(R1 / "candidates.json"))
    ver = {r["email"]: r for r in json.load(open(R1 / "verified.json"))}
    def src(r):
        v = ver.get(r["email"])
        if v and v["verified"]:
            return v["verified_url"], TODAY
        return "Overture Maps places 2026-08-19.0 (pulled 2026-08-20); domain has MX", "2026-08-20"
    def rank(r):
        v = ver.get(r["email"], {})
        below = bool(r.get("list_price") and r["list_price"] < r["emv"] * 0.98)
        return (not v.get("verified"), not below, -(r["gap"] or -9))
    agents, seen_co = [], {}
    for r in sorted(cand["agent"], key=rank):
        if len(agents) >= 40:
            break
        co = r["company"].split(" - ")[0].lower()
        if seen_co.get(co, 0) >= 4:          # no more than 4 from one brokerage: a segment, not one office
            continue
        if not (ver.get(r["email"], {}).get("verified") or mx_ok(r["email"])):
            continue
        seen_co[co] = seen_co.get(co, 0) + 1
        agents.append({**r, "email_source": src(r)[0], "email_source_date": src(r)[1]})
    lands, seen_e = [], set()
    for r in cand["landlord"]:
        if r["email"] in seen_e or not (ver.get(r["email"], {}).get("verified") or mx_ok(r["email"])):
            continue
        seen_e.add(r["email"])
        lands.append({**r, "email_source": src(r)[0], "email_source_date": src(r)[1]})
    return agents, lands

def body(r, variant, link):
    c = COUNTY[r["pk"].split(":")[0]]
    if r["segment"] == "agent":
        when = date.fromisoformat(r["list_date"]).strftime("%B %-d") if r.get("list_date") else "this year"
        l1 = f"You listed {r['addr']}, {r['city']} at {money(r['list_price'])} on {when}. {c} County has it at {money(r['emv'])} on the {r['ay']} roll."
        l2 = (f"Recorded sales of homes like it nearby since July 2024 put it at {money(r['target'])}. "
              f"Whoever buys it gets the county's number on their next notice, and the window to argue it opens in March 2027.")
        thing = "comps and the drafted appeal for it, with the county's form fields and dates,"
    else:
        own = f"{tidy(r['owner_name'])} owns {r['n_homes']} homes on the county roll"
        l1 = f"{own}. One is {r['addr']}, {r['city']}, which {c} County has at {money(r['emv'])} for {r['ay']}."
        if r["gap"] >= 0.03:
            l2 = f"Recorded sales of homes like it within two miles put it at {money(r['target'])}. The county is {round(r['gap']*100)}% above them."
        else:
            l2 = f"Recorded sales of homes like it within two miles put it at {money(r['target'])}, so the county is about right on that one."
        if r["n_argue"] > 1 or (r["n_argue"] == 1 and r["gap"] < 0.10):
            l2 += f" {r['n_argue']} of your {r['n_scored']} homes we could score sit 10% or more above their comparable sales."
        l2 += " The next appeal window opens with the March 2027 notices."
        thing = "comps and the drafted appeal for a home, with the county's form fields and dates,"
    l3 = f"That home is open to poke at, no login: {link}"
    if variant == "A":
        l3 += f" The full {thing} are ${PRICE}, once."
    return "\n\n".join([l1, l2, l3, f"How this gets built: {SUBSTACK}", "Aidan\nBrick & Mortar"])

def main():
    agents, lands = pick()
    FOR.mkdir(parents=True, exist_ok=True)
    (R1 / "drafts").mkdir(parents=True, exist_ok=True)
    old = {}
    if (R1 / "ledger.csv").exists():
        old = {r["email"]: r for r in csv.DictReader(open(R1 / "ledger.csv")) if r["email"]}
    rows = []
    for seg in (agents, lands):
        for i, r in enumerate(seg):
            prev = old.get(r["email"], {})
            tok = prev.get("token") or secrets.token_hex(5)
            var = prev.get("variant") or "AB"[i % 2]
            link = f"{SITE}/for/{tok}/"
            (FOR / f"{tok}.json").write_text(json.dumps({"zip": r["zip"], "pk": r["pk"], "shard": shard(r["addr"]), "variant": var}))
            company = r["company"] if r["segment"] == "agent" else r["owner_name"]
            text = f"To: {r['email']}\nSubject: bricks / {r['company'] if r['segment'] == 'agent' else tidy(r['owner_name'])}\n\n" + body(r, var, link) + "\n"
            (R1 / "drafts" / f"{tok}.txt").write_text(text)
            own = (f"listing {r['addr']}, {r['city']} at {money(r['list_price'])} ({r.get('listing_url','')})" if r["segment"] == "agent"
                   else f"owner of {r['n_homes']} homes incl. {r['addr']}, {r['city']} (assessor owner_name)")
            rows.append({"token": tok, "variant": var, "segment": r["segment"], "company": company, "name": r.get("name", ""),
                         "email": r["email"], "email_source": r["email_source"], "email_source_date": r["email_source_date"],
                         "own_record": own, "status": "drafted", "hold_reason": "", "drafted_on": TODAY, "sent_on": "",
                         "reply_kind": "", "reply_on": "", "for_url": link, "pk": r["pk"], "zip": r["zip"]})
    for co, url in APPEAL_SERVICES:
        rows.append({**{k: "" for k in COLS}, "segment": "appeal_service", "company": co, "status": "hold", "drafted_on": TODAY,
                     "email_source": url, "email_source_date": TODAY,
                     "hold_reason": "no home of their own in the data to open on; and no verified named email"})
    with open(R1 / "ledger.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
    from collections import Counter
    print(Counter((r["segment"], r["status"], r["variant"]) for r in rows))

if __name__ == "__main__":
    main()
