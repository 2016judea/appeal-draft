import sys
from datetime import date
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import model as M  # noqa: E402


def sales(n=8):
    return {"key": np.array([f"ramsey:{i}" for i in range(n)]), "sf": np.array([1500, 1550, 1600, 1450, 1900, 1520, 1480, 3000], float),
            "yb": np.array([1950, 1955, 1960, 1948, 1950, 1951, np.nan, 1950], float),
            "lat": np.array([44.95, 44.951, 44.952, 44.953, 44.954, 44.99, 44.95, 44.95]), "lon": np.array([-93.1] * 8),
            "price": np.array([300e3, 310e3, 320e3, 290e3, 380e3, 305e3, 296e3, 600e3]), "days": np.array([100, 200, 300, 400, 500, 50, 10, 20], float)}


def test_pick_comps_bands_and_order():
    S = sales()
    subj = {"sf": 1500, "yb": 1950, "lat": 44.95, "lon": -93.1}
    idx = M.pick_comps(subj, S)
    assert len(idx) == M.N_COMPS
    assert 7 not in idx, "3000 sqft is outside the ±25% band"
    assert 5 not in idx, "44.99 is ~2.8 miles away, outside 2 miles"
    assert 4 not in idx, "1900 sqft is outside the band for a 1500 sqft home"
    assert idx[0] in (0, 6), "nearest, most alike and most recent first"


def test_pick_comps_excludes_subject_and_needs_three():
    S = sales()
    subj = {"sf": 1500, "yb": 1950, "lat": 44.95, "lon": -93.1}
    assert "ramsey:0" not in [S["key"][i] for i in M.pick_comps(subj, S, exclude_key="ramsey:0")]
    far = {"sf": 1500, "yb": 1950, "lat": 45.5, "lon": -93.1}
    assert M.pick_comps(far, S) == []


def test_target_value_is_median_ppsf_times_sqft_to_100():
    target, ppsf = M.target_value(2000, [300e3, 320e3, 400e3], [1500, 1600, 2000])  # ppsf 200, 200, 200
    assert (target, ppsf) == (400_000, 200.0)
    target, _ = M.target_value(1234, [300e3], [1500])  # 200 * 1234 = 246,800
    assert target == 246_800


def test_verdict_thresholds():
    assert M.verdict(300_000, None) == ("no_comps", None)
    assert M.verdict(306_000, 300_000)[0] == "backs"   # +2%
    assert M.verdict(280_000, 300_000)[0] == "backs"   # under the sales
    assert M.verdict(321_000, 300_000)[0] == "call"    # +7%
    assert M.verdict(345_000, 300_000)[0] == "argue"   # +15%


def test_arms_length():
    assert M.arms_length(300_000, 290_000, date(2025, 1, 1))
    assert not M.arms_length(20_000, 290_000, date(2025, 1, 1)), "below the floor"
    assert not M.arms_length(300_000, 1_000, date(2025, 1, 1)), "a garage stall's EMV"
    assert not M.arms_length(300_000, 290_000, date(2023, 1, 1)), "too old"


def test_tax_saving():
    assert M.tax_saving(5000, 400_000, 360_000) == 500
    assert M.tax_saving(5000, 400_000, 420_000) == 0
    assert M.tax_saving(None, 400_000, 360_000) == 0


def test_days_since_accepts_duckdb_types():
    today = date(2026, 10, 19)
    assert M.days_since(date(2026, 10, 18), today) == 1
    assert M.days_since(np.datetime64("2026-10-09"), today) == 10
    assert M.days_since(np.datetime64("NaT"), today) == 10_000
