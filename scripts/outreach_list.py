#!/usr/bin/env python3
"""Draft round 1's recipient list: every person opens on a home of THEIR OWN in the appeal data.

  python3 scripts/outreach_list.py      # writes outreach/round1/candidates.json (gitignored)

Segments (README "## Distribution"):
  agent     a Twin Cities agent with a live listing (msp-house-index realtor pull, advertiser name)
            whose Overture place carries a personal email; own row = that listing's parcel.
  landlord  a company that owns 2-40 non-homestead houses in our counties (assessor owner_name),
            matched by name to an Overture property-management / investment place with an email;
            own row = the house of theirs the county values highest above its comps.
  appeal_service  MN firms that file residential appeals; no home of their own in the data, so
            every row is status=hold (scripts note why). Filled by hand into candidates.json.
Dedupe against ~/Desktop/outreach-ledger/outreach.duckdb `contacted` is done here, not later.
Nothing is sent.
"""
import json, re, sys
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
ZIP = ROOT / "site/public/data/zip"
OUT = ROOT / "outreach/round1"
MSP = Path.home() / "Desktop/msp-house-index/data/listings_raw.jsonl"
DB = Path.home() / "Desktop/bricks/data/closed_system.duckdb"
LEDGER = Path.home() / "Desktop/outreach-ledger/outreach.duckdb"
F = dict(pk=0, addr=1, city=2, sf=3, yb=4, emv=5, prior=6, tax=7, hs=8, ay=9, target=10, ppsf=11, n=12, first=13)

_shards = {}
def shard(z, d):
    k = (z, d)
    if k not in _shards:
        p = ZIP / f"{z}-{d}.json"
        _shards[k] = json.loads(p.read_text()) if p.exists() else None
    return _shards[k]

def norm_addr(s):
    s = re.sub(r"[.,#]", " ", s.lower())
    rep = {"avenue": "ave", "street": "st", "road": "rd", "drive": "dr", "lane": "ln", "court": "ct", "place": "pl",
           "boulevard": "blvd", "circle": "cir", "trail": "trl", "terrace": "ter", "parkway": "pkwy", "north": "n", "south": "s",
           "east": "e", "west": "w", "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw"}
    return " ".join(rep.get(w, w) for w in s.split())

def find_home(line, z):
    a = norm_addr(line)
    d = shard(z, a[0] if a[:1].isdigit() else "0")
    if not d:
        return None, None
    for h in d["homes"]:
        if norm_addr(h[F["addr"]]) == a:
            return h, d
    return None, d

def gap(h):
    return h[F["emv"]] / h[F["target"]] - 1 if h[F["target"]] else None

def contacted():
    con = duckdb.connect(str(LEDGER), read_only=True)
    return {r[0] for r in con.sql("select recipient_key from contacted").fetchall() if r[0]}

def overture(cats):
    con = duckdb.connect(str(DB), read_only=True)
    q = f"""select attrs->>'name', attrs->>'emails', attrs->>'websites', attrs->>'city', attrs->>'category' from record
            where layer='overture_places' and (attrs->>'category') in ({",".join(f"'{c}'" for c in cats)}) and (attrs->>'emails') <> 'null'"""
    out = []
    for name, em, web, city, cat in con.sql(q).fetchall():
        ems = json.loads(em or "[]"); webs = json.loads(web or "[]") if web and web != "null" else []
        if ems:
            out.append({"name": name, "email": ems[0].lower(), "website": webs[0] if webs else "", "city": city, "category": cat})
    return out

