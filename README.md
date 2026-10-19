# Appeal Draft

**Live:** https://appeal-draft.vercel.app

Type a Twin Cities address. You get the county's value for the home (blue), what recorded
sales of homes like it say it is worth (green), your ZIP's sales per square foot (sand), and
one comparable sale. For $90 you get every comparable sale behind the green number and a
one-page appeal filled in with your county's form fields, steps and dates, ready to print
or save as a PDF.

The next appeal window opens with the **March 2027** valuation notices: local boards and Open
Book meetings run April 1 to May 31, 2027, county boards in June 2027. A Tax Court petition on
the 2026 value is open until April 30, 2027. Sources and read dates: `data/deadlines.json`.

Covers houses and townhouses in Ramsey, Anoka, Dakota, Scott and Washington counties and the
City of Minneapolis (618,892 homes, 48,604 recorded sales since July 2024). Not covered:
Hennepin outside Minneapolis, Carver, condos. See `DATA_MODEL.md` for every field and what
reality could not fill.

## How good is the green number

Every home that sold itself since January 2025 (30,224 of them; a home is never its own comp)
is a test: the median sale landed at 1.00× our number, and 53% sold within 10% of it. So a gap
under 10% is a phone call to the assessor, not a fight. The comp rule ignores lot size and
water frontage, so a lake lot or acreage reads too low; the page says which sales it used.
Recomputed on every build (`site/public/data/meta.json` → `backtest`).

## Price

**$90, once, per home. A hypothesis.** Among the 86,790 homes where the county sits 10% or more
above the comps and a tax bill is on the roll, the median yearly saving if the value fell to
the comp number is $954 (tax × the cut, assuming tax moves with value; it moves less). A tenth
of one year's saving is about $95; $90 is the round number under it. Measured 2026-10-19.
Counter-signal: AppealDesk sells a DIY evidence packet for $49 flat (their own comparison page,
read 2026-10-19). If round 1 shows checkout opens and no pays, $49 is the next test.

## Distribution

Round 1 is drafted, not sent: 50 recipients in `outreach/round1/` (gitignored), each with a
`/for/<token>/` page that opens on a home of their own — 40 listing agents (their live
listing), 10 small landlords (a house their LLC owns), and 5 MN appeal services on hold (no home
of their own to open on). Subject `bricks / <company>`.

A/B, the same single variable on all seven shelf products so results pool: **A** states the
price in the email, **B** leaves it to the page. Alternated within each segment; the variant
rides in `/data/for/<token>.json` and fires with `preview_open`, never in the URL.
Hypothesis: stating the price in the email lowers clicks but raises paid-per-click. Readout on
day 3: visits, checkout_open, paid and replies, by variant, by segment and pooled.

## Run it

    make build    # closed_system.duckdb (read-only) -> site/public/data + private/bundle, then the page
    make test     # pytest + node handler tests, logs/*.log
    make serve    # localhost:4321 with the API handlers
    set -a; . ~/Desktop/bricks/.env; set +a; make deploy

Only `site/public/` is served statically. The paid comp sets ride up as `api/_full/`, bundled
with `/api/data` and never under a public URL. Webhook goes through `~/Desktop/stripe-router`.
`scripts/fulfil.py` reprints a lost password or mints a comp one.

MIT licence for the code. The data is public record from the county assessors and recorded
sales; the owner name is never printed, the homeowner types it on the letter.
