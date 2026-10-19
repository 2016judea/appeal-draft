#!/usr/bin/env python3
"""Build the appeal draft's data from closed_system.duckdb (read-only).

  python3 scripts/build.py [--db PATH] [--out DIR] [--county ramsey,...] [--sample N]

Writes
  site/public/data/zip/<zip>.json       the FREE slice: one row per home (assessor value, prior value,
                                 tax, sqft, built, the comp-based target, ONE comp) + the zip's
                                 sale $/sqft median
  private/bundle/comps/<zip>.json.gz   the PAID slice: every home's full comp set, as indices into
                                 the zip file's sales table; served only by /api/data
  site/public/data/meta.json            counts, build date, spread (every number the page quotes)
  site/public/data/example.json         the home the page opens on

The rule for what counts as a comp lives in scripts/model.py; DATA_MODEL.md says why.
"""
import argparse, gzip, json, sys, time
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model as M  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DB = Path.home() / "Desktop/bricks/data/closed_system.duckdb"

# Which snapshot vintage is "now" per county, and which use classes are a house or townhouse.
VINTAGE = {"ramsey": "metrogis_current", "anoka": "metrogis_current", "dakota": "metrogis_current",
           "scott": "metrogis_current", "washington": "metrogis_current", "hennepin": "minneapolis_assessor_2025"}
RES = {
    "ramsey": "useclass1 in ('1A/1B/4BB RESIDENTIAL SINGLE UNIT','1A/1B/4B1 RESIDENTIAL 1-3 UNITS')",
    "anoka": "useclass1 in ('1a RESIDENTIAL SINGLE UNIT','RESIDENTIAL 1 TO 3 UNITS')",
    "dakota": "useclass1 in ('Residential','Residential-townhouse')",
    "scott": "useclass1 like '201 %RESIDENTIAL SINGLE UNIT'",
    "washington": "useclass1 = '100' and coalesce(attrs->>'DWELL_TYPE','') not ilike '%condo%'",
    "hennepin": "useclass1 in ('RESIDENTIAL 1 UNIT','RESIDENTIAL 2 UNITS','RESIDENTIAL 3 UNITS')",
}
COUNTY_NAME = {"ramsey": "Ramsey", "anoka": "Anoka", "dakota": "Dakota", "scott": "Scott", "washington": "Washington", "hennepin": "Hennepin"}


def homes_sql(county, vintage):
    return f"""
    with cur as (
      select s.parcel_key, s.pin, s.county, s.mkt_year, s.emv_total emv, s.total_tax tax, s.fin_sq_ft sf, s.year_built yb,
             s.homestead, coalesce(s.lat, p.lat) lat, coalesce(s.lon, p.lon) lon, s.sale_date own_sale_date, s.sale_value own_sale_value,
             coalesce(nullif(s.zip,''), s.attrs->>'ZIP', s.attrs->>'ZIP1') zip,
             coalesce(nullif(s.city,''), s.attrs->>'POSTCOMM', s.attrs->>'CTU_NAME') city,
             nullif(s.street,'') street, nullif(s.anumber,'') house,
             s.attrs->>'ANUMBER' a_num, s.attrs->>'ST_PRE_DIR' a_pre, s.attrs->>'ST_NAME' a_name,
             s.attrs->>'ST_POS_TYP' a_typ, s.attrs->>'ST_POS_DIR' a_dir
      from parcel_snapshot s left join parcel p using (parcel_key)
      where s.county = '{county}' and s.vintage = '{vintage}' and {RES[county]}
        and s.fin_sq_ft > 400 and s.emv_total > 50000 and coalesce(s.lat, p.lat) is not null
    ),
    prior as (
      select parcel_key, arg_max(emv_total, as_of) emv_prior
      from parcel_snapshot p where p.county = '{county}'
        and p.mkt_year = (select max(mkt_year) from cur) - 1 group by 1
    ),
    addr as (select parcel_key, any_value(house) house, any_value(street) street, any_value(city) city, any_value(zip) zip
             from address_index group by 1)
    select c.parcel_key, c.pin, c.mkt_year, c.emv, pr.emv_prior, c.tax, c.sf, c.yb, c.homestead, c.lat, c.lon,
           c.own_sale_date, c.own_sale_value,
           coalesce(a.house, c.house, c.a_num) house,
           coalesce(a.street, c.street, trim(concat_ws(' ', c.a_pre, c.a_name, c.a_typ, c.a_dir))) street,
           coalesce(a.city, c.city) city, coalesce(c.zip, a.zip) zip
    from cur c left join prior pr using (parcel_key) left join addr a using (parcel_key)
    """


