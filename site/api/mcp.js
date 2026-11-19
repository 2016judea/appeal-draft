// MCP server at /mcp (site/vercel.json rewrites it here). Streamable HTTP, stateless JSON responses.
// The homeowner asks an assistant "is my property tax assessment too high, should I appeal?"; this
// does the step in the chat and hands back a link that opens the page already filled in (src=mcp).
//
// Every number comes from the same files the page reads: the county roll and the comp rule in the
// public ZIP shards (/data/zip/<zip>-<shard>.json, built by scripts/build.py), and _mcp_data.json
// (scripts/build_connector.py: the ratio study, the dates, the city index). A model is never the
// source of a number. Nothing is sold in the chat: the paid comp set stays on the site.
//
// Annotations: all three hints set explicitly (OpenAI rejects a null one); openWorldHint true because
// the address lookup reaches the Census geocoder.
const crypto = require("crypto");
const D = require("./_mcp_data.json");

const SITE = "https://appeal-draft.vercel.app";
const VERSION = "1.0.0";
const PH_KEY = "phc_yFgRGppL6H7DvhgZTQKbHdrY5oqnpLT482rrNYtLqnAx"; // public project key, same as the page
const ANN = { readOnlyHint: true, destructiveHint: false, openWorldHint: true, idempotentHint: true };
const COVERED = "houses and townhouses in Ramsey, Anoka, Dakota, Scott and Washington counties and the City of Minneapolis";
const C27 = D.deadlines.cycle_2027;

const TOOLS = [
  {
    name: "check_property_assessment",
    title: "Is my property tax assessment too high? Should I appeal? (Twin Cities, Minnesota)",
    description: "For one home in the Minneapolis-Saint Paul area: the county's estimated market value, what recorded sales of similar nearby homes say it is worth, the gap between them, whether an appeal looks worth filing, the yearly tax a cut would save, and the county's appeal steps and 2027 dates. Use for 'is my property tax assessment too high', 'should I appeal my property value', 'my assessment went up, is it fair', 'what is my house assessed at vs what it would sell for'. Covers " + COVERED + "; any other address gets an honest 'not covered'. Pass the street address with its city or ZIP. If the user has a newer valuation notice, pass its estimated market value as value_on_notice. Returns a link that opens the comparison on appeal-draft.vercel.app already filled in for that home; always show it.",
    inputSchema: { type: "object", properties: {
      address: { type: "string", description: "Street address, ideally with city and ZIP, e.g. '1852 Ashland Ave, Saint Paul, MN 55104'" },
      zip: { type: "string", description: "5-digit ZIP, if not in the address" },
      city: { type: "string", description: "City, if not in the address" },
      value_on_notice: { type: "integer", minimum: 20000, description: "Optional: the estimated market value printed on the owner's newest valuation notice, used instead of the value on our roll" },
    }, required: ["address"], additionalProperties: false },
    annotations: { title: "Check a property assessment", ...ANN },
  },
  {
    name: "property_tax_appeal_dates",
    title: "Minnesota property tax appeal dates and steps (2027 valuation notices, open book, local and county boards, Tax Court)",
    description: "When Minnesota valuation notices mail, when open book and Local Board of Appeal and Equalization meetings run, when the County Board meets and when the Tax Court deadline falls, each with its official source, plus the county's own steps and assessor phone for Hennepin (Minneapolis), Ramsey, Anoka, Dakota, Scott and Washington. Use for 'when can I appeal my property taxes', 'what is the deadline to appeal my assessment in Minnesota', 'when do 2027 valuation notices come out'. Minnesota only.",
    inputSchema: { type: "object", properties: {
      county: { type: "string", description: "Optional: a Minnesota county, e.g. 'Ramsey' or 'Hennepin'" },
    }, additionalProperties: false },
    annotations: { title: "Appeal dates", ...ANN },
  },
  {
    name: "assessment_ratio_by_area",
    title: "Does the county over-assess homes here? Assessment ratio by ZIP, city or county (Twin Cities)",
    description: "The assessment ratio (county value / sale price) for recorded home sales in a Twin Cities ZIP, city or county: the share of sold homes the county valued above their sale price, the median ratio, and how it ranks against the rest of the metro, plus the IAAO uniformity measures by county and the gap between cheaper and dearer homes. Use for 'does Ramsey County over-assess homes', 'are assessments too high in 55104', 'how accurate are property assessments in Roseville'. Covers " + COVERED + ".",
    inputSchema: { type: "object", properties: {
      area: { type: "string", description: "A ZIP (55104), a city (Roseville, Saint Paul) or a county (Ramsey)" },
    }, required: ["area"], additionalProperties: false },
    annotations: { title: "Assessment ratio by area", ...ANN },
  },
];

