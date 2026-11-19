#!/usr/bin/env python3
"""Tell IndexNow (Bing, and ChatGPT search, Copilot and DuckDuckGo through it) that every page in the
sitemap changed. Run after each deploy (make deploy does). The key file is site/public/<key>.txt.

  python3 scripts/indexnow.py
"""
import json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "appeal-draft.vercel.app"
keys = [p.stem for p in (ROOT / "site/public").glob("*.txt") if re.fullmatch(r"[0-9a-f]{32}", p.stem) and p.read_text().strip() == p.stem]
if not keys:
    sys.exit("no IndexNow key file in site/public/")
urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "site/public/sitemap.xml").read_text())
urls += [f"https://{HOST}/llms.txt", f"https://{HOST}/llms-full.txt"]
body = json.dumps({"host": HOST, "key": keys[0], "keyLocation": f"https://{HOST}/{keys[0]}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, method="POST",
                             headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "appeal-draft-indexnow/1.0"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("indexnow", r.status, len(urls), "urls")
except urllib.error.HTTPError as e:
    print("indexnow", e.code, e.read()[:200])
    sys.exit(1 if e.code >= 400 and e.code != 429 else 0)
