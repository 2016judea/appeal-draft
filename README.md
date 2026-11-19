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

## Ask an AI: the connector

**MCP:** `https://appeal-draft.vercel.app/mcp` (Streamable HTTP, no auth). For the homeowner who asks
Claude or ChatGPT "is my property tax assessment too high, should I appeal?". Three read-only tools:

- `check_property_assessment`: address in; the county's value, what recorded sales of similar homes
  say, the gap, a verdict, the yearly tax a cut would save, the 2027 dates, and a link that opens this
  page filled in for that home (`/?pk=…&zip=…&sh=…&src=mcp`, plus `&v=` when the owner passes the
  value from a newer notice). No ZIP? The Census geocoder finds it; out-of-area addresses get a
  plain "not covered", never an estimate.
- `property_tax_appeal_dates`: the 2027 cycle per county, every date with its official source
  (`data/deadlines.json` → `cycle_2027`, read 2026-11-19).
- `assessment_ratio_by_area`: the fresh number below, for a ZIP, city or county.

Every number comes from the same shards and files the page reads; a model is never the source of a
number. Nothing is sold in the chat: the comp set and the letter stay on the site. Listing copy and
what needs a click: `SUBMISSION.md`. What it records: `ANALYTICS.md`.

## Assessment ratio: the fresh number

**Live:** https://appeal-draft.vercel.app/assessment-ratio/

County value ÷ sale price for 17,606 recorded sales, each tested against the value it did not go
into (sales from the October before to the June after the January 2 valuation date). 31% of homes
that sold were valued above their price; the typical home at 0.958. By ZIP the share runs from 14%
(55449, Blaine) to 47% (55130, Saint Paul) among ZIPs with 80+ sales, and the cheapest quarter of
Ramsey homes is valued above its price 49% of the time against 29% for the dearest. Every county
passes the IAAO median and COD tests; Ramsey (PRB −0.051) and Washington (−0.058) sit just past the
PRB line. `scripts/build_ratio.py` → `data/ratio.json`; the page, `llms.txt`, `llms-full.txt` and
the sitemap come from `scripts/build_connector.py`.

## Expectation

Written 2026-11-19, before the connector is in any directory.

- **Base rates.** heistclips' connector links brought 151 people in 4 days (11/16–11/19), 54% of
  whom made a clip, because clippers already ask an AI that exact question. The control, the Brick &
  Mortar business connector on the same channel, got zero human calls in 7 days. Directory review
  has taken weeks (Claude) and three rounds (ChatGPT).
- **Expected by the read date:** between now and March 2027, about zero human calls (the control's
  rate; nobody has a notice in hand). In the two weeks after notices mail: 10 to 40 people landing
  from `src=mcp` links and 0 or 1 paid, if at least one directory has listed it by then.
- **Would surprise us, upward:** 100+ `src=mcp` people by the read date, or any paid letter from a
  `src=mcp` visit before March.
- **Would surprise us, downward:** zero non-test `mcp_tool_call` events between 2027-03-15 and the
  read date while a directory lists it. That says homeowners do not take this question to an
  assistant, even on the date.
- **Read on 2027-04-01** (two weeks after mid-March notices): `mcp_tool_call` by client and verdict,
  people with `src=mcp` landings and their `checkout_open` / `paid`, and chatgpt.com / bing
  referrers on `/assessment-ratio/`. Queries: `ANALYTICS.md`.

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

    make build    # closed_system.duckdb (read-only) -> site/public/data + private/bundle, the ratio study, the pages
    make page     # just the pages (index, /assessment-ratio/, /privacy/, llms*.txt, sitemap, api/_mcp_data.json)
    make test     # pytest + node handler tests (paywall and /mcp), logs/*.log
    make serve    # localhost:4321 with the API handlers and /mcp
    set -a; . ~/Desktop/workspace/bricks/.env; set +a; make deploy   # then pings IndexNow
    python3 scripts/build_chatgpt_plugin.py   # chatgpt-plugin.zip for the ChatGPT plugin portal

Only `site/public/` is served statically. The paid comp sets ride up as `api/_full/`, bundled
with `/api/data` and never under a public URL. Webhook goes through `~/Desktop/workspace/stripe-router`.
`scripts/fulfil.py` reprints a lost password or mints a comp one.

MIT licence for the code. The data is public record from the county assessors and recorded
sales; the owner name is never printed, the homeowner types it on the letter.
