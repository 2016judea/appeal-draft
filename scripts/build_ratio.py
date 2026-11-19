#!/usr/bin/env python3
"""The assessment ratio by county, city, ZIP and price tier: the county's value on a home / what it sold for.

  python3 scripts/build_ratio.py [--db PATH]      # closed_system.duckdb (read-only) -> data/ratio.json

Method (printed on /assessment-ratio/ from the same file, so the page and this agree):
- Value: the county's current roll per county (scripts/build.py VINTAGE), valued as of January 2 of
  its assessment year Y. Houses and townhouses only (scripts/build.py RES), no condos.
- Sales: recorded sales of $50,000+ from October 1 of Y-1 to June 30 of Y, the latest per home. The
  assessor's own study for the year-Y value used sales through September 30 of Y-1, so none of these
  sales went into the value they are tested against (assessment-ratio-study rule 2).
- Trim: ratio 0.5 to 2.0 (the band for judging an office; assessment-ratio-study rule 3).
- Statistics: median ratio, share valued ABOVE the sale price (ratio > 1), COD, PRD, PRB
  (IAAO Standard on Ratio Studies). PRB regresses on the proxy ½·(value / median ratio) + ½·price,
  never on price alone (rule 5). Areas with fewer than MIN_N sales are left out; every row prints n.
"""
import argparse, json, re, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LO, HI = 0.5, 2.0
MIN_N = 30


def sales_sql(county, vintage):
    res = B.RES[county].replace("useclass1", "ps.useclass1").replace("attrs->>", "ps.attrs->>")
    return f"""
    select s.sale_date, s.sale_value, ps.emv_total emv, ps.mkt_year ay,
      coalesce(a.city, nullif(ps.city,''), ps.attrs->>'POSTCOMM', ps.attrs->>'CTU_NAME') city,
      coalesce(nullif(ps.zip,''), ps.attrs->>'ZIP', ps.attrs->>'ZIP1', a.zip) zip
    from sale s join parcel_snapshot ps on ps.parcel_key = s.parcel_key and ps.vintage = '{vintage}' and ps.county = '{county}'
    left join (select parcel_key, any_value(city) city, any_value(zip) zip from address_index group by 1) a on a.parcel_key = s.parcel_key
    where {res} and ps.fin_sq_ft > 400 and ps.emv_total > 50000 and s.sale_value >= 50000
      and s.sale_date >= make_date(ps.mkt_year - 1, 10, 1) and s.sale_date < make_date(ps.mkt_year, 7, 1)
    qualify row_number() over (partition by s.parcel_key order by s.sale_date desc) = 1
    """


def stats(price, value):
    """IAAO statistics on one group of sales. price, value: numpy arrays, already trimmed."""
    r = value / price
    med = float(np.median(r))
    n = len(r)
    above = float(np.mean(r > 1.0))
    out = {"n": n, "median": round(med, 3), "above": round(above, 3),
           "above_moe": round(1.645 * (above * (1 - above) / n) ** 0.5, 3),  # 90% margin on the share
           "cod": round(100 * float(np.mean(np.abs(r - med))) / med, 1),
           "prd": round(float(np.mean(r)) / float(value.sum() / price.sum()), 3)}
    if n >= 100:
        proxy = 0.5 * value / med + 0.5 * price
        out["prb"] = round(float(np.polyfit(np.log2(proxy / np.median(proxy)), (r - med) / med, 1)[0]), 3)
    return out


def tidy_city(c):
    c = " ".join(w.capitalize() for w in str(c or "").strip().split())
    return re.sub(r"\bSt\.? (Paul|Francis|Anthony)\b", r"Saint \1", c)


def build(db):
    con = duckdb.connect(str(db), read_only=True)
    rows = []
    for county, vintage in B.VINTAGE.items():
        for sd, sv, emv, ay, city, z in con.sql(sales_sql(county, vintage)).fetchall():
            if LO <= emv / sv <= HI:
                rows.append((county, sd, float(sv), float(emv), int(ay), tidy_city(city), str(z or "")[:5]))
    if not rows:
        sys.exit("no sales: check the store")
    P = np.array([r[2] for r in rows]); V = np.array([r[3] for r in rows])
    groups = {"county": defaultdict(list), "city": defaultdict(list), "zip": defaultdict(list)}
    for i, r in enumerate(rows):
        groups["county"][r[0]].append(i)
        if r[5]:
            groups["city"][(r[0], r[5])].append(i)
        if len(r[6]) == 5:
            groups["zip"][r[6]].append(i)
    out = {"built": date.today().isoformat(), "trim": [LO, HI], "min_n": MIN_N, "all": stats(P, V), "counties": {}, "cities": [], "zips": [], "tiers": {}}
    for c, idx in groups["county"].items():
        ix = np.array(idx)
        ay = rows[idx[0]][4]
        s = stats(P[ix], V[ix])
        s.update({"name": B.COUNTY_NAME[c], "assessment_year": ay, "valued_as_of": f"{ay}-01-02",
                  "sales_from": f"{ay - 1}-10-01", "sales_to": f"{ay}-06-30", "minneapolis_only": c == "hennepin",
                  "last_sale": str(max(rows[i][1] for i in idx))})
        out["counties"][c] = s
        # price tiers by the PRB proxy (a tier by sale price alone puts every low-selling home in the
        # bottom tier and fakes regressivity: assessment-ratio-study rule 5)
        r = V[ix] / P[ix]
        proxy = 0.5 * V[ix] / np.median(r) + 0.5 * P[ix]
        q = np.quantile(proxy, [0.25, 0.5, 0.75])
        tiers = []
        for name, m in (("lowest-priced quarter", proxy <= q[0]), ("second quarter", (proxy > q[0]) & (proxy <= q[1])),
                        ("third quarter", (proxy > q[1]) & (proxy <= q[2])), ("highest-priced quarter", proxy > q[2])):
            t = stats(P[ix][m], V[ix][m]); t.pop("prd", None); t.pop("prb", None)
            t.update({"tier": name, "price_median": int(np.median(P[ix][m]))})
            tiers.append(t)
        out["tiers"][c] = tiers
    for (c, city), idx in groups["city"].items():
        if len(idx) >= MIN_N:
            ix = np.array(idx)
            out["cities"].append({"county": c, "city": city, **stats(P[ix], V[ix])})
    zip_city = defaultdict(lambda: defaultdict(int))
    for r in rows:
        zip_city[r[6]][r[5]] += 1
    for z, idx in groups["zip"].items():
        if len(idx) >= MIN_N:
            ix = np.array(idx)
            top = sorted(zip_city[z].items(), key=lambda kv: -kv[1])
            out["zips"].append({"zip": z, "county": rows[idx[0]][0], "city": top[0][0] if top else "", **stats(P[ix], V[ix])})
    out["cities"].sort(key=lambda x: -x["above"])
    out["zips"].sort(key=lambda x: -x["above"])
    (ROOT / "data/ratio.json").write_text(json.dumps(out, indent=1) + "\n")
    a = out["all"]
    print(f"{a['n']:,} sales: median {a['median']}, above {a['above']:.0%}; {len(out['cities'])} cities, {len(out['zips'])} zips")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(B.DB))
    build(Path(ap.parse_args().db))