const INSTRUCTIONS = "Appeal Draft answers 'is my property tax assessment too high, and should I appeal?' for homes in the Minneapolis-Saint Paul area (" + COVERED + "). Use check_property_assessment with the user's address: it returns the county's value, what recorded sales of similar homes say, the gap, a verdict, and a link that opens the comparison filled in for that home; always show that link. Use property_tax_appeal_dates for when and how to appeal in Minnesota, and assessment_ratio_by_area for whether the county tends to over-assess a ZIP, city or county. Quote numbers exactly as returned, with their year; never estimate a value yourself. Outside the covered area, say plainly that the address is not covered.";

// Every link the connector hands out carries src=mcp, so visits from it are countable on the site.
function tag(url) {
  url = String(url);
  if (!url.startsWith(SITE) || /[?&]src=/.test(url)) return url;
  const i = url.indexOf("#"), base = i < 0 ? url : url.slice(0, i), hash = i < 0 ? "" : url.slice(i);
  return base + (base.includes("?") ? "&" : "?") + "src=mcp" + hash;
}

// ---- address matching: the page's findRow (scripts/build_page.py), stricter on the street name ----
const ABBR = { street: "st", avenue: "ave", av: "ave", road: "rd", drive: "dr", lane: "ln", court: "ct", circle: "cir", boulevard: "blvd", place: "pl", terrace: "ter", trail: "trl", parkway: "pkwy", highway: "hwy", north: "n", south: "s", east: "e", west: "w", northeast: "ne", northwest: "nw", southeast: "se", southwest: "sw", saint: "st" };
const GENERIC = new Set(["st", "ave", "rd", "dr", "ln", "ct", "cir", "blvd", "pl", "ter", "trl", "pkwy", "hwy", "way", "n", "s", "e", "w", "ne", "nw", "se", "sw", "mn", "minnesota", "unit", "apt"]);
const norm = (s) => String(s).toLowerCase().replace(/[.,#]/g, " ").replace(/\s+/g, " ").trim().split(" ").filter(Boolean).map((w) => ABBR[w] || w);
const normCity = (c) => String(c || "").toLowerCase().replace(/[.,]/g, " ").replace(/\bst\b/g, "saint").replace(/\s+/g, " ").trim();
const shardOf = (a) => { const m = String(a).trim().match(/^\d/); return m ? m[0] : "0"; };

function parseAddress(address, zip, city) {
  const raw = String(address || "").trim();
  const parts = raw.split(",").map((s) => s.trim()).filter(Boolean);
  const z = (String(zip || "").match(/\b\d{5}\b/) || raw.match(/\b(5[56]\d{3})(?:-\d{4})?\b\s*$/) || raw.match(/\b(5[56]\d{3})\b/) || [])[0];
  let street = parts[0] || raw;
  street = street.replace(/\b(5[56]\d{3})(-\d{4})?\b/g, "").replace(/\b(mn|minnesota)\b\.?/gi, "").trim();
  let c = city || (parts.length > 1 ? parts[1].replace(/\b(mn|minnesota)\b.*$/i, "").replace(/\d{5}.*/, "").trim() : "");
  return { raw, street, zip: z ? z.slice(0, 5) : "", city: c };
}

function scoreRow(row, t, num, words, need) {
  const a = norm(row[1]);
  if (a[0] !== num) return 0;
  const rest = a.slice(1);
  if (need && !rest.includes(need)) return 0;
  let s = 1;
  for (const w of words) if (rest.includes(w)) s += 2;
  if (words.length && rest[0] && words.includes(rest[0])) s += 3;
  return s;
}

function findIn(rows, street, cityWanted) {
  const t = norm(street);
  const num = t.find((w) => /^\d+[a-z]?$/.test(w));
  if (!num) return { err: "no_number" };
  const words = t.filter((w) => w !== num && !/^\d{5}$/.test(w));
  const need = words.find((w) => !GENERIC.has(w));
  let best = null, bs = 0;
  for (const r of rows) {
    if (cityWanted && normCity(r[2]) !== cityWanted) continue;
    const s = scoreRow(r, t, num, words, need);
    if (s > bs) { bs = s; best = r; }
  }
  return best && bs >= 3 ? { row: best, score: bs } : { err: "not_found" };
}

// ---- data: the same public shards the page fetches ----
const SHARDS = new Map();
async function shard(base, zip, sh) {
  const k = zip + "-" + sh;
  if (SHARDS.has(k)) return SHARDS.get(k);
  let d = null;
  if (process.env.ZIP_DIR) {
    const fs = require("fs"), path = require("path");
    const f = path.join(process.env.ZIP_DIR, k + ".json");
    d = fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, "utf8")) : null;
  } else {
    const r = await fetch(`${base}/data/zip/${k}.json`, { signal: AbortSignal.timeout(6000) });
    d = r.ok ? await r.json() : null;
  }
  if (SHARDS.size > 200) SHARDS.clear();
  SHARDS.set(k, d);
  return d;
}

