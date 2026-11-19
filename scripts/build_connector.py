#!/usr/bin/env python3
"""Write everything the connector and the AI crawlers read, from data/ratio.json, data/deadlines.json,
site/public/data/meta.json and the ZIP shards:

  site/api/_mcp_data.json            what /mcp answers from besides the shards (bundled with the function)
  site/public/assessment-ratio/      the fresh-number page: county value / sale price, by county, city, ZIP, tier
  site/public/privacy/               what the site and the connector record (directories ask for it)
  site/public/llms.txt, llms-full.txt, sitemap.xml

  python3 scripts/build_connector.py      (after scripts/build.py and scripts/build_ratio.py)

Generated output: never hand-edit any of the files above; edit this and re-run.
"""
import html, json, re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://appeal-draft.vercel.app"
OFFER = json.loads((ROOT / "site/offer.json").read_text())
META = json.loads((ROOT / "site/public/data/meta.json").read_text())
DEAD = json.loads((ROOT / "data/deadlines.json").read_text())
RATIO = json.loads((ROOT / "data/ratio.json").read_text())
POSTHOG = (ROOT / "scripts/posthog_snippet.html").read_text().replace("__SITE__", OFFER["product"])
VA = '<script>window.va=window.va||function(){(window.vaq=window.vaq||[]).push(arguments)};</script><script defer src="/_vercel/insights/script.js"></script>'
C27 = DEAD["cycle_2027"]
SHOW = 12  # rows per table before "Show all": the page is read on a phone
e = html.escape


def norm_city(c):
    c = re.sub(r"[.,]", " ", str(c or "").lower())
    c = re.sub(r"\bst\b", "saint", c)
    return re.sub(r"\s+", " ", c).strip()


def city_index():
    """city (normalised) -> the ZIPs whose shards hold homes in it; ZIP -> county. Read off the shards."""
    cities, zc = defaultdict(set), {}
    for f in sorted((ROOT / "site/public/data/zip").glob("*.json")):
        d = json.loads(f.read_text())
        zc[d["zip"]] = d["county"]
        for r in d["homes"]:
            cities[norm_city(r[2])].add(d["zip"])
    return {k: sorted(v) for k, v in sorted(cities.items()) if k}, zc


def pct(x):
    return f"{round(x * 100)}%"


def mcp_data(cities, zc):
    keep = ("n", "median", "above", "above_moe", "cod", "prd", "prb")
    return {
        "built": META["built"], "ratio_built": RATIO["built"], "sales_since": META["sales_since"], "rule": META["rule"],
        "thresholds": {"backs_below": 0.03, "argue_from": 0.10},  # scripts/model.py BACKS_ASSESSOR, WORTH_A_CALL
        "backtest": META.get("backtest"),
        "counties": {k: {"name": v["name"], "assessment_year": v["assessment_year"], "payable_year": v["payable_year"],
                         "homes": v["homes"], "minneapolis_only": v["minneapolis_only"]} for k, v in META["counties"].items()},
        "deadlines": {"counties": DEAD["counties"], "cycle_2027": C27, "statewide": DEAD["statewide"]},
        "ratio": {"trim": RATIO["trim"], "all": RATIO["all"],
                  "counties": {k: {x: v.get(x) for x in keep + ("assessment_year", "sales_from", "sales_to")} for k, v in RATIO["counties"].items()},
                  "cities": [{"county": c["county"], "city": c["city"], **{x: c.get(x) for x in keep[:4]}} for c in RATIO["cities"]],
                  "zips": [{"zip": z["zip"], "county": z["county"], "city": z["city"], **{x: z.get(x) for x in keep[:4]}} for z in RATIO["zips"]],
                  "tiers": {k: [{x: t[x] for x in ("tier", "n", "median", "above", "price_median")} for t in v] for k, v in RATIO["tiers"].items()}},
        "cities": cities, "zip_county": zc,
    }


