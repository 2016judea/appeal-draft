"""The ratio statistics, and the files the connector and the crawlers read (scripts/build_ratio.py,
scripts/build_connector.py)."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def test_ratio_stats_match_iaao_definitions():
    import build_ratio as R
    price = np.array([100_000, 200_000, 300_000, 400_000], float)
    value = np.array([110_000, 190_000, 300_000, 360_000], float)  # ratios 1.10, 0.95, 1.00, 0.90
    s = R.stats(price, value)
    assert s["n"] == 4
    assert s["median"] == 0.975
    assert s["above"] == 0.25                      # only the 1.10 is above its price
    assert s["cod"] == round(100 * np.mean(np.abs(np.array([1.1, .95, 1.0, .9]) - .975)) / .975, 1)
    assert s["prd"] == round(np.mean([1.1, .95, 1.0, .9]) / (960_000 / 1_000_000), 3)
    assert "prb" not in s, "PRB only from 100 sales up"


def test_city_names_fold_saint():
    import build_ratio as R
    assert R.tidy_city("NORTH ST PAUL") == "North Saint Paul"
    assert R.tidy_city("st. paul") == "Saint Paul"
    assert R.tidy_city("Stillwater") == "Stillwater"


def test_mcp_thresholds_are_the_model_thresholds():
    import model as M
    d = json.loads((ROOT / "site/api/_mcp_data.json").read_text())
    assert d["thresholds"] == {"backs_below": M.BACKS_ASSESSOR, "argue_from": M.WORTH_A_CALL}


@pytest.mark.skipif(not (ROOT / "site/public/data/meta.json").exists(), reason="data not built")
def test_connector_build_writes_tagged_pages():
    subprocess.run([sys.executable, str(ROOT / "scripts/build_connector.py")], check=True, capture_output=True)
    ratio = json.loads((ROOT / "data/ratio.json").read_text())
    for rel in ("site/public/assessment-ratio/index.html", "site/public/privacy/index.html"):
        html = (ROOT / rel).read_text()
        assert "/_vercel/insights/script.js" in html, rel
        assert "bm-posthog:begin" in html and "phc_" in html, rel
    page = (ROOT / "site/public/assessment-ratio/index.html").read_text()
    assert f"{round(ratio['all']['above'] * 100)}% of Twin Cities homes" in page
    for z in ratio["zips"][:3]:
        assert f"<td>{z['zip']}</td>" in page
    assert "Method" in page and "Sources" in page and ratio["built"] in page
    llms = (ROOT / "site/public/llms.txt").read_text()
    assert "/mcp" in llms and "/assessment-ratio/" in llms and "April 30, 2027" in llms
    full = (ROOT / "site/public/llms-full.txt").read_text()
    assert all(z["zip"] in full for z in ratio["zips"])
    sm = (ROOT / "site/public/sitemap.xml").read_text()
    assert re.search(r"<loc>https://appeal-draft\.vercel\.app/assessment-ratio/</loc>", sm)


def test_deadlines_2027_cycle_is_sourced():
    d = json.loads((ROOT / "data/deadlines.json").read_text())["cycle_2027"]
    for k in ("notices", "local_boards", "county_boards"):
        assert d[k]["sources"] and all(s["url"].startswith("https://") and s["says"] for s in d[k]["sources"]), k
    assert d["tax_court"]["for_2026_value"] == "April 30, 2027" and d["tax_court"]["for_2027_value"] == "April 30, 2028"
    assert d["read_on"] >= "2026-11-19"
