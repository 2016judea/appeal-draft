// node --test tests/mcp.test.js   (Node 26: pass the file, not the directory)
// Drives /mcp (site/api/mcp.js) with a fake req/res over fixture shards: the protocol, the three
// tools, an honest not-found, and src=mcp on every link it hands out. No network: the geocoder and
// PostHog are switched off.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs"), path = require("path"), os = require("os");

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ad-mcp-"));
process.env.ZIP_DIR = tmp;
process.env.AD_NO_GEOCODE = "1";
process.env.AD_NO_ANALYTICS = "1";
// row: [pk, addr, city, sf, yb, emv, prior, tax, hs, ay, target, ppsf, ncomps, first, ownD, ownP, pin]
fs.writeFileSync(path.join(tmp, "55104-1.json"), JSON.stringify({ zip: "55104", shard: "1", county: "ramsey", ppsf: 230, n_sales: 868, homes: [
  ["ramsey:1001", "100 Elm St", "St Paul", 1500, 1950, 400000, 360000, 5200, 1, 2025, 300000, 200, 5, ["102 Elm St", "St Paul", "2025-06-01", 305000, 1520, 0.1], null, null, "1001"],
  ["ramsey:1002", "100 Ashland Ave", "St Paul", 1500, 1950, 300000, 290000, 3900, 1, 2025, 305000, 203.3, 5, null, null, null, "1002"],
] }));
fs.writeFileSync(path.join(tmp, "55104-2.json"), JSON.stringify({ zip: "55104", shard: "2", county: "ramsey", ppsf: 230, n_sales: 868, homes: [] }));

const mcp = require(path.resolve(__dirname, "..", "site", "api", "mcp.js"));

async function rpc(method, params, headers = {}) {
  const o = { code: null, body: null, headers: {} };
  const res = { setHeader(k, v) { o.headers[k.toLowerCase()] = v; }, end(b) { o.body = b; }, set statusCode(c) { o.code = c; }, get statusCode() { return o.code; } };
  await mcp({ method: "POST", headers: { host: "appeal-draft.vercel.app", ...headers }, body: { jsonrpc: "2.0", id: 7, method, params } }, res);
  return { code: o.code, j: o.body ? JSON.parse(o.body) : null };
}
const call = async (name, args) => (await rpc("tools/call", { name, arguments: args })).j.result;

test("initialize and tools/list: three tools, every hint an explicit boolean", async () => {
  const init = (await rpc("initialize", { protocolVersion: "2025-06-18" })).j.result;
  assert.equal(init.serverInfo.name, "appeal-draft");
  assert.match(init.instructions, /Twin Cities|Minneapolis/);
  const { tools } = (await rpc("tools/list", {})).j.result;
  assert.deepEqual(tools.map((t) => t.name), ["check_property_assessment", "property_tax_appeal_dates", "assessment_ratio_by_area"]);
  for (const t of tools) for (const k of ["readOnlyHint", "destructiveHint", "openWorldHint", "idempotentHint"]) assert.equal(typeof t.annotations[k], "boolean", `${t.name}.${k}`);
});

test("check_property_assessment: found by ZIP, numbers from the shard, link opens the page with src=mcp", async () => {
  const r = await call("check_property_assessment", { address: "100 Elm Street, Saint Paul, MN 55104" });
  const s = r.structuredContent;
  assert.equal(s.found, true);
  assert.equal(s.county_value.amount, 400000);
  assert.equal(s.sales_of_similar_homes_say.amount, 300000);
  assert.equal(s.gap, "33.3%");
  assert.equal(s.verdict, "worth_appealing");
  assert.equal(s.yearly_tax_saving_if_cut.amount, 1300); // 5200 × (1 − 300000/400000)
  assert.equal(s.zip_market.amount, 345000);              // 230 × 1500
  assert.equal(s.open_the_comparison, "https://appeal-draft.vercel.app/?pk=ramsey%3A1001&zip=55104&sh=1&src=mcp");
  assert.match(s.county_value.note, /2025 value/);
  assert.ok(s.when_to_appeal.tax_court.includes("April 30, 2027"));
});

test("the street name must match: 100 Ashland is not 100 Elm, and a notice value overrides the roll", async () => {
  const a = (await call("check_property_assessment", { address: "100 Ashland Ave", zip: "55104", value_on_notice: 330000 })).structuredContent;
  assert.equal(a.home.address.startsWith("100 Ashland Ave"), true);
  assert.equal(a.county_value.amount, 330000);
  assert.equal(a.verdict, "worth_a_call"); // 330000 / 305000 − 1 = 8.2%
  assert.match(a.open_the_comparison, /&v=330000&src=mcp$/);
  const miss = (await call("check_property_assessment", { address: "100 Maple St, 55104" })).structuredContent;
  assert.equal(miss.found, false);
  assert.match(miss.message, /condos are not covered/);
});

test("by city without a ZIP (geocoder off): the city index finds the ZIP", async () => {
  const s = (await call("check_property_assessment", { address: "100 Elm St, St. Paul" })).structuredContent;
  assert.equal(s.found, true);
  assert.equal(s.home.parcel_id, "1001");
});

test("no house number asks for one; nothing is invented", async () => {
  const s = (await call("check_property_assessment", { address: "Elm St, Saint Paul" })).structuredContent;
  assert.equal(s.found, false);
  assert.match(s.message, /house number/);
});

test("assessment_ratio_by_area answers a ZIP, a city and a county from the built study; Denver is not covered", async () => {
  const D = require(path.resolve(__dirname, "..", "site", "api", "_mcp_data.json"));
  const z = D.ratio.zips[0].zip;
  const s = (await call("assessment_ratio_by_area", { area: z })).structuredContent;
  assert.equal(s.found, true);
  assert.equal(s.share_valued_above_sale_price, D.ratio.zips[0].above);
  assert.match(s.page, /assessment-ratio\/\?src=mcp$/);
  assert.equal((await call("assessment_ratio_by_area", { area: "Ramsey County" })).structuredContent.found, true);
  assert.equal((await call("assessment_ratio_by_area", { area: "st paul" })).structuredContent.found, true);
  assert.equal((await call("assessment_ratio_by_area", { area: "Denver" })).structuredContent.found, false);
});

test("property_tax_appeal_dates carries the 2027 dates with sources", async () => {
  const s = (await call("property_tax_appeal_dates", { county: "Hennepin" })).structuredContent;
  assert.match(s.local_board_or_open_book, /April 1 to May 31, 2027/);
  assert.match(s.county_board, /June 11, 2027/);
  assert.ok(s.sources.some((u) => u.includes("revisor.mn.gov/statutes/cite/278.01")));
  assert.equal(s.assessor_phone, "612-348-7050");
});

test("GET says what it is; an unknown tool is an error, not a crash", async () => {
  const o = {};
  await mcp({ method: "GET", headers: {} }, { setHeader() {}, end(b) { o.b = b; }, set statusCode(c) { o.c = c; } });
  assert.equal(o.c, 405);
  assert.match(o.b, /streamable-http/);
  const r = await call("sell_me_something", {});
  assert.equal(r.isError, true);
});

test("tag() adds src=mcp once, keeps the hash, and leaves other hosts alone", () => {
  assert.equal(mcp.tag("https://appeal-draft.vercel.app/x#y"), "https://appeal-draft.vercel.app/x?src=mcp#y");
  assert.equal(mcp.tag("https://appeal-draft.vercel.app/?a=1&src=ratio"), "https://appeal-draft.vercel.app/?a=1&src=ratio");
  assert.equal(mcp.tag("https://example.com/"), "https://example.com/");
});