HEAD = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="__DESC__">
<link rel="canonical" href="__CANON__">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%232457c5'/><rect x='8' y='14' width='16' height='3' fill='%23f7f1e3'/><rect x='8' y='20' width='10' height='3' fill='%23c9973f'/></svg>">
__POSTHOG__
<style>
:root{--bg:#f7f3ea;--paper:#fffdf8;--ink:#17150f;--muted:#6b6557;--rule:#e0d8c6;--assessor:#2457c5;--sales:#c9973f;--target:#2e7d4f;--mono:ui-monospace,SFMono-Regular,Menlo,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;--serif:Georgia,"Times New Roman",serif;color-scheme:light}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#15130e;--paper:#1e1c15;--ink:#f0ebe0;--muted:#a7a08f;--rule:#38342a;--assessor:#6f95ea;--sales:#d9ac5a;--target:#5fb37f;color-scheme:dark}}
:root[data-theme=dark]{--bg:#15130e;--paper:#1e1c15;--ink:#f0ebe0;--muted:#a7a08f;--rule:#38342a;--assessor:#6f95ea;--sales:#d9ac5a;--target:#5fb37f;color-scheme:dark}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 var(--sans)}
.wrap{max-width:1040px;margin:0 auto;padding:22px 16px 64px}
.eyebrow{font:500 12px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.eyebrow a{color:inherit}
h1{font:400 clamp(27px,5.2vw,44px)/1.12 var(--serif);margin:8px 0 14px;letter-spacing:-.01em;max-width:26ch}
h2{font:400 clamp(21px,3.4vw,27px)/1.2 var(--serif);margin:30px 0 6px}
.lede{margin:0 0 16px;max-width:60ch;color:var(--muted)}
.lede b{color:var(--ink)}
.card{background:var(--paper);border:1px solid var(--rule);border-radius:14px;padding:16px;margin:0 0 14px}
.btn{font:600 16px var(--sans);border-radius:9px;padding:12px 18px;background:var(--ink);color:var(--bg);min-height:46px;text-decoration:none;display:inline-flex;align-items:center}
.hint{font-size:13px;color:var(--muted)}
input{font:16px var(--sans);padding:12px;border:1px solid var(--rule);border-radius:9px;background:var(--paper);color:var(--ink);min-height:46px;width:100%;max-width:26em}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{width:100%;border-collapse:collapse;font-size:14px;margin:8px 0}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--rule);vertical-align:middle}
th{font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
td.r,th.r{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.bar{width:34%;min-width:90px}
td.bar i{display:block;height:12px;border-radius:3px;background:var(--assessor)}
.dates{display:grid;grid-template-columns:1fr;gap:6px 18px;margin:8px 0 0;padding:0;list-style:none}
@media (min-width:720px){.dates{grid-template-columns:1fr 1fr}}
.dates b{font:600 15px var(--mono)}
.foot{margin-top:40px;border-top:1px solid var(--rule);padding-top:12px;font-size:13px;color:var(--muted);max-width:76ch}
.foot a,.card a,.lede a,p a{color:inherit}
tr[hidden]{display:none}
@media (max-width:560px){.opt{display:none}}
.more{margin:4px 0 0}
</style></head><body>
"""


FILTER_JS = r"""<script>
const q=document.getElementById("q"),qn=document.getElementById("qn");let t=null;
const rows=()=>document.querySelectorAll("#tz tbody tr,#tc tbody tr");
function reset(){for(const tr of rows())tr.hidden=tr.hasAttribute("data-more");for(const b of document.querySelectorAll("[data-show]"))b.parentNode.hidden=false}
q.addEventListener("input",()=>{const v=q.value.trim().toLowerCase().replace(/\bst\.?\s/g,"saint ");if(!v){reset();qn.textContent="";return}let n=0;for(const tr of rows()){const hit=tr.dataset.k.includes(v);tr.hidden=!hit;if(hit)n++}for(const b of document.querySelectorAll("[data-show]"))b.parentNode.hidden=true;qn.textContent=n?n+" match"+(n>1?"es":""):"No ZIP or city with 30+ sales matches. Covered: Ramsey, Anoka, Dakota, Scott, Washington, Minneapolis.";clearTimeout(t);t=setTimeout(()=>{if(v.length>=3)try{window.posthog&&posthog.capture("ratio_search",{q_len:v.length,hits:n})}catch(e){}},1200)});
for(const b of document.querySelectorAll("[data-show]"))b.addEventListener("click",()=>{for(const tr of document.querySelectorAll("#"+b.dataset.show+" tbody tr"))tr.hidden=false;b.parentNode.hidden=true;try{window.posthog&&posthog.capture("ratio_show_all",{table:b.dataset.show})}catch(e){}});
</script>
"""


def head(title, desc, canon):
    return HEAD.replace("__TITLE__", e(title)).replace("__DESC__", e(desc)).replace("__CANON__", canon).replace("__POSTHOG__", POSTHOG)


def dates_html():
    return f"""<ul class="dates">
<li>Valuation notices: <b>{e(C27['notices']['when'])}</b>, at least 10 days before your local meeting</li>
<li>Local boards and open book: <b>{e(C27['local_boards']['when'])}</b></li>
<li>County boards: <b>{e(C27['county_boards']['when'])}</b></li>
<li>Tax Court on the 2026 value: <b>{e(C27['tax_court']['for_2026_value'])}</b>; on the 2027 value: <b>{e(C27['tax_court']['for_2027_value'])}</b></li>
</ul>"""


def ratio_page():
    a, cs, zs = RATIO["all"], RATIO["counties"], RATIO["zips"]
    lo, hi = zs[-1], zs[0]
    hi2 = next((z for z in zs if z["n"] >= 80), hi)
    county_names = ", ".join(v["name"] for k, v in cs.items() if k != "hennepin")
    tiers_low = {k: v[0] for k, v in RATIO["tiers"].items()}
    tiers_high = {k: v[-1] for k, v in RATIO["tiers"].items()}
    worst_tier = max(RATIO["tiers"], key=lambda k: tiers_low[k]["above"] - tiers_high[k]["above"])
    title = "Twin Cities assessment ratio: county value vs. sale price, by ZIP and city"
    desc = (f"{pct(a['above'])} of Twin Cities homes that sold were valued by the county above their sale price. "
            f"County value / sale price for {a['n']:,} recorded sales, by county, city, ZIP and price tier.")

    def bar_row(cells, above, key, i):
        extra = ' data-more hidden' if i >= SHOW else ''
        return f'<tr data-k="{e(key.lower())}"{extra}>{cells}<td class="bar opt" aria-hidden="true"><i style="width:{max(2, round(above * 100))}%"></i></td></tr>'

    zip_rows = "".join(bar_row(f'<td>{z["zip"]}</td><td>{e(z["city"])}</td><td class="r opt">{z["n"]:,}</td><td class="r">{pct(z["above"])} <span class="hint">±{round(z["above_moe"] * 100)}</span></td><td class="r">{z["median"]:.3f}</td>',
                                   z["above"], z["zip"] + " " + z["city"], i) for i, z in enumerate(zs))
    city_rows = "".join(bar_row(f'<td>{e(c["city"])}</td><td class="opt">{e(cs[c["county"]]["name"])}</td><td class="r opt">{c["n"]:,}</td><td class="r">{pct(c["above"])} <span class="hint">±{round(c["above_moe"] * 100)}</span></td><td class="r">{c["median"]:.3f}</td>',
                                    c["above"], c["city"] + " " + cs[c["county"]]["name"], i) for i, c in enumerate(RATIO["cities"]))
    county_rows = "".join(f'<tr><td>{e(v["name"])}{" (Minneapolis)" if v["minneapolis_only"] else ""}</td><td class="r">{v["assessment_year"]}</td><td class="r">{v["n"]:,}</td><td class="r">{pct(v["above"])}</td><td class="r">{v["median"]:.3f}</td><td class="r">{v["cod"]}</td><td class="r">{v["prd"]:.3f}</td><td class="r">{v.get("prb", "")}</td></tr>' for v in cs.values())
    money = lambda n: "$" + format(n, ",")
    tier_rows = "".join(f'<tr><td>{e(cs[k]["name"])}</td><td class="r">{pct(tiers_low[k]["above"])} <span class="hint">({money(tiers_low[k]["price_median"])})</span></td><td class="r">{pct(tiers_high[k]["above"])} <span class="hint">({money(tiers_high[k]["price_median"])})</span></td></tr>' for k in RATIO["tiers"])
    windows = "; ".join(f'{v["name"]}: {v["assessment_year"]} value (as of Jan 2, {v["assessment_year"]}) against sales {v["sales_from"]} to {v["sales_to"]}' for v in cs.values())
    body = f"""<main class="wrap">
<div class="eyebrow"><a href="/?src=ratio">Appeal Draft</a> · Assessment ratio · built {e(RATIO["built"])}</div>
<h1>{pct(a["above"])} of Twin Cities homes that sold were valued by the county above their sale price</h1>
<p class="lede">The county's value on a home divided by what it actually sold for. Across <b>{a["n"]:,} recorded sales</b> of houses and townhouses, the typical home was valued at <b>{a["median"]:.3f}</b> of its price, a little under. But the share valued <b>above</b> the price runs from <b>{pct(lo["above"])} in {lo["zip"]}</b> ({e(lo["city"])}) to <b>{pct(hi2["above"])} in {hi2["zip"]}</b> ({e(hi2["city"])}).</p>
<p><a class="btn" href="/?src=ratio">Check your own home</a></p>
<div class="card"><b>Find your ZIP or city</b><br><input id="q" placeholder="ZIP or city, e.g. 55104 or Roseville" inputmode="search" aria-label="ZIP or city"><p class="hint" id="qn"></p></div>
<h2>By ZIP</h2>
<p class="hint">Share of sold homes the county valued above their sale price, with its 90% margin; then the median ratio (value / price). ZIPs with {RATIO["min_n"]}+ sales.</p>
<div class="scroll"><table id="tz"><thead><tr><th>ZIP</th><th>City</th><th class="r opt">Sales</th><th class="r">Above price</th><th class="r">Median</th><th class="opt"></th></tr></thead><tbody>{zip_rows}</tbody></table></div>
<p class="more"><button class="btn" type="button" data-show="tz" style="background:transparent;color:var(--ink);border:1px solid var(--rule)">Show all {len(zs)} ZIPs</button></p>
<h2>By city</h2>
<div class="scroll"><table id="tc"><thead><tr><th>City</th><th class="opt">County</th><th class="r opt">Sales</th><th class="r">Above price</th><th class="r">Median</th><th class="opt"></th></tr></thead><tbody>{city_rows}</tbody></table></div>
<p class="more"><button class="btn" type="button" data-show="tc" style="background:transparent;color:var(--ink);border:1px solid var(--rule)">Show all {len(RATIO["cities"])} cities</button></p>
<h2>Cheaper homes are valued above their price more often</h2>
<p class="hint">Share valued above the sale price, lowest-priced quarter of sales vs. highest (median price in brackets). Quarters are cut on ½ × (value / median ratio) + ½ × price, so a home that simply sold cheap does not land in the bottom quarter on its own.</p>
<div class="scroll"><table><thead><tr><th>County</th><th class="r">Cheapest quarter</th><th class="r">Dearest quarter</th></tr></thead><tbody>{tier_rows}</tbody></table></div>
<p class="hint">The widest gap is {e(cs[worst_tier]["name"])}: {pct(tiers_low[worst_tier]["above"])} vs. {pct(tiers_high[worst_tier]["above"])}.</p>
<h2>By county</h2>
<p class="hint">IAAO targets for homes: median ratio 0.90 to 1.10, COD 5 to 15 (lower is more uniform), PRD 0.98 to 1.03, PRB within ±0.05 (below −0.05 means cheaper homes are valued high relative to dearer ones). Every county passes on the median and the COD.</p>
<div class="scroll"><table><thead><tr><th>County</th><th class="r">Value year</th><th class="r">Sales</th><th class="r">Above price</th><th class="r">Median</th><th class="r">COD</th><th class="r">PRD</th><th class="r">PRB</th></tr></thead><tbody>{county_rows}</tbody></table></div>
<h2>The next appeal window</h2>
<div class="card">{dates_html()}<p class="hint">Sources: <a href="{e(C27["notices"]["sources"][0]["url"])}" rel="noopener">Hennepin County</a>, <a href="{e(C27["notices"]["sources"][1]["url"])}" rel="noopener">Ramsey County</a>, <a href="{e(C27["county_boards"]["sources"][0]["url"])}" rel="noopener">MN Revenue</a>, <a href="{e(C27["local_boards"]["sources"][0]["url"])}" rel="noopener">Minn. Stat. 274.01</a>, <a href="{e(C27["tax_court"]["sources"][0]["url"])}" rel="noopener">278.01</a>; read {e(C27["read_on"])}. {e(C27["right_now"])}</p></div>
<h2>Method</h2>
<div class="foot" style="margin-top:6px;border:0;padding:0">
<p><b>Ratio</b> = the county's estimated market value on the home ÷ its recorded sale price. Houses and townhouses only (no condos), in {e(county_names)} counties and the City of Minneapolis. Hennepin outside Minneapolis and Carver are not covered.</p>
<p><b>Which value, which sales.</b> {e(windows)}. Each county's own ratio study for that value used sales through the September before it, so none of these sales went into the value they are tested against. Sales of $50,000 and up, the latest per home; ratios outside {RATIO["trim"][0]} to {RATIO["trim"][1]} are dropped as not arm's length. Hennepin records sale months, not days.</p>
<p><b>Sources.</b> County assessor rolls (MetroGIS regional parcel data for the suburbs and Saint Paul; the Minneapolis assessor's file for Minneapolis) and the recorded sales on them. Built {e(RATIO["built"])} from the Brick &amp; Mortar records store. The full numbers are in <a href="/ratio.json">ratio.json</a> and <a href="/llms-full.txt">llms-full.txt</a>.</p>
<p><b>What it is not.</b> A ratio above 1.00 on one sale is not proof that home was over-valued: sale prices are noisy, and a share above 1.00 near 30% is normal for an office valuing a little under the market. It is where to look first. For one home, <a href="/?src=ratio">Appeal Draft</a> compares its value with recorded sales of homes like it. Ask an AI assistant with the Appeal Draft connector added (<code>{SITE}/mcp</code>).</p>
<p><a href="/privacy/">Privacy</a> · Code: <a href="https://github.com/2016judea/appeal-draft" rel="noopener">github.com/2016judea/appeal-draft</a> (MIT)</p>
</div>
</main>
{VA}
</body></html>"""
    return head(title, desc, SITE + "/assessment-ratio/") + body.replace("</body>", FILTER_JS + "</body>")


def privacy_page():
    body = f"""<main class="wrap">
<div class="eyebrow"><a href="/">Appeal Draft</a> · Privacy</div>
<h1>What Appeal Draft records</h1>
<div class="foot" style="border:0;padding:0;font-size:15px;color:var(--ink)">
<p><b>The website.</b> Page views go to Vercel Web Analytics and to PostHog: the page, the step you reached (home found, checkout opened, paid), the link you arrived from, your device type. Not the address you type. Payments go through Stripe, which keeps your email for the receipt; we keep the email only to send your password.</p>
<p><b>The AI connector</b> (<code>{SITE}/mcp</code>). Each call records which tool ran, whether it worked, how long it took, the county and the verdict (for example "argue" or "backs"), and which assistant called (Claude, ChatGPT). The address you ask about is used to find the home and is <b>not stored</b>. When no ZIP is given, the address is sent to the U.S. Census Bureau's public geocoder to find one. Nothing is sold or shared for advertising.</p>
<p><b>The data.</b> Public record from the county assessors and the recorded sales. Owner names are never shown or returned.</p>
<p>Questions or deletion requests: <a href="mailto:aidan@brickandmortar.dev">aidan@brickandmortar.dev</a>. Brick and Mortar AI LLC, Saint Paul, Minnesota. Updated 2026-11-19.</p>
</div></main>
{VA}
</body></html>"""
    return head("Privacy · Appeal Draft", "What Appeal Draft and its AI connector record.", SITE + "/privacy/") + body


def llms(full):
    a, cs = RATIO["all"], RATIO["counties"]
    lines = [
        "# Appeal Draft",
        "",
        "> Is my Twin Cities property tax assessment too high, and should I appeal? Appeal Draft compares the county's value on a home with recorded sales of homes like it, says whether an appeal looks worth filing, and gives the dates. Houses and townhouses in Ramsey, Anoka, Dakota, Scott and Washington counties and the City of Minneapolis.",
        "",
        f"- [Check one home]({SITE}/): type an address; the county's value, what similar sales say, the gap.",
        f"- [Assessment ratio by ZIP and city]({SITE}/assessment-ratio/): county value / sale price for {a['n']:,} sales; {pct(a['above'])} were valued above their price.",
        f"- [MCP connector]({SITE}/mcp): Streamable HTTP, no auth. Tools: check_property_assessment, property_tax_appeal_dates, assessment_ratio_by_area.",
        f"- [Full numbers]({SITE}/llms-full.txt)",
        "",
        "## Dates (2027 cycle, read " + C27["read_on"] + ")",
        f"- Valuation notices: {C27['notices']['when']}, at least 10 days before the local board or open book meeting.",
        f"- Local boards / open book: {C27['local_boards']['when']}.",
        f"- County boards: {C27['county_boards']['when']}.",
        f"- Minnesota Tax Court: {C27['tax_court']['for_2026_value']} for the 2026 value; {C27['tax_court']['for_2027_value']} for the 2027 value.",
    ]
    if full:
        lines += ["", "## Assessment ratio method", "",
                  f"Ratio = county estimated market value / recorded sale price. Houses and townhouses, no condos. Trim {RATIO['trim'][0]}-{RATIO['trim'][1]}. Built {RATIO['built']}.",
                  "Each county's value (as of Jan 2 of its value year) is tested against sales from Oct 1 before it to Jun 30 after it, none of which went into that value.",
                  "", "## By county", "", "county | value year | sales | share valued above sale price | median ratio | COD | PRD | PRB", "--- | --- | --- | --- | --- | --- | --- | ---"]
        lines += [f"{v['name']}{' (Minneapolis only)' if v['minneapolis_only'] else ''} | {v['assessment_year']} | {v['n']} | {pct(v['above'])} | {v['median']:.3f} | {v['cod']} | {v['prd']:.3f} | {v.get('prb', '')}" for v in cs.values()]
        lines += ["", "## By ZIP (30+ sales)", "", "zip | city | sales | share valued above sale price (90% margin) | median ratio", "--- | --- | --- | --- | ---"]
        lines += [f"{z['zip']} | {z['city']} | {z['n']} | {pct(z['above'])} (±{round(z['above_moe'] * 100)}) | {z['median']:.3f}" for z in RATIO["zips"]]
        lines += ["", "## By city (30+ sales)", "", "city | county | sales | share valued above sale price | median ratio", "--- | --- | --- | --- | ---"]
        lines += [f"{c['city']} | {cs[c['county']]['name']} | {c['n']} | {pct(c['above'])} | {c['median']:.3f}" for c in RATIO["cities"]]
        lines += ["", "## By price tier (share valued above sale price)", "", "county | lowest-priced quarter | highest-priced quarter", "--- | --- | ---"]
        lines += [f"{cs[k]['name']} | {pct(v[0]['above'])} (median price ${v[0]['price_median']:,}) | {pct(v[-1]['above'])} (median price ${v[-1]['price_median']:,})" for k, v in RATIO["tiers"].items()]
        lines += ["", "## Appeal steps by county", ""]
        for k, c in DEAD["counties"].items():
            lines += [f"### {c['name']}", f"Assessor: {c['assessor_phone']} · {c['url']}"] + [f"- {s}" for s in c["steps"]] + [""]
    return "\n".join(lines) + "\n"


def sitemap():
    urls = [("/", META["built"]), ("/assessment-ratio/", RATIO["built"]), ("/privacy/", "2026-11-19")]
    rows = "\n".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{d}</lastmod></url>" for u, d in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}\n</urlset>\n'


def main():
    cities, zc = city_index()
    out = {
        "site/api/_mcp_data.json": json.dumps(mcp_data(cities, zc), separators=(",", ":")),
        "site/public/assessment-ratio/index.html": ratio_page(),
        "site/public/privacy/index.html": privacy_page(),
        "site/public/llms.txt": llms(False),
        "site/public/llms-full.txt": llms(True),
        "site/public/sitemap.xml": sitemap(),
        "site/public/ratio.json": json.dumps(RATIO, indent=1) + "\n",
    }
    for rel, text in out.items():
        p = ROOT / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        print(f"wrote {rel} ({len(text):,} bytes)")


if __name__ == "__main__":
    main()
