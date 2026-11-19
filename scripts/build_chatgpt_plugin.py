#!/usr/bin/env python3
"""Build the ChatGPT plugin ZIP that platform.openai.com/plugins takes (Agent Plugins format: root
plugin.json with OpenAI fields under extensions.com.openai, mcp.json, assets/). Pattern:
~/Desktop/workspace/small-business-intelligence-mcp/scripts/build_chatgpt_plugin.py.

Tool names and annotations are read off site/api/mcp.js, never typed here: a listing that disagrees
with the live server is the one rejection cause on record (SUBMISSION-KIT §10, 2026-10-09).
The long description carries no pricing words; OpenAI's metadata check fails "Free" and prices.

    python3 scripts/build_chatgpt_plugin.py   ->  chatgpt-plugin.zip   (bump VERSION for every upload)
"""
import json, re, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PKG, OUT = ROOT / "chatgpt-plugin", ROOT / "chatgpt-plugin.zip"
VERSION = "1.0.0"
SITE = "https://appeal-draft.vercel.app"

DESC = ("Appeal Draft answers \"is my property tax assessment too high, and should I appeal?\" for a home in the "
        "Minneapolis-Saint Paul area. Given an address, it returns the county's estimated market value, what recorded "
        "sales of similar nearby homes say the home is worth, the gap between them, whether an appeal looks worth filing, "
        "about how much a cut would lower the yearly tax, and the county's appeal steps with the 2027 dates for valuation "
        "notices, open book and local boards, county boards and the Minnesota Tax Court, each with its official source. "
        "It also gives the assessment ratio (county value divided by sale price) by ZIP, city and county: the share of "
        "sold homes valued above their sale price, and whether cheaper homes are valued high more often. Every number "
        "comes from county assessor rolls and recorded sales; nothing is estimated by the model. Coverage is houses and "
        "townhouses in Ramsey, Anoka, Dakota, Scott and Washington counties and the City of Minneapolis; other addresses "
        "get a plain 'not covered'. Each answer links to a page that opens the same comparison for that home. "
        "All three tools are read-only and need no account.")

POSITIVE = [
    ("Check whether one covered home's assessment is above what similar sales support.",
     "Is the property tax assessment on 1852 Ashland Ave, St Paul MN 55104 too high? Should I appeal?",
     "check_property_assessment",
     "Returns the county's 2025 value ($616,500), the comparable-sales value ($477,500), a 29% gap, the verdict worth_appealing, the yearly tax saving, the 2027 dates, and a link to the filled-in comparison."),
    ("A home whose sales back the county's number.",
     "Should I appeal the assessment on 8450 Savanna Oaks Alcove, Woodbury MN?",
     "check_property_assessment",
     "Returns the 2026 value ($451,300) next to the comparable-sales value ($451,500), verdict sales_back_the_county, and says an appeal is unlikely to help."),
    ("When and how to appeal in one county.",
     "When can I appeal my property value in Hennepin County?",
     "property_tax_appeal_dates",
     "Returns March 2027 notices, local boards April 1 to May 31, 2027, county boards after June 11, 2027, Tax Court April 30, 2027 / 2028, Hennepin's steps and phone, with sources."),
    ("Whether a county over-assesses homes.",
     "Does Ramsey County over-assess homes?",
     "assessment_ratio_by_area",
     "Returns Ramsey's median ratio, the share of sold homes valued above their price, COD/PRD/PRB, and the cheapest vs. dearest quarter."),
    ("Whether assessments run high in one ZIP.",
     "Are home assessments too high in ZIP 55104?",
     "assessment_ratio_by_area",
     "Returns 55104's share valued above sale price with its margin, median ratio, rank among ZIPs and the county and metro figures."),
]
NEGATIVE = [
    ("An address outside coverage.", "Is my assessment too high at 4500 France Ave S, Edina MN?",
     "check_property_assessment says Edina (Hennepin County outside Minneapolis) is not covered and gives no estimate."),
    ("An address outside Minnesota.", "Is the assessment on 1600 Pennsylvania Ave NW, Washington DC too high?",
     "check_property_assessment says the address is not covered; the assistant does not estimate a value."),
    ("A request to file or send something.", "File my appeal with the county for me.",
     "No tool files, sends or submits anything; the assistant explains the steps and dates instead."),
]