def agents(seen):
    ov = overture(["real_estate_agent"])
    by_person = defaultdict(list)
    for o in ov:
        person = re.split(r"\s+[-|,–]\s+|\s+(?:Realtor|REALTOR|Real Estate)", o["name"])[0].strip()
        if len(person.split()) in (2, 3) and all(w[:1].isupper() for w in person.split()):
            first, last = person.split()[0].lower(), person.split()[-1].lower()
            local = o["email"].split("@")[0]
            if first in local or last in local or (first[0] + last) in local:
                by_person[person.lower()].append({**o, "person": person})
    rows = []
    for line in MSP.read_text().splitlines():
        L = json.loads(line)
        for adv in L.get("advertisers") or []:
            nm = (adv.get("name") or "").strip().lower()
            if nm in by_person and L.get("status") == "for_sale":
                loc = L["location"]["address"]
                h, _ = find_home(loc["line"], loc.get("postal_code", "")[:5])
                if h and h[F["target"]]:
                    o = by_person[nm][0]
                    rows.append({"segment": "agent", "name": o["person"], "company": (adv.get("office") or {}).get("name") or o["name"],
                                 "email": o["email"], "website": o["website"], "zip": loc["postal_code"][:5], "pk": h[F["pk"]],
                                 "addr": h[F["addr"]], "city": h[F["city"]], "list_price": L.get("list_price"), "list_date": (L.get("list_date") or "")[:10],
                                 "listing_url": "https://www.realtor.com/realestateandhomes-detail/" + (L.get("href") or "").split("/")[-1] if L.get("href") else "",
                                 "emv": h[F["emv"]], "target": h[F["target"]], "gap": gap(h), "ay": h[F["ay"]]})
    # one row per agent: the listing where the county is furthest above the comps
    best = {}
    for r in rows:
        if r["email"] in seen:
            continue
        if r["email"] not in best or (r["gap"] or -9) > (best[r["email"]]["gap"] or -9):
            best[r["email"]] = r
    return sorted(best.values(), key=lambda r: -(r["gap"] or -9))

STRIP = re.compile(r"\b(llc|l l c|inc|co|corp|corporation|company|ltd|lp|llp|the|of|mn|minnesota|group)\b")
def key(s):
    return " ".join(STRIP.sub(" ", re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())).split())

def landlords(seen):
    ov = [o for o in overture(["property_management", "real_estate_investment", "real_estate_service"])]
    ovk = {}
    for o in ov:
        k = key(o["name"])
        if len(k) >= 6:
            ovk.setdefault(k, o)
    con = duckdb.connect(str(DB), read_only=True)
    owners = con.sql("""select owner_name, list(parcel_key) pks, count(*) n from parcel_snapshot
        where vintage in ('metrogis_current','minneapolis_assessor_2025') and county in ('ramsey','anoka','dakota','scott','washington','hennepin')
          and coalesce(homestead,'') not ilike 'y%' and owner_name is not null
          and regexp_matches(upper(owner_name), '(LLC|INC|PROPERT|HOMES|RENTAL|MANAGEMENT|INVEST|HOLDINGS|REALTY)')
        group by 1 having count(*) between 2 and 40""").fetchall()
    pkz = {}
    for z in ZIP.glob("*.json"):
        d = json.loads(z.read_text())
        for h in d["homes"]:
            pkz[h[F["pk"]]] = (h, d["zip"])
    out = []
    for owner, pks, n in owners:
        o = ovk.get(key(owner))
        if not o or o["email"] in seen:
            continue
        homes = [pkz[p] for p in pks if p in pkz and pkz[p][0][F["target"]]]
        if not homes:
            continue
        n_argue = sum(1 for t in homes if gap(t[0]) >= 0.10)
        h, z = max(homes, key=lambda t: gap(t[0]))
        out.append({"segment": "landlord", "name": "", "company": o["name"], "owner_name": owner, "n_homes": n, "n_scored": len(homes), "n_argue": n_argue, "email": o["email"],
                    "website": o["website"], "zip": z, "pk": h[F["pk"]], "addr": h[F["addr"]], "city": h[F["city"]],
                    "emv": h[F["emv"]], "target": h[F["target"]], "gap": gap(h), "ay": h[F["ay"]]})
    return sorted(out, key=lambda r: -r["gap"])

if __name__ == "__main__":
    seen = contacted()
    A, Lr = agents(seen), landlords(seen)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "candidates.json").write_text(json.dumps({"agent": A, "landlord": Lr}, indent=1))
    print(f"contacted keys {len(seen):,}; agents {len(A)}; landlords {len(Lr)}")
