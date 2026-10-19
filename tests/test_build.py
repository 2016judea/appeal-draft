import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import model as M  # noqa: E402

ROW = dict(pk=0, addr=1, city=2, sf=3, yb=4, emv=5, prior=6, tax=7, hs=8, ay=9, target=10, ppsf=11, ncomps=12, first=13, own_date=14, own_price=15, pin=16)


def rows(out):
    files = sorted((out / "site/data/zip").glob("55104-*.json"))
    assert files, "one shard file per zip + house digit"
    homes = {}
    for f in files:
        d = json.loads(f.read_text())
        assert d["zip"] == "55104" and d["county"] == "ramsey"
        for r in d["homes"]:
            homes[r[ROW["pk"]]] = (r, d)
    return homes


def test_build_counts_and_meta(built):
    out, meta = built
    assert meta["counties"]["ramsey"]["homes"] == 6
    # 5 arm's-length sales: the 2019 one is too old, the $10k one is below the floor
    assert meta["counties"]["ramsey"]["sales"] == 5
    assert meta["counties"]["ramsey"]["assessment_year"] == 2025
    assert json.loads((out / "site/data/meta.json").read_text())["homes"] == 6


def test_free_row_shape_and_headline(built):
    out, _ = built
    homes = rows(out)
    r, d = homes["ramsey:1"]
    assert len(r) == len(ROW), "the free row is exactly the fields the page needs; no lat/lon, no owner"
    assert r[ROW["addr"]] == "100 Elm St" and r[ROW["city"]] == "St Paul"
    assert r[ROW["emv"]] == 400_000 and r[ROW["prior"]] == 360_000 and r[ROW["hs"]] == 1 and r[ROW["ay"]] == 2025
    # comps for home 1: sales 2,3,4,5 are in band (6 is 1600 sqft, within 25% of 1500 -> also in). ppsf median
    assert r[ROW["ncomps"]] == 5
    target, ppsf = M.target_value(1500, [305e3, 296e3, 310e3, 290e3, 320e3], [1520, 1480, 1550, 1450, 1600])
    assert r[ROW["target"]] == target and r[ROW["ppsf"]] == ppsf
    assert M.verdict(400_000, target)[0] == "argue"
    assert d["n_sales"] == 5 and d["ppsf"] is None, "fewer than 10 zip sales: no zip median shown"
    assert r[ROW["own_date"]] is None, "home 1 never sold"
    r2, _ = homes["ramsey:2"]
    assert r2[ROW["own_date"]] == "2025-06-01" and r2[ROW["own_price"]] == 305_000


def test_free_slice_holds_exactly_one_comp_and_paid_bundle_holds_them_all(built):
    out, _ = built
    homes = rows(out)
    r, _ = homes["ramsey:1"]
    first = r[ROW["first"]]
    assert isinstance(first, list) and len(first) == 6, "addr, city, date, price, sf, miles"
    bundle = json.loads(gzip.open(out / "private/bundle/comps/55104.json.gz", "rt").read())
    comps = [bundle["sales"][i] for i in bundle["comps"]["ramsey:1"]]
    assert len(comps) == 5
    assert comps[0][0] == first[0] and comps[0][3] == first[3], "the free comp is the bundle's first"
    # none of the other four comps' sale lines appear anywhere under site/ (the free slice never leaks paid fields)
    public = "".join(p.read_text() for p in (out / "site/data").rglob("*.json"))
    for addr, city, date, price, *_ in comps[1:]:
        assert f'"{addr}","{city}","{date}",{price}' not in public


def test_subject_is_not_its_own_comp(built):
    out, _ = built
    homes = rows(out)
    r, _ = homes["ramsey:2"]
    bundle = json.loads(gzip.open(out / "private/bundle/comps/55104.json.gz", "rt").read())
    assert all(bundle["sales"][i][0] != "102 Elm St" for i in bundle["comps"]["ramsey:2"])


def test_example_is_argue_with_five_comps(built):
    out, _ = built
    ex = out / "site/data/example.json"
    if ex.exists():
        e = json.loads(ex.read_text())
        assert set(e) == {"zip", "pk", "shard"}