// The Census Bureau's public geocoder: ZIP, state and county for an address with no ZIP, and the
// county for one we cannot find (so an out-of-area answer names where it is).
async function geocode(q) {
  if (process.env.AD_NO_GEOCODE) return null;
  try {
    const u = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress?benchmark=Public_AR_Current&vintage=Current_Current&layers=Counties&format=json&address=" + encodeURIComponent(q);
    const r = await fetch(u, { signal: AbortSignal.timeout(4500) });
    if (!r.ok) return null;
    const m = ((await r.json()).result || {}).addressMatches || [];
    if (!m.length) return { matched: false };
    const a = m[0].addressComponents || {}, c = ((m[0].geographies || {}).Counties || [])[0] || {};
    return { matched: true, address: m[0].matchedAddress, zip: a.zip, state: a.state, city: a.city, county: String(c.BASENAME || c.NAME || "").replace(/ County$/, "") };
  } catch (e) { return null; }
}

const money = (n) => (n == null ? null : "$" + Math.round(n).toLocaleString("en-US"));
const pctS = (x) => Math.round(Math.abs(x) * 100) + "%";

function areaRatio(zip, county, city) {
  const R = D.ratio;
  const z = R.zips.find((x) => x.zip === zip);
  const c = R.cities.find((x) => x.county === county && normCity(x.city) === normCity(city));
  const k = R.counties[county];
  const one = (x, label) => x && { area: label, sales: x.n, share_valued_above_sale_price: x.above, median_ratio: x.median };
  return {
    what: "Assessment ratio = county value / sale price, for recorded sales the county's value had not seen. Above 1.00 means valued above the price.",
    zip: one(z, "ZIP " + zip), city: one(c, city), county: one(k, D.counties[county] && D.counties[county].name + " County" + (county === "hennepin" ? " (Minneapolis)" : "")),
    metro: one(R.all, "all covered areas"),
    page: tag(SITE + "/assessment-ratio/"),
  };
}

function datesFor(county) {
  const c = county && D.deadlines.counties[county];
  return {
    right_now: C27.right_now,
    valuation_notices: C27.notices.when + ". " + C27.notices.rule,
    local_board_or_open_book: C27.local_boards.when + ". " + C27.local_boards.rule,
    county_board: C27.county_boards.when + ". " + C27.county_boards.rule,
    tax_court: `${C27.tax_court.for_2026_value} for the 2026 value; ${C27.tax_court.for_2027_value} for the 2027 value. ${C27.tax_court.rule}`,
    county_steps: c ? c.steps : undefined,
    assessor_phone: c ? c.assessor_phone : undefined,
    county_page: c ? c.url : undefined,
    sources: [...C27.notices.sources, ...C27.local_boards.sources, ...C27.county_boards.sources, ...C27.tax_court.sources].map((s) => s.url).filter((u, i, a) => a.indexOf(u) === i),
    read_on: C27.read_on,
  };
}

const notCovered = (where, extra = {}) => ({
  found: false, covered: false,
  message: `Appeal Draft covers ${COVERED}. ${where} is not covered, so there is no comparison to give. Say so plainly; do not estimate a value.`,
  ...extra,
});

