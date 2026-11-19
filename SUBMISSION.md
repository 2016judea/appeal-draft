# Connector listing kit: Appeal Draft

Copy from here. Pattern and rejection history: `~/Desktop/workspace/small-business-intelligence-mcp/SUBMISSION-KIT.md`;
the last filing run end to end: `~/Desktop/workspace/heistclips/SUBMISSION.md`. **Nothing here has been submitted.**

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

## What needs Aidan's click (none of it done)

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
