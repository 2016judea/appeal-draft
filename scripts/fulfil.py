#!/usr/bin/env python3
"""The paywall's backup, run by hand. Nothing here emails anyone.

    python3 scripts/fulfil.py cs_live_...        # a buyer lost their password: reprint it
    python3 scripts/fulfil.py --recent           # every session of ours since launch, paid or not
    python3 scripts/fulfil.py --comp             # a $0 checkout link that unlocks like a paid one (end-to-end test)
    python3 scripts/fulfil.py --comp-password X  # a comp password with no Stripe session (label X), for QA

Reads STRIPE_SECRET_KEY from ~/Desktop/bricks/.env and ACCESS_SECRET from ./.access_secret.
"""
import hashlib, hmac, json, secrets, sys
from pathlib import Path
import urllib.parse, urllib.request

ROOT = Path(__file__).resolve().parent.parent
OFFER = json.loads((ROOT / "site/offer.json").read_text())
SITE, PRODUCT = OFFER["site"], OFFER["product"]
ALPHA = "23456789BCDFGHJKMNPQRSTVWXYZ"  # same as site/api/_lib.js
LAUNCH = 1792368000


def env(path, key):
    for line in Path(path).expanduser().read_text().splitlines():
        if line.startswith(key + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{key} missing from {path}")


def stripe(path, **form):
    key = env("~/Desktop/bricks/.env", "STRIPE_SECRET_KEY")
    data = urllib.parse.urlencode(form).encode() if form else None
    r = urllib.request.Request(f"https://api.stripe.com/v1/{path}", data=data, headers={"Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"stripe: {e.read().decode()[:300]}")


def secret():
    return (ROOT / ".access_secret").read_text().strip().encode()


def chars(b, n):
    return "".join(ALPHA[x % len(ALPHA)] for x in b[:n])


def password(nonce, domain=""):
    mac = hmac.new(secret(), (domain + PRODUCT + ":" + nonce).encode(), hashlib.sha256).digest()
    raw = nonce + chars(mac, 7)
    return f"{raw[:4]}-{raw[4:8]}-{raw[8:]}"


def comp_password(label):
    nonce = chars(hmac.new(secret(), ("label:" + label).encode(), hashlib.sha256).digest(), 5)
    return password(nonce, "comp:")


def show(s):
    m = s.get("metadata") or {}
    email = (s.get("customer_details") or {}).get("email")
    print(f"{s['id']}\n  status   {s['status']} / {s['payment_status']}  ${(s.get('amount_total') or 0) / 100:.2f}"
          f"\n  email    {email}\n  password {m.get('password')}\n  link     {SITE}/?pw={m.get('password')}"
          f"\n  emailed  {m.get('pw_emailed') or 'NOT YET'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    if arg == "--recent":
        for s in stripe(f"checkout/sessions?limit=100&created[gte]={LAUNCH}")["data"]:
            if (s.get("metadata") or {}).get("product") == PRODUCT:
                show(s)
    elif arg == "--comp-password":
        label = sys.argv[2]
        print(f"{label}\n  password {comp_password(label)}\n  link     {SITE}/?pw={comp_password(label)}")
    elif arg == "--comp":
        coupon = "APPEAL-DRAFT-COMP"
        try:
            urllib.request.urlopen(urllib.request.Request(f"https://api.stripe.com/v1/coupons/{coupon}", headers={"Authorization": f"Bearer {env('~/Desktop/bricks/.env', 'STRIPE_SECRET_KEY')}"}))
        except urllib.error.HTTPError:
            stripe("coupons", id=coupon, percent_off=100, duration="once", name="Appeal Draft comp")
        nonce = "".join(secrets.choice(ALPHA) for _ in range(5))
        pw = password(nonce)
        s = stripe("checkout/sessions", **{
            "mode": "payment", "line_items[0][quantity]": 1,
            "line_items[0][price_data][currency]": "usd", "line_items[0][price_data][unit_amount]": OFFER["price_usd"] * 100,
            "line_items[0][price_data][product_data][name]": f"{OFFER['name']}: full comps and the appeal letter",
            "discounts[0][coupon]": coupon, "customer_creation": "always",
            "metadata[product]": PRODUCT, "metadata[pw_nonce]": nonce, "metadata[password]": pw, "metadata[comp]": "1",
            "success_url": f"{SITE}/?paid={{CHECKOUT_SESSION_ID}}",
        })
        print(f"comp checkout (no card, $0): {s['url']}\nsession {s['id']}  password {pw}")
    else:
        show(stripe(f"checkout/sessions/{arg}"))
