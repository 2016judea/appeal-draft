#!/usr/bin/env python3
"""Create (once), configure and deploy site/ to Vercel production over the REST API (no CLI).

  python3 scripts/deploy.py --setup   # create the project, env vars, analytics, public (idempotent)
  python3 scripts/deploy.py           # deploy site/ + private/bundle/ (as api/_full/), wait for READY

Needs VERCEL_TOKEN, STRIPE_SECRET_KEY, MAILGUN_API_KEY, MAILGUN_DOMAIN, MAILGUN_FROM in the environment
(`set -a; . ~/Desktop/bricks/.env; set +a`). ACCESS_SECRET is generated once into .access_secret (gitignored).
The paid comp sets ride up as api/_full/comps/*.json.gz, bundled with /api/data and redirected away from
any public URL by site/vercel.json.
"""
import hashlib, json, os, secrets, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"
BUNDLE = REPO / "private/bundle"
OFFER = json.loads((SITE / "offer.json").read_text())
PROJECT = OFFER["product"]
TEAM = "team_XnhPzBEcaSfEmZFo9M2isLFY"
API = "https://api.vercel.com"
SKIP = {".git", "node_modules", ".vercel", "__pycache__", ".DS_Store", ".env", "_full"}


def req(method, url, token, body=None, headers=None, raw=None):
    h = {"Authorization": f"Bearer {token}"}
    h.update(headers or {})
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    if body is not None:
        h["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=h, method=method)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(r, timeout=120) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(2 + attempt * 3)  # Errno 51 is transient here; retry
    sys.exit(f"network failed: {url}")


def setup(token):
    code, p = req("GET", f"{API}/v9/projects/{PROJECT}?teamId={TEAM}", token)
    if code == 404:
        code, p = req("POST", f"{API}/v10/projects?teamId={TEAM}", token, {"name": PROJECT, "framework": None})
        print("created project", code, p.get("id"))
    pid = p["id"]
    sec_file = REPO / ".access_secret"
    if not sec_file.exists():
        sec_file.write_text(secrets.token_hex(32))
    env = {"STRIPE_SECRET_KEY": os.environ["STRIPE_SECRET_KEY"], "ACCESS_SECRET": sec_file.read_text().strip(),
           "SITE_URL": OFFER["site"], **{k: os.environ[k] for k in ("MAILGUN_API_KEY", "MAILGUN_DOMAIN", "MAILGUN_FROM")}}
    for k, v in env.items():
        c, out = req("POST", f"{API}/v10/projects/{pid}/env?teamId={TEAM}&upsert=true", token,
                     {"key": k, "value": v, "type": "encrypted", "target": ["production", "preview"]})
        print("env", k, c)
    c, out = req("POST", f"{API}/web/insights/toggle?projectId={pid}&teamId={TEAM}", token, {"value": True})
    print("analytics", c, out)
    c, out = req("PATCH", f"{API}/v9/projects/{pid}?teamId={TEAM}", token, {"ssoProtection": None})
    print("public", c)
    _, p = req("GET", f"{API}/v9/projects/{PROJECT}?teamId={TEAM}", token)
    print("aliases", (p.get("targets", {}).get("production") or {}).get("alias"), "analytics", (p.get("webAnalytics") or {}).get("enabledAt"))


def upload(token, item):
    p, rel = item
    b = p.read_bytes()
    sha = hashlib.sha1(b).hexdigest()
    c, out = req("POST", f"{API}/v2/files?teamId={TEAM}", token, raw=b,
                 headers={"Content-Type": "application/octet-stream", "x-vercel-digest": sha})
    if c >= 400:
        sys.exit(f"upload {rel} failed: {c} {out}")
    return {"file": rel, "sha": sha, "size": len(b)}


def deploy(token):
    assert (SITE / "public/index.html").exists(), "run scripts/build_page.py first"
    assert (SITE / "public/data/meta.json").exists() and any(BUNDLE.glob("comps/*.json.gz")), "run scripts/build.py first"
    paths = [(p, str(p.relative_to(SITE))) for p in sorted(SITE.rglob("*")) if p.is_file() and not any(x in SKIP for x in p.relative_to(SITE).parts)]
    paths += [(p, "api/_full/" + str(p.relative_to(BUNDLE))) for p in sorted(BUNDLE.rglob("*")) if p.is_file()]
    with ThreadPoolExecutor(12) as ex:
        files = list(ex.map(lambda it: upload(token, it), paths))
    print(f"  {len(files)} files, {sum(f['size'] for f in files):,} bytes")
    c, out = req("POST", f"{API}/v13/deployments?teamId={TEAM}&skipAutoDetectionConfirmation=1&forceNew=1", token,
                 {"name": PROJECT, "project": PROJECT, "target": "production", "files": files,
                  "projectSettings": {"framework": None, "buildCommand": "echo build", "outputDirectory": "public", "installCommand": "echo skip"}})
    if c >= 400 or out.get("error"):
        sys.exit(f"create failed: {c} {json.dumps(out.get('error'))}")
    url = out["url"]
    print(f"  deploying https://{url}")
    for _ in range(120):
        time.sleep(3)
        _, d = req("GET", f"{API}/v13/deployments/{url}?teamId={TEAM}", token)
        s = d.get("readyState")
        if s in ("READY", "ERROR", "BLOCKED", "CANCELED"):
            print(f"  {s} {d.get('errorMessage') or ''}")
            sys.exit(0 if s == "READY" else 1)
    sys.exit("timed out")


if __name__ == "__main__":
    tok = os.environ.get("VERCEL_TOKEN") or sys.exit("VERCEL_TOKEN is not set")
    setup(tok) if "--setup" in sys.argv else deploy(tok)