async function checkAssessment(args, base, log) {
  const p = parseAddress(args.address, args.zip, args.city);
  const tn = norm(p.street);
  if (!tn.some((w) => /^\d+[a-z]?$/.test(w))) { log.err = "no_number"; return { found: false, message: "Ask for the street address with its house number, like '1234 Maple St, Saint Paul'." }; }
  const sh = shardOf(p.street);
  let zip = p.zip, hit = null, geo = null;
  log.via = zip ? "zip" : "none";
  const tryZip = async (z, cityWanted) => {
    const d = await shard(base, z, sh);
    if (!d) return null;
    const f = findIn(d.homes, p.street, cityWanted);
    return f.row ? { d, row: f.row, zip: z, score: f.score } : null;
  };
  if (zip) hit = await tryZip(zip);
  if (!hit) {
    geo = await geocode([p.street, p.city, zip, "MN"].filter(Boolean).join(", "));
    if (geo && geo.matched) {
      if (geo.state && geo.state !== "MN") { log.err = "out_of_state"; return notCovered(`${geo.address} (${geo.state})`, { matched_address: geo.address }); }
      const ck = geo.county.toLowerCase();
      if (!D.counties[ck]) { log.err = "out_of_area"; log.county = ck.slice(0, 20); return notCovered(`${geo.address}, in ${geo.county} County,`, { matched_address: geo.address, county: geo.county + " County", appeal_dates: datesFor(null) }); }
      if (geo.zip && geo.zip !== zip) { log.via = "geocoder"; hit = await tryZip(geo.zip); }
      if (!hit && ck === "hennepin" && normCity(geo.city) !== "minneapolis") { log.err = "out_of_area"; log.county = "hennepin"; return notCovered(`${geo.address} is in Hennepin County outside Minneapolis, which`, { matched_address: geo.address, county: "Hennepin County", appeal_dates: datesFor("hennepin") }); }
    }
  }
  if (!hit && p.city) {
    const zs = D.cities[normCity(p.city)] || [];
    if (zs.length) {
      log.via = "city";
      const res = (await Promise.all(zs.map((z) => tryZip(z, normCity(p.city))))).filter(Boolean).sort((a, b) => b.score - a.score);
      hit = res[0] || null;
    }
  }
  if (!hit) {
    log.err = "not_found";
    return { found: false, covered: geo && geo.matched ? true : undefined, matched_address: geo && geo.matched ? geo.address : undefined,
      message: `No house or townhouse at "${p.street}"${zip ? " in " + zip : ""}${p.city ? ", " + p.city : ""} in our records. Appeal Draft covers ${COVERED}; condos are not covered. Check the house number and street, or pass the ZIP from the tax statement.`,
      try_on_the_site: tag(SITE + "/") };
  }
  const { d, row } = hit;
  const [pk, addr, city, sf, yb, emv0, prior, tax, hs, ay, target, ppsf, ncomps, first, ownD, ownP, pin] = row;
  const county = d.county, cty = D.counties[county];
  const override = args.value_on_notice && args.value_on_notice > 20000 ? Math.round(args.value_on_notice) : null;
  const emv = override || emv0;
  let verdict = "not_enough_sales", gap = null;
  if (target) { gap = emv / target - 1; verdict = gap < D.thresholds.backs_below ? "sales_back_the_county" : gap < D.thresholds.argue_from ? "worth_a_call" : "worth_appealing"; }
  const saving = tax && target && target < emv ? Math.round((tax * (1 - target / emv)) / 10) * 10 : 0;
  const zv = d.ppsf ? Math.round((d.ppsf * sf) / 100) * 100 : null;
  const SAY = {
    worth_appealing: `Worth appealing. The county's value is ${gap != null ? pctS(gap) : ""} above what recorded sales of similar homes support. Ask the board for ${money(target)}.`,
    worth_a_call: `A little high: ${gap != null ? pctS(gap) : ""} above the sales. Worth a call to the assessor before any board; a gap under 10% is a phone call, not a fight.`,
    sales_back_the_county: `Sales back the county's number${gap != null && gap < 0 ? ` (it is ${pctS(gap)} under them)` : ""}. An appeal is unlikely to help.`,
    not_enough_sales: "Fewer than 3 sales of similar homes within 2 miles since July 2024, so there is not enough to say.",
  };
  log.found = true; log.county = county; log.verdict = verdict; log.override = !!override;
  const link = tag(`${SITE}/?pk=${encodeURIComponent(pk)}&zip=${hit.zip}&sh=${d.shard}` + (override ? `&v=${override}` : ""));
  return {
    found: true,
    home: { address: `${addr}, ${city}, MN ${hit.zip}`, county: cty.name + " County" + (county === "hennepin" ? " (Minneapolis)" : ""), parcel_id: pin, finished_sq_ft: sf, year_built: yb, homestead: !!hs },
    county_value: { amount: emv, from: override ? "the owner's valuation notice" : `${ay} assessment, taxes payable ${ay + 1}`, roll_value: emv0, assessment_year: ay,
      prior_year: prior || null, change_from_prior_year: prior ? Math.round((emv0 / prior - 1) * 1000) / 10 + "%" : null,
      note: !override && ay < 2026 ? `This is the ${ay} value. The ${ay + 1} value (notice mailed March ${ay + 1}, also on the November proposed-tax notice) is not in our records; pass it as value_on_notice to compare that instead.` : undefined },
    sales_of_similar_homes_say: target ? { amount: target, how: `median $${Math.round(ppsf)}/sq ft across ${ncomps} recorded sales of similar homes (within 25% of the size, 25 years of the age, 2 miles), times ${sf.toLocaleString("en-US")} sq ft` } : null,
    one_comparable_sale: first ? { address: `${first[0]}, ${first[1]}`, sold: first[2], price: first[3], sq_ft: first[4], miles_away: first[5] } : null,
    zip_market: zv ? { amount: zv, how: `median $${Math.round(d.ppsf)}/sq ft over ${d.n_sales} sales in ${hit.zip} since ${D.sales_since.slice(0, 7)}, times the home's sq ft` } : null,
    gap: gap != null ? Math.round(gap * 1000) / 10 + "%" : null,
    verdict, says: SAY[verdict],
    yearly_tax_saving_if_cut: saving ? { amount: saving, how: `the ${money(tax)} bill times the cut, assuming tax moves with value (it moves less)` } : null,
    own_purchase: ownD && ownP ? { date: ownD, price: ownP } : null,
    how_reliable: D.backtest && D.backtest.n ? `Tested on ${D.backtest.n.toLocaleString("en-US")} homes that sold since January 2025 (never their own comp): ${Math.round(D.backtest.within_10pct * 100)}% sold within 10% of the comparable-sales number. Lot size and water frontage are not in the comparison, so a lake lot or acreage reads low.` : undefined,
    area_assessment_ratio: areaRatio(hit.zip, county, city),
    when_to_appeal: datesFor(county),
    open_the_comparison: link,
    on_that_page: "The same comparison drawn out, with the full set of comparable sales and a one-page appeal filled in for the county's board.",
  };
}