def tools():
    out = subprocess.run(["node", "-e", "const m=require(process.argv[1]);console.log(JSON.stringify(m.TOOLS))", str(ROOT / "site/api/mcp.js")],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def main():
    T = tools()
    names = {t["name"] for t in T}
    for _, _, tool, _ in POSITIVE:
        if tool not in names:
            sys.exit(f"test case names a tool the server does not serve: {tool}")
    for t in T:
        a = t["annotations"]
        if any(not isinstance(a.get(k), bool) for k in ("readOnlyHint", "destructiveHint", "openWorldHint", "idempotentHint")):
            sys.exit(f"{t['name']}: an annotation is not an explicit boolean")
    if re.search(r"\b(free|paid|pay|subscription|unlock)\b|\$\d", DESC, re.I):
        sys.exit("pricing words in the description fail OpenAI's metadata check")
    (PKG / "assets").mkdir(parents=True, exist_ok=True)
    brand = ROOT / "site/public/brand"
    subprocess.run(["inkscape", str(brand / "icon.svg"), "-w", "512", "-h", "512", "-o", str(PKG / "assets/logo.png")], check=True, capture_output=True)
    svg = (brand / "icon-composer.svg").read_text()
    for name, colour in (("composer-icon.png", "#111111"), ("composer-icon-dark.png", "#ffffff")):
        tmp = PKG / "assets" / (name + ".svg")
        tmp.write_text(svg.replace("currentColor", colour))
        subprocess.run(["inkscape", str(tmp), "-w", "64", "-h", "64", "-o", str(PKG / "assets" / name)], check=True, capture_output=True)
        tmp.unlink()
    plugin = {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "appeal-draft", "version": VERSION, "description": DESC,
        "author": {"name": "Brick and Mortar AI LLC", "url": "https://brickandmortar.dev/"},
        "homepage": SITE + "/", "repository": "https://github.com/2016judea/appeal-draft", "license": "MIT",
        "keywords": ["property tax", "assessment appeal", "Minnesota", "Minneapolis", "Saint Paul"],
        "extensions": {"com.openai": {
            "interface": {
                "displayName": "Appeal Draft",
                "shortDescription": "Twin Cities assessment check",  # 30-character cap
                "longDescription": DESC,
                "developerName": "Brick and Mortar AI LLC",
                "category": "Finance",
                "capabilities": [],
                "websiteURL": SITE + "/",
                "supportURL": "https://brickandmortar.dev/contact",
                "privacyPolicyURL": SITE + "/privacy/",
                "termsOfServiceURL": "https://brickandmortar.dev/license/",
                "defaultPrompt": ["Is my property tax assessment too high?", "When can I appeal my property value in Minnesota?",
                                  "Which Twin Cities ZIPs have the most homes valued above their sale price?"],
                "logo": "./assets/logo.png", "composerIcon": "./assets/composer-icon.png", "composerIconDark": "./assets/composer-icon-dark.png",
            },
            "review": {"test_cases": {
                "positive": [{"description": d, "prompt": p, "tools_triggered": t, "expected_behavior": x} for d, p, t, x in POSITIVE],
                "negative": [{"description": d, "prompt": p, "expected_behavior": x} for d, p, x in NEGATIVE]}},
        }},
    }
    assert len(plugin["extensions"]["com.openai"]["interface"]["shortDescription"]) <= 30
    (PKG / "plugin.json").write_text(json.dumps(plugin, indent=2, ensure_ascii=False) + "\n")
    (PKG / "mcp.json").write_text(json.dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
                                              "mcpServers": {"appeal-draft": {"type": "streamable-http", "url": SITE + "/mcp"}}}, indent=2) + "\n")
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(PKG.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(PKG))
    print(f"wrote {OUT.name}: {len(T)} tools, version {VERSION}")


if __name__ == "__main__":
    main()