def sales_sql(county, vintage):
    return f"""
    select s.parcel_key, s.sale_date, s.sale_value, ps.fin_sq_ft sf, ps.year_built yb, ps.emv_total emv,
           coalesce(ps.lat, p.lat) lat, coalesce(ps.lon, p.lon) lon,
           coalesce(a.house, ps.anumber, ps.attrs->>'ANUMBER') house,
           coalesce(a.street, nullif(ps.street,''), trim(concat_ws(' ', ps.attrs->>'ST_PRE_DIR', ps.attrs->>'ST_NAME', ps.attrs->>'ST_POS_TYP', ps.attrs->>'ST_POS_DIR'))) street,
           coalesce(a.city, nullif(ps.city,''), ps.attrs->>'POSTCOMM') city,
           coalesce(nullif(ps.zip,''), ps.attrs->>'ZIP', ps.attrs->>'ZIP1', a.zip) zip
    from sale s
    join parcel_snapshot ps on ps.parcel_key = s.parcel_key and ps.vintage = '{vintage}' and ps.county = '{county}'
    left join parcel p on p.parcel_key = s.parcel_key
    left join (select parcel_key, any_value(house) house, any_value(street) street, any_value(city) city, any_value(zip) zip
               from address_index group by 1) a on a.parcel_key = s.parcel_key
    where s.sale_date >= DATE '{M.SALES_SINCE.isoformat()}' and s.sale_value >= {M.MIN_SALE}
      and ps.fin_sq_ft > 400 and ps.emv_total > 0 and coalesce(ps.lat, p.lat) is not null and {RES[county].replace('useclass1', 'ps.useclass1').replace('attrs->>', 'ps.attrs->>')}
      and s.sale_value / ps.emv_total between {M.RATIO_LO} and {M.RATIO_HI}
    qualify row_number() over (partition by s.parcel_key order by s.sale_date desc) = 1
    """


def cols(rel):
    """fetchnumpy() hands back masked arrays for nullable columns; make them plain (None / nan / NaT)."""
    out = {}
    for k, v in rel.fetchnumpy().items():
        if np.ma.isMaskedArray(v):
            if v.dtype.kind in "fiu":
                v = v.astype(float).filled(np.nan)
            elif v.dtype.kind == "M":
                v = v.filled(np.datetime64("NaT"))
            else:
                v = v.astype(object).filled(None)
        out[k] = v
    return out


def shard_of(addr):
    """Free rows are split by the house number's first digit, so a phone fetches ~1/10 of a ZIP."""
    return addr[0] if addr[:1].isdigit() else "0"


def tidy_addr(house, street, city):
    h = (house or "").strip()
    DIRS = {"N", "S", "E", "W", "NE", "NW", "SE", "SW"}
    st = " ".join(w.upper() if w.upper() in DIRS else w.capitalize() for w in (street or "").strip().split())
    # directional suffixes: keep N/S/E/W/NE/NW/SE/SW upper; ordinal streets: 39th not 39Th
    st = " ".join(w[:-2] + w[-2:].lower() if w[:-2].isdigit() and w[-2:].isalpha() and len(w) > 2 else w for w in st.split())
    c = " ".join(w.capitalize() for w in (city or "").strip().split())
    return f"{h} {st}".strip(), c