function ratioFor(args) {
  const q = String(args.area || "").trim(), R = D.ratio;
  const z = (q.match(/\b\d{5}\b/) || [])[0];
  const fmt = (x) => ({ sales: x.n, share_valued_above_sale_price: x.above, margin_90pct: x.above_moe, median_ratio: x.median });
  if (z) {
    const i = R.zips.findIndex((x) => x.zip === z);
    if (i < 0) return { found: false, message: D.zip_county[z] ? `ZIP ${z} has fewer than 30 qualifying sales, too few to give a ratio. Try its city or county.` : `ZIP ${z} is not covered. Appeal Draft covers ${COVERED}.`, page: tag(SITE + "/assessment-ratio/") };
    const x = R.zips[i];
    return { found: true, area: `ZIP ${z} (${x.city})`, ...fmt(x), rank: `${i + 1} of ${R.zips.length} ZIPs by share valued above sale price (1 = highest)`, county: R.counties[x.county] && { name: D.counties[x.county].name, ...fmt(R.counties[x.county]) }, metro: fmt(R.all), method: method(), page: tag(SITE + "/assessment-ratio/") };
  }
  const k = q.toLowerCase().replace(/\s+county$/, "").trim();
  const ck = Object.keys(D.counties).find((c) => c === k);
  if (ck) {
    const x = R.counties[ck];
    return { found: true, area: D.counties[ck].name + " County" + (ck === "hennepin" ? " (Minneapolis only)" : ""), ...fmt(x), assessment_year: x.assessment_year, sales_window: `${x.sales_from} to ${x.sales_to}`,
      uniformity: { cod: x.cod, prd: x.prd, prb: x.prb, targets: "IAAO for homes: median 0.90-1.10, COD 5-15, PRD 0.98-1.03, PRB within +/-0.05" },
      cheaper_vs_dearer_homes: (R.tiers[ck] || []).map((t) => ({ tier: t.tier, median_price: t.price_median, share_valued_above_sale_price: t.above })),
      metro: fmt(R.all), method: method(), page: tag(SITE + "/assessment-ratio/") };
  }
  const nc = normCity(q.replace(/,?\s*(mn|minnesota)\b.*$/i, ""));
  const i = R.cities.findIndex((x) => normCity(x.city) === nc);
  if (i >= 0) {
    const x = R.cities[i];
    return { found: true, area: `${x.city} (${D.counties[x.county].name} County)`, ...fmt(x), rank: `${i + 1} of ${R.cities.length} cities by share valued above sale price (1 = highest)`, county: { name: D.counties[x.county].name, ...fmt(R.counties[x.county]) }, metro: fmt(R.all), method: method(), page: tag(SITE + "/assessment-ratio/") };
  }
  if (nc === "hennepin" || /hennepin/.test(nc)) return { found: false, message: "Only the City of Minneapolis is covered in Hennepin County. Ask for 'Minneapolis'.", page: tag(SITE + "/assessment-ratio/") };
  return { found: false, message: `"${q}" is not a covered ZIP, city (30+ sales) or county. Appeal Draft covers ${COVERED}.`, page: tag(SITE + "/assessment-ratio/") };
}
function method() {
  return `County value (as of January 2 of its value year) / recorded sale price, houses and townhouses, sales from the October before to the June after the valuation date (none of them went into that value), ratios outside ${D.ratio.trim[0]}-${D.ratio.trim[1]} dropped. Built ${D.ratio_built}.`;
}

