# Connector listing kit: Appeal Draft

Copy from here. Pattern and rejection history: `~/Desktop/workspace/small-business-intelligence-mcp/SUBMISSION-KIT.md`;
the last filing run end to end: `~/Desktop/workspace/heistclips/SUBMISSION.md`. **Filed 2026-11-19: see "Submitted 2026-11-19" at the end.**

| Field | Value |
|---|---|
| Name | Appeal Draft |
| Endpoint | `https://appeal-draft.vercel.app/mcp` · Streamable HTTP · auth none · no UI |
| Publisher | Brick and Mortar AI LLC, 1651 Eleanor Ave, Saint Paul, MN 55116 |
| Website / docs | https://appeal-draft.vercel.app/ · https://appeal-draft.vercel.app/llms.txt |
| Privacy | https://appeal-draft.vercel.app/privacy/ |
| Terms | https://brickandmortar.dev/license/ |
| Support | aidan@brickandmortar.dev (ChatGPT wants a URL: https://brickandmortar.dev/contact) |
| Source | https://github.com/2016judea/appeal-draft |
| Icon | https://appeal-draft.vercel.app/brand/icon.svg · `icon.png` (512) · `icon-256.png` · composer `icon-composer.svg` |
| OpenAI domain challenge | Vercel env `OPENAI_APPS_CHALLENGE` → `/.well-known/openai-apps-challenge` (404 until set) |
| ChatGPT package | `chatgpt-plugin.zip` (`python3 scripts/build_chatgpt_plugin.py`; bump `VERSION` per upload) |

## One-liner (≤100)
Is my Twin Cities property tax assessment too high? County value vs. recorded sales, and when to appeal

## Description
For a homeowner in the Minneapolis–Saint Paul area deciding whether to appeal. Give it an address
and it returns the county's value, what recorded sales of similar nearby homes say the home is
worth, the gap, whether an appeal looks worth filing, about how much a cut would save in tax each
year, and the county's appeal steps with the 2027 dates, each with its official source. It also
gives the assessment ratio (county value ÷ sale price) by ZIP, city and county. Every number comes
from county assessor rolls and recorded sales. Covers houses and townhouses in Ramsey, Anoka,
Dakota, Scott and Washington counties and the City of Minneapolis. No account.

(For ChatGPT use `DESC` in `scripts/build_chatgpt_plugin.py`: no pricing words, which fail the metadata check.)

## Connection requirements
None: no account, key or OAuth. Coverage is houses and townhouses in Ramsey, Anoka, Dakota, Scott
and Washington counties and the City of Minneapolis; any other address gets a plain "not covered",
which is correct behaviour, not a fault. When no ZIP is given the address goes to the U.S. Census
Bureau's public geocoder.

## Annotations (explicit booleans; `tests/mcp.test.js` holds them)
| Tool | readOnly | destructive | openWorld | idempotent |
|---|---|---|---|---|
| check_property_assessment, property_tax_appeal_dates, assessment_ratio_by_area | true | false | true | true |

openWorld is true because the address lookup reaches the Census geocoder.

## Test cases (run against the live endpoint, see the report of 2026-11-19)
1. "Is the property tax assessment on 1852 Ashland Ave, St Paul MN 55104 too high? Should I appeal?" → check_property_assessment: 2025 value $616,500 vs. $477,500 from 5 sales, 29%, worth_appealing.
2. "Should I appeal the assessment on 8450 Savanna Oaks Alcove, Woodbury MN?" → $451,300 vs. $451,500, sales_back_the_county.
3. "When can I appeal my property value in Hennepin County?" → property_tax_appeal_dates.
4. "Does Ramsey County over-assess homes?" → assessment_ratio_by_area: 37% of sold homes valued above price; cheapest quarter 49% vs. dearest 29%.
5. "Are home assessments too high in ZIP 55104?" → assessment_ratio_by_area.

Negative: "4500 France Ave S, Edina" → not covered (Hennepin outside Minneapolis), no estimate;
"1600 Pennsylvania Ave NW, Washington DC" → not covered; "File my appeal with the county for me" → no tool files anything.

Test addresses are homes the public page itself opens on or a random covered home; keep them out of
anything public (starter prompts carry no address).

## Starter prompts
- Is my property tax assessment too high?
- When can I appeal my property value in Minnesota?
- Which Twin Cities ZIPs have the most homes valued above their sale price?

## What needed Aidan's click (superseded: all filed 2026-11-19, see below)

1. **Claude Connectors Directory** (claude.ai/directory, "submit a connector"). The portal makes the
   server a custom connector in his Claude first: Settings → Connectors → Add custom connector →
   `https://appeal-draft.vercel.app/mcp`. Then the form: name, one-liner and description above;
   categories Finance, Data & Analytics; privacy and docs URLs above; prerequisites none; "Read
   only" (all three tools are read-only); company Brick and Mortar AI LLC; data handling "We own the
   API" (public county records; the geocoder is the Census Bureau's public service). Use cases =
   test cases 1, 3 and 4. **He presses Submit.**
2. **ChatGPT plugin portal** (platform.openai.com/plugins, signs in with Google + his passkey). New
   plugin → upload `chatgpt-plugin.zip` → publisher "Business — Brick and Mortar AI LLC". The portal
   shows a domain token: put it in Vercel env `OPENAI_APPS_CHALLENGE` (I can do that and redeploy
   once he pastes it), then Verify. MCP tab: connect, no auth. Demo recording: Developer mode works
   on the Free plan (heistclips 11/16). Six attestations, then **he presses Submit**; after the
   approval email **he presses Publish** (approval does not publish).
3. Optional, no gate: Official MCP Registry (`mcp-publisher`, GitHub device login, JWT expires in
   under an hour) and Glama. Grok's form and mcp.so need no sign-in but each is still a submission.

## Submitted 2026-11-19

Filed by Claude in Aidan's own Chrome (JavaScript run by process id into his signed-in tabs). His screen was
locked, so a copied Chrome profile could not decrypt his cookies and was not used. Nothing was paid, nothing
was sent to a person, nothing was published. Each status below was read back off the portal after filing.

| Where | Status | UTC | Listing / ID |
|---|---|---|---|
| Official MCP Registry | **LISTED**, active | 22:28 | `io.github.2016judea/appeal-draft` 1.0.0 |
| Claude Connectors Directory | **READY TO PUBLISH** (approved within minutes) | 22:45 | claude.ai/directory/manage/appeal-draft · slug `appeal-draft` (permanent) |
| ChatGPT plugin directory | **1.0.0 IN REVIEW**, estimated completion Dec 2, 2026 | 23:33 | `plugin_asdk_app_6aff788c121481918c605466c4e3fed7` |

**What needs Aidan**
- **Claude:** click **Publish** at claude.ai/directory/manage/appeal-draft. Approval does not publish it.
- **ChatGPT:** when the approval email comes, click **Publish** at
  platform.openai.com/plugins/manage/plugin_asdk_app_6aff788c121481918c605466c4e3fed7. Leave Vercel env
  `OPENAI_APPS_CHALLENGE` set: OpenAI re-checks it.

**Official MCP Registry.** No device code needed. `server.json` plus `.github/workflows/mcp-registry.yml`
publish over GitHub Actions OIDC (`mcp-publisher login github-oidc`), which proves the repo owner and grants
`io.github.2016judea/*`. It runs when `server.json` changes on `master`; bump `version` there to republish.
Check: `curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=io.github.2016judea/appeal-draft"`.

**Claude, what was filed.** Custom connector "Appeal Draft" added to his Claude (Settings → Connectors). The
first one was deleted and re-added after a server change, because the portal caches the tool list it read at
connect time. Name, one-liner and description are verbatim from this kit. Categories: Financial Services, Data &
Analytics. Author: Brick and Mortar AI LLC (https://appeal-draft.vercel.app/). Docs `/llms.txt`, support
aidan@brickandmortar.dev, privacy `/privacy/`, custom icon `/brand/icon.svg` (`/favicon.ico` 404s). Use cases are
test cases 1, 3 and 4. Prerequisites: none. Read only. Company Brick and Mortar AI LLC, https://brickandmortar.dev,
Aidan Jude, Founder. Auth none (detected). Data handling: "We own the API", no health data, no sponsored content.
All seven compliance boxes ticked. The reviewer note names the Census geocoder as the one outside call.
- **Server change made for this filing (commit a4ed6d5, deployed):** `check_property_assessment`'s description
  ended "...; always show it." The compliance step attests that tool descriptions hold no instructions about model
  behavior, so it now ends at the link sentence. The instruction stays in the server `instructions`, which is
  where it belongs.

**ChatGPT, what was filed.** `chatgpt-plugin.zip` 1.0.0 as built, publisher **Business — Brick and Mortar AI LLC**.
- **Domain:** token in Vercel env `OPENAI_APPS_CHALLENGE` (all targets), production redeployed; the route serves
  it and the portal shows "Domain verified". MCP connected, no auth, 3 tools.
- **Findings:** one non-blocking metadata finding ("Review the plugin's privacy policy against the submission
  guidelines") and the generic "new tool definition needs further review" on `check_property_assessment`. The
  private review note answers the privacy one, and says plainly that the site sells an optional comparable-sales
  packet while nothing is sold or priced inside ChatGPT. **If a rejection cites in-app commerce, that is the
  soft spot.**
- **Review information:** the ZIP supplies the 5 + 3 test cases. Demo URL and release notes were entered in the
  portal (the ZIP carries no `demo_recording_url`; add it to `build_chatgpt_plugin.py` before the next upload).
- **Demo:** https://cf546sdmyewh8fpm.public.blob.vercel-storage.com/demo/appeal-draft-chatgpt-review.mp4 (Vercel
  Blob, heistclips store, not in the repo). 2 min 47 s, 1536×742, the 8 test cases each in a fresh developer-mode
  chat with the plugin attached by `@Appeal Draft`. His screen was locked, so the frames were rendered from the
  live ChatGPT tab in-page (modern-screenshot 4.6.0) and stitched with ffmpeg. ChatGPT greets him as "Aidan" in a
  few frames. This added a developer-mode plugin "Appeal Draft" to his ChatGPT.
- **Submitted** with the same six attestations as heistclips and Appeal the Denial.