def build(db, out, counties, sample, today):
    con = duckdb.connect(str(db), read_only=True)
    zip_dir = out / "site/public/data/zip"; zip_dir.mkdir(parents=True, exist_ok=True)
    bundle = out / "private/bundle/comps"; bundle.mkdir(parents=True, exist_ok=True)
    for old in list(zip_dir.glob("*.json")) + list(bundle.glob("*.json.gz")):
        old.unlink()
    meta = {"built": today.isoformat(), "sales_since": M.SALES_SINCE.isoformat(), "counties": {}, "rule": {
        "sqft_band": M.SQFT_BAND, "age_band_years": M.AGE_BAND, "max_miles": M.MAX_MILES, "n_comps": M.N_COMPS,
        "min_comps": M.MIN_COMPS, "ratio_band": [M.RATIO_LO, M.RATIO_HI], "min_sale": M.MIN_SALE}}
    by_zip_rows = defaultdict(list)       # zip -> free rows
    by_zip_sales = defaultdict(list)      # zip -> sales table rows (the comps are indices into this)
    by_zip_comps = defaultdict(dict)      # zip -> {pk: [sale idx...]}
    zip_county = {}
    all_gaps = []
    example = None
    for county in counties:
        t = time.time()
        vintage = VINTAGE[county]
        H = cols(con.sql(homes_sql(county, vintage)))
        S = cols(con.sql(sales_sql(county, vintage)))
        n = len(H["parcel_key"])
        if sample and n > sample:
            keep = np.random.default_rng(1).choice(n, sample, replace=False)
            H = {k: v[keep] for k, v in H.items()}
            n = sample
        sale_days = np.array([M.days_since(d, today) for d in S["sale_date"]], float)
        sales = {"key": S["parcel_key"], "sf": S["sf"].astype(float), "yb": S["yb"].astype(float), "lat": S["lat"].astype(float),
                 "lon": S["lon"].astype(float), "price": S["sale_value"].astype(float), "days": sale_days}
        # the zip's own sale $/sqft median (sand): the market around the home in general
        zmed, zn = {}, {}
        for z in set(str(x)[:5] for x in S["zip"] if x):
            m = np.array([str(x)[:5] == z for x in S["zip"]])
            zn[str(z)] = int(m.sum())
            if zn[str(z)] >= M.MIN_ZIP_SALES:
                zmed[str(z)] = round(float(np.median(S["sale_value"][m] / S["sf"][m])), 2)
        # sales table per zip of the SALE (comps may cross zips: index them by the subject's zip below)
        sale_row = []
        for i in range(len(S["parcel_key"])):
            a, c = tidy_addr(S["house"][i], S["street"][i], S["city"][i])
            sale_row.append([a, c, str(S["sale_date"][i])[:7 if county == "hennepin" else 10],  # Hennepin records the month only (every row is the 1st)
                             int(S["sale_value"][i]), int(S["sf"][i]),
                             int(S["yb"][i]) if S["yb"][i] == S["yb"][i] and S["yb"][i] else None,
                             round(float(S["lat"][i]), 5), round(float(S["lon"][i]), 5)])
        local_index = defaultdict(dict)   # zip -> {sale idx -> local idx}
        c_argue = c_call = c_backs = c_none = 0
        gaps = []
        if n == 0:
            sys.exit(f"{county}: zero homes; check RES/VINTAGE")
        ay = int(np.nanmax(H["mkt_year"].astype(float)))
        for i in range(n):
            z = str(H["zip"][i] or "")
            if len(z) < 5: continue
            z = z[:5]
            sf = float(H["sf"][i]); yb = float(H["yb"][i]) if H["yb"][i] == H["yb"][i] and H["yb"][i] else None
            subj = {"sf": sf, "yb": yb, "lat": float(H["lat"][i]), "lon": float(H["lon"][i])}
            pk = str(H["parcel_key"][i])
            comps = M.pick_comps(subj, sales, exclude_key=pk)
            emv = float(H["emv"][i])
            target = ppsf = None
            if comps:
                target, ppsf = M.target_value(sf, sales["price"][comps], sales["sf"][comps])
            kind, gap = M.verdict(emv, target)
            if kind == "argue": c_argue += 1
            elif kind == "call": c_call += 1
            elif kind == "backs": c_backs += 1
            else: c_none += 1
            if gap is not None: gaps.append(gap)
            addr, city = tidy_addr(H["house"][i], H["street"][i], H["city"][i])
            hs = 1 if str(H["homestead"][i] or "").lower().startswith("y") else 0
            li = local_index[z]
            loc = []
            for ci in comps:
                if ci not in li:
                    li[ci] = len(by_zip_sales[z]); by_zip_sales[z].append(sale_row[ci])
                loc.append(li[ci])
            first = None
            if comps:
                r = sale_row[comps[0]]
                first = [r[0], r[1], r[2], r[3], r[4], round(float(M.miles(subj["lat"], subj["lon"], sales["lat"][comps[0]], sales["lon"][comps[0]])), 2)]
            prior = H["emv_prior"][i]
            own_d, own_v = H["own_sale_date"][i], H["own_sale_value"][i]
            row = [pk, addr, city, int(sf), int(yb) if yb else None, int(emv),
                   int(prior) if prior == prior and prior else None,
                   int(H["tax"][i]) if H["tax"][i] == H["tax"][i] and H["tax"][i] else None,
                   hs, ay, target, ppsf, len(comps), first,
                   str(own_d)[:10] if own_d and str(own_d) != "NaT" and own_v == own_v and own_v and own_v >= M.MIN_SALE else None,
                   int(own_v) if own_v == own_v and own_v and own_v >= M.MIN_SALE else None,
                   str(H["pin"][i] or "")]
            by_zip_rows[(z, shard_of(addr))].append(row)
            by_zip_comps[z][pk] = loc
            zip_county[z] = county
            if example is None and county == "ramsey" and kind == "argue" and len(comps) == M.N_COMPS and 0.12 <= gap <= 0.2 and hs and city.lower() in ("st paul", "saint paul"):
                example = {"zip": z, "pk": pk, "shard": shard_of(addr)}
        for z, md in zmed.items():
            meta.setdefault("zip_ppsf", {})[z] = md
        for z, cnt in zn.items():
            meta.setdefault("zip_sales_n", {})[z] = cnt
        g = np.array(gaps)
        meta["counties"][county] = {
            "name": COUNTY_NAME[county], "assessment_year": ay, "payable_year": ay + 1, "homes": n, "sales": int(len(S["parcel_key"])),
            "argue": c_argue, "call": c_call, "backs": c_backs, "no_comps": c_none,
            "gap_pct": {str(p): round(float(np.percentile(g, p)) * 100, 1) for p in (10, 25, 50, 75, 90)} if len(g) else {},
            "minneapolis_only": county == "hennepin"}
        all_gaps.extend(gaps)
        print(f"{county}: {n:,} homes, {len(S['parcel_key']):,} sales, argue {c_argue:,} call {c_call:,} backs {c_backs:,} none {c_none:,}  {time.time()-t:.0f}s", flush=True)
    # write
    for (z, sh), rows in by_zip_rows.items():
        (zip_dir / f"{z}-{sh}.json").write_text(json.dumps({
            "zip": z, "shard": sh, "county": zip_county[z], "ppsf": meta.get("zip_ppsf", {}).get(z), "n_sales": meta.get("zip_sales_n", {}).get(z, 0),
            "sales_since": M.SALES_SINCE.isoformat(), "homes": rows}, separators=(",", ":")))
    for z in by_zip_comps:
        with gzip.open(bundle / f"{z}.json.gz", "wt") as f:
            json.dump({"sales": by_zip_sales[z], "comps": by_zip_comps[z]}, f, separators=(",", ":"))
    g = np.array(all_gaps)
    meta["homes"] = sum(c["homes"] for c in meta["counties"].values())
    meta["sales"] = sum(c["sales"] for c in meta["counties"].values())
    meta["argue"] = sum(c["argue"] for c in meta["counties"].values())
    meta["call"] = sum(c["call"] for c in meta["counties"].values())
    meta["backs"] = sum(c["backs"] for c in meta["counties"].values())
    meta["gap_pct"] = {str(p): round(float(np.percentile(g, p)) * 100, 1) for p in (10, 25, 50, 75, 90)} if len(g) else {}
    # Backtest: homes that sold themselves since Jan 2025 (their own sale is never their own comp).
    bt = np.array([r[15] / r[10] for rows in by_zip_rows.values() for r in rows if r[10] and r[14] and r[14] >= "2025-01" and r[15]])
    meta["backtest"] = {"n": int(len(bt)), "median": round(float(np.median(bt)), 3) if len(bt) else None,
                        "within_10pct": round(float(np.mean(np.abs(bt - 1) <= 0.10)), 3) if len(bt) else None}
    meta["zips"] = len(by_zip_comps)
    meta["shards"] = len(by_zip_rows)
    meta.pop("zip_ppsf", None); meta.pop("zip_sales_n", None)
    (out / "site/public/data").mkdir(parents=True, exist_ok=True)
    (out / "site/public/data/meta.json").write_text(json.dumps(meta, indent=1))
    if example:
        (out / "site/public/data/example.json").write_text(json.dumps(example))
    print(json.dumps({k: v for k, v in meta.items() if k not in ("counties", "rule")}))
    return meta


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB))
    ap.add_argument("--out", default=str(ROOT))
    ap.add_argument("--county", default=",".join(VINTAGE))
    ap.add_argument("--sample", type=int, default=0)
    a = ap.parse_args()
    build(Path(a.db), Path(a.out), a.county.split(","), a.sample, date.today())