function datesTool(args) {
  const q = String(args.county || "").toLowerCase().replace(/\s+county$/, "").replace(/^minneapolis$/, "hennepin").trim();
  if (q && /\b(wi|wisconsin|iowa|ia|nd|sd)\b/.test(q)) return { found: false, message: "Minnesota only." };
  const covered = D.deadlines.counties[q] ? q : null;
  return { state: "Minnesota", county: covered ? D.deadlines.counties[covered].name : q ? q.replace(/\b\w/g, (c) => c.toUpperCase()) + " County (statewide rules; check the county assessor for its own meeting dates)" : undefined, ...datesFor(covered), check_a_home: tag(SITE + "/") };
}

// ---- analytics: one PostHog event per call ----
// No address, no arguments, no IP. claude.ai and ChatGPT call from their own servers, so the IP and
// user agent are the platform's, not a person's: the distinct_id is per call, and people are
// counted on the web side by src=mcp landings (ANALYTICS.md).
const clientOf = (ua) => (/claude|anthropic/i.test(ua) ? "claude" : /openai|chatgpt/i.test(ua) ? "chatgpt" : /grok|xai/i.test(ua) ? "grok" : /cursor/i.test(ua) ? "cursor" : /node|undici|python|curl/i.test(ua) ? "script" : "other");
async function logCall(tool, ok, ms, meta, extra) {
  if (process.env.AD_NO_ANALYTICS) return;
  try {
    const props = { tool, ok, ms, client: meta.client, client_ua: String(meta.ua).split(/[\/ ;(]/)[0].slice(0, 30), site: "appeal-draft", $process_person_profile: false, $lib: "appeal-draft-mcp" };
    for (const k of ["err", "via", "found", "county", "verdict", "override"]) if (extra[k] !== undefined) props[k] = extra[k];
    if (meta.test) props.test = true;
    await fetch("https://us.i.posthog.com/capture/", { method: "POST", headers: { "content-type": "application/json" }, signal: AbortSignal.timeout(1500),
      body: JSON.stringify({ api_key: PH_KEY, event: "mcp_tool_call", distinct_id: "mcp_call_" + crypto.randomUUID(), properties: props }) });
  } catch (e) {}
}

async function callTool(name, args, base, log) {
  if (name === "check_property_assessment") return checkAssessment(args, base, log);
  if (name === "property_tax_appeal_dates") return datesTool(args);
  if (name === "assessment_ratio_by_area") { const r = ratioFor(args); log.found = r.found; return r; }
  throw Object.assign(new Error("Unknown tool: " + name), { code: "unknown_tool" });
}

async function handleOne(msg, base, meta) {
  const { id, method, params } = msg || {};
  const ok = (result) => ({ jsonrpc: "2.0", id, result });
  if (method === "initialize") return ok({ protocolVersion: (params && params.protocolVersion) || "2025-06-18", capabilities: { tools: { listChanged: false } },
    serverInfo: { name: "appeal-draft", title: "Appeal Draft – Twin Cities property tax appeal", version: VERSION, websiteUrl: SITE }, instructions: INSTRUCTIONS });
  if (method === "ping") return ok({});
  if (method === "tools/list") return ok({ tools: TOOLS });
  if (method === "tools/call") {
    const t0 = Date.now(), name = String((params && params.name) || ""), log = {};
    let out;
    try {
      const body = await callTool(name, (params && params.arguments) || {}, base, log);
      out = { content: [{ type: "text", text: JSON.stringify(body, null, 1) }], structuredContent: body };
    } catch (e) {
      log.err = e.code || "exception";
      out = { content: [{ type: "text", text: "Error: " + e.message }], isError: true };
    }
    await logCall(TOOLS.some((t) => t.name === name) ? name : "unknown", !out.isError && !log.err, Date.now() - t0, meta, log);
    return ok(out);
  }
  if (method === "resources/list") return ok({ resources: [] });
  if (method === "prompts/list") return ok({ prompts: [] });
  if (method && method.startsWith("notifications/")) return null;
  return { jsonrpc: "2.0", id, error: { code: -32601, message: "Method not found: " + method } };
}

async function readBody(req) {
  if (req.body !== undefined) { // Vercel (and scripts/serve.js) parse a JSON body already
    const b = req.body;
    return Buffer.isBuffer(b) ? JSON.parse(b.toString("utf8")) : typeof b === "string" ? JSON.parse(b) : b;
  }
  let s = ""; for await (const c of req) s += c;
  return JSON.parse(s || "null");
}

module.exports = async function handler(req, res) {
  res.setHeader("access-control-allow-origin", "*");
  res.setHeader("access-control-allow-headers", "content-type, mcp-session-id, mcp-protocol-version, authorization, x-ad-test");
  res.setHeader("access-control-allow-methods", "POST, GET, OPTIONS, DELETE");
  if (req.method === "OPTIONS") { res.statusCode = 204; return res.end(); }
  if (req.method === "GET") {
    res.statusCode = 405; res.setHeader("allow", "POST"); res.setHeader("content-type", "application/json");
    return res.end(JSON.stringify({ name: "Appeal Draft MCP", transport: "streamable-http", url: SITE + "/mcp", tools: TOOLS.map((t) => t.name), docs: SITE + "/llms.txt" }));
  }
  if (req.method === "DELETE") { res.statusCode = 204; return res.end(); }
  let body;
  try { body = await readBody(req); } catch (e) { res.statusCode = 400; res.setHeader("content-type", "application/json"); return res.end(JSON.stringify({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } })); }
  const host = String(req.headers.host || "");
  const base = process.env.DATA_BASE || (/^(localhost|127\.0\.0\.1)(:\d+)?$/.test(host) ? "http://" + host : SITE);
  const ua = String(req.headers["user-agent"] || "");
  const meta = { ua, client: clientOf(ua), test: !!req.headers["x-ad-test"] };
  const batch = Array.isArray(body);
  const out = (await Promise.all((batch ? body : [body]).map((m) => handleOne(m, base, meta)))).filter(Boolean);
  if (!out.length) { res.statusCode = 202; return res.end(); }
  res.statusCode = 200;
  res.setHeader("content-type", "application/json");
  res.end(JSON.stringify(batch ? out : out[0]));
};
module.exports.TOOLS = TOOLS;
module.exports.findIn = findIn;
module.exports.parseAddress = parseAddress;
module.exports.tag = tag;
