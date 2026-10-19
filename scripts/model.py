"""The comp rule and the headline arithmetic, in one place so the build and the tests share it.

Every number on the page comes through here from the assessor's roll and the recorded sales;
nothing is typed. DATA_MODEL.md names the entities; this file is the join.
"""
from __future__ import annotations

import math
from datetime import date

import numpy as np

SALES_SINCE = date(2024, 7, 1)       # recorded sales from here on count as evidence
MIN_SALE = 50_000                    # below this it is a lot, a stall or a family transfer
RATIO_LO, RATIO_HI = 0.5, 2.0        # sale / its own EMV outside this is not arm's length (eng-lead memory, 10/10)
SQFT_BAND = 0.25                     # a comp is within ±25% of the subject's finished sqft
AGE_BAND = 25                        # and within ±25 years of its build year
MAX_MILES = 2.0                      # and within two miles
N_COMPS = 5
MIN_COMPS = 3
MIN_ZIP_SALES = 10                   # fewer than this and the zip median is not shown
BACKS_ASSESSOR = 0.03                # EMV within 3% of the comps: sales back the assessor
WORTH_A_CALL = 0.10                  # 3–10%: a little high; ≥10%: argue for the comp value

MI_PER_DEG_LAT = 69.0
MI_PER_DEG_LON = 49.0                # at 45°N


def miles(lat1, lon1, lat2, lon2):
    return np.hypot((lat2 - lat1) * MI_PER_DEG_LAT, (lon2 - lon1) * MI_PER_DEG_LON)


def arms_length(sale_value, emv_of_sold_home, sale_date):
    """Does a recorded sale count as evidence? (DATA_MODEL: Sale.arm's length)"""
    if sale_value is None or sale_value < MIN_SALE or sale_date is None or sale_date < SALES_SINCE:
        return False
    if not emv_of_sold_home or emv_of_sold_home <= 0:
        return False
    r = sale_value / emv_of_sold_home
    return RATIO_LO <= r <= RATIO_HI


def pick_comps(subject, sales, exclude_key=None):
    """subject: dict(sf, yb, lat, lon). sales: dict of numpy arrays (key, sf, yb, lat, lon, price, days).
    Returns indices into sales of the best N_COMPS, nearest and most alike first; [] if fewer than MIN_COMPS."""
    sf, yb = subject["sf"], subject["yb"] or 1950
    s_yb = np.where(np.isnan(sales["yb"]), 1950, sales["yb"])
    d = miles(subject["lat"], subject["lon"], sales["lat"], sales["lon"])
    ok = (np.abs(sales["sf"] / sf - 1) <= SQFT_BAND) & (np.abs(s_yb - yb) <= AGE_BAND) & (d <= MAX_MILES)
    if exclude_key is not None:
        ok &= sales["key"] != exclude_key
    idx = np.flatnonzero(ok)
    if len(idx) < MIN_COMPS:
        return []
    score = d[idx] + 2 * np.abs(sales["sf"][idx] / sf - 1) + np.abs(s_yb[idx] - yb) / 50 + sales["days"][idx] / 730
    return idx[np.argsort(score, kind="stable")[:N_COMPS]].tolist()


def target_value(subject_sf, comp_prices, comp_sfs):
    """Median comp $/sqft × the subject's finished sqft, to the nearest $100 (the green number)."""
    ppsf = float(np.median(np.asarray(comp_prices, float) / np.asarray(comp_sfs, float)))
    return int(round(ppsf * subject_sf / 100.0) * 100), round(ppsf, 2)


def verdict(emv, target):
    """What the headline says. gap = emv / target − 1."""
    if not target:
        return "no_comps", None
    gap = emv / target - 1
    if gap < BACKS_ASSESSOR:
        return "backs", gap
    if gap < WORTH_A_CALL:
        return "call", gap
    return "argue", gap


def tax_saving(total_tax, emv, target):
    """About what a cut to the target is worth per year, assuming tax moves with value."""
    if not total_tax or not emv or not target or target >= emv:
        return 0
    return int(round(total_tax * (1 - target / emv) / 10.0) * 10)


def days_since(d, today: date) -> int:
    """d may be a date, a datetime or a numpy datetime64 (DuckDB hands back all three)."""
    if d is None or str(d) == "NaT":
        return 10_000
    if hasattr(d, "astype"):
        d = d.astype("datetime64[D]").astype(object)
    if hasattr(d, "date") and not isinstance(d, date.__class__):
        d = d.date() if hasattr(d, "hour") else d
    return (today - d).days


def fmt_money(n):
    return "$" + f"{int(round(n)):,}" if n is not None and not (isinstance(n, float) and math.isnan(n)) else "—"
