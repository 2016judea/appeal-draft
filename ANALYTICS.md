# Analytics: what Appeal Draft records

Vercel Web Analytics on every page (`/_vercel/insights/script.js`) and the shared PostHog block
(`scripts/posthog_snippet.html`, events tagged `site: appeal-draft`). No address, owner name or
email is put in an event. Read with `~/.claude/skills/site-analytics` or HogQL.

## Web (`scripts/build_page.py`, `scripts/build_connector.py`)

| Event | When | Properties |
|---|---|---|
| `preview_open` | the page loaded and drew its home | `token`, `variant`, `src` |
| `home_found` / `home_not_found` | an address was looked up | `zip`, `src` |
| `override_value` | the owner typed the value from a newer notice | `set`, `src` |
| `checkout_open`, `paid`, `unlock`, `print` | the paid step | `src` (`unlock` also `via`) |
| `ratio_search`, `ratio_show_all` | `/assessment-ratio/` filter typed (length only, never the text), a table expanded | `q_len`, `hits`, `table` |

`src` is the `src` URL parameter the visit arrived with (`mcp` = a link the connector handed out,
`ratio` = from the ratio page), `direct` without one. It is also registered on the browser as
`entry`, and once as `first_src`.

## Connector (`site/api/mcp.js`)

`mcp_tool_call`, one per call: `tool`, `ok`, `ms`, `client` (claude, chatgpt, grok, cursor, script,
other), `client_ua`, `found`, `county`, `verdict`, `via` (zip, geocoder, city), `override`, `err`
(short code), `test` (the call carried `x-ad-test`). No address, no arguments.

**Count calls here, never people.** claude.ai and ChatGPT call from their own servers, so an IP or
user agent identifies the platform, not a person: the `distinct_id` is random per call on purpose.
People are counted on the web side, by `src=mcp` landings.

## The read (README `## Expectation`, 2027-04-01)

    -- people who arrived from a connector link, and how far they got
    select properties.src, event, count(distinct distinct_id)
    from events where properties.site = 'appeal-draft' and properties.src = 'mcp'
      and event in ('preview_open','home_found','checkout_open','paid') and timestamp >= '2027-03-01'
    group by 1, 2

    -- connector calls by client and verdict, test calls out
    select properties.client, properties.tool, properties.verdict, count()
    from events where event = 'mcp_tool_call' and properties.site = 'appeal-draft'
      and properties.test is null and timestamp >= '2027-03-01'
    group by 1, 2, 3 order by 4 desc
