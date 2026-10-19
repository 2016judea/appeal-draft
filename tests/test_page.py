import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_page_builds_with_analytics_and_price(tmp_path):
    if not (ROOT / "site/public/data/meta.json").exists():
        import pytest
        pytest.skip("site/public/data/meta.json not built")
    subprocess.run([sys.executable, str(ROOT / "scripts/build_page.py")], check=True)
    html = (ROOT / "site/public/index.html").read_text()
    offer = json.loads((ROOT / "site/offer.json").read_text())
    assert "/_vercel/insights/script.js" in html, "Vercel Web Analytics tag"
    assert "bm-posthog:begin" in html and "phc_" in html, "the shared PostHog block"
    assert f"Unlock for ${offer['price_usd']}" in html
    assert offer["stripe_pk"].startswith("pk_live_") and offer["stripe_pk"] in html
    assert "preview_open" in html and "checkout_open" in html and '"paid"' in html
    assert "/data/for/" in html and "/for/" in html, "/for/<token>/ reads the recipient's own home"
    assert re.search(r"Minneapolis homes show the 2025 assessment", html)
    assert "<title>Appeal Draft</title>" in html
    # the page quotes no typed figures: every count comes from META
    assert "618,892" not in html.split("<script")[0]


def test_deadlines_cite_a_source_and_date():
    d = json.loads((ROOT / "data/deadlines.json").read_text())
    for k, c in d["counties"].items():
        assert c["url"].startswith("https://") and re.match(r"\d{4}-\d{2}-\d{2}", c["read_on"]), k
        assert c["steps"] and c["assessor_phone"]
    assert d["statewide"]["next"]["tax_court_for_2026_value"] == "April 30, 2027"
