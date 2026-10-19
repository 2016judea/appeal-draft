// node --test tests/api.test.js   (Node 26: pass the file, not the directory)
// Drives the Vercel handlers with a fake req/res: the paywall's 401/400/404/200 paths and the password HMAC.
const test = require("node:test");
const assert = require("node:assert");
const fs = require("fs"), path = require("path"), os = require("os"), zlib = require("zlib");

process.env.ACCESS_SECRET = "test-secret-not-the-real-one";
process.env.SITE_URL = "https://appeal-draft.vercel.app";
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "ad-"));
process.env.FULL_DIR = tmp;
fs.writeFileSync(path.join(tmp, "55104.json.gz"), zlib.gzipSync(JSON.stringify({
  sales: [["102 Elm St", "St Paul", "2025-06-01", 305000, 1520, 1952, 44.951, -93.1], ["104 Elm St", "St Paul", "2025-03-15", 296000, 1480, 1949, 44.952, -93.1], ["106 Elm St", "St Paul", "2024-11-01", 310000, 1550, 1955, 44.953, -93.1]],
  comps: { "ramsey:1001": [0, 1, 2] },
})));

const ROOT = path.resolve(__dirname, "..", "site", "api");
const lib = require(path.join(ROOT, "_lib.js"));
const data = require(path.join(ROOT, "data.js"));
const check = require(path.join(ROOT, "check.js"));

function res() {
  const o = { code: null, body: null, headers: {} };
  return { o, setHeader(k, v) { o.headers[k.toLowerCase()] = v; }, status(c) { o.code = c; return this; }, json(b) { o.body = b; return this; }, end(b) { o.body = b; return this; } };
}
const comp = () => { const n = "QWERT"; const raw = n + lib.mac(n, "comp:"); return `${raw.slice(0, 4)}-${raw.slice(4, 8)}-${raw.slice(8)}`; };

test("checkPassword: garbage fails without a network call; a comp password is recognised", () => {
  assert.equal(lib.checkPassword(""), null);
  assert.equal(lib.checkPassword("ABCD-EFGH-JKLM"), null);
  assert.equal(lib.checkPassword("QWER-T" + "2345678"), null, "a tail we never signed fails");
  const c = lib.checkPassword(comp());
  assert.equal(c.kind, "comp");
  assert.equal(lib.checkPassword(comp().toLowerCase().replace(/-/g, " ")).kind, "comp", "any case, spaces or dashes");
  const { password } = lib.newPassword();
  assert.equal(lib.checkPassword(password).kind, "paid");
});

test("/api/data is 401 bare and with a wrong password", async () => {
  let r = res(); await data({ method: "GET", headers: {}, query: { zip: "55104", pk: "ramsey:1001" } }, r);
  assert.equal(r.o.code, 401);
  r = res(); await data({ method: "GET", headers: { "x-password": "ABCD-EFGH-JKLM" }, query: { zip: "55104", pk: "ramsey:1001" } }, r);
  assert.equal(r.o.code, 401);
  assert.equal(r.o.headers["cache-control"], "private, no-store");
});

test("/api/data with a comp password: 400 on a bad zip or parcel, 404 unknown, 200 with every comp", async () => {
  let r = res(); await data({ method: "GET", headers: { "x-password": comp() }, query: { zip: "5510", pk: "ramsey:1001" } }, r);
  assert.equal(r.o.code, 400);
  r = res(); await data({ method: "GET", headers: { "x-password": comp() }, query: { zip: "55104", pk: "../etc" } }, r);
  assert.equal(r.o.code, 400);
  r = res(); await data({ method: "GET", headers: { "x-password": comp() }, query: { zip: "55105", pk: "ramsey:1001" } }, r);
  assert.equal(r.o.code, 404);
  r = res(); await data({ method: "GET", headers: { "x-password": comp() }, query: { zip: "55104", pk: "ramsey:9009" } }, r);
  assert.equal(r.o.code, 404);
  r = res(); await data({ method: "GET", headers: {}, query: { zip: "55104", pk: "ramsey:1001", pw: comp() } }, r);
  assert.equal(r.o.code, 200);
  assert.equal(r.o.body.n, 3);
  assert.deepEqual(r.o.body.comps[0], { addr: "102 Elm St", city: "St Paul", date: "2025-06-01", price: 305000, sf: 1520, yb: 1952, ppsf: 200.66 });
  assert.equal(r.o.headers["x-access"], "comp");
});

test("/api/check: 401 without, 200 with a comp password", async () => {
  let r = res(); await check({ method: "POST", headers: {}, body: {} }, r);
  assert.equal(r.o.code, 401);
  r = res(); await check({ method: "POST", headers: { "x-password": comp() }, body: {} }, r);
  assert.equal(r.o.code, 200);
  assert.equal(r.o.body.kind, "comp");
});

test("vercel.json bundles the paid comps with /api/data and redirects them away from any public URL", () => {
  const v = JSON.parse(fs.readFileSync(path.resolve(__dirname, "..", "site", "vercel.json"), "utf8"));
  assert.equal(v.functions["api/data.js"].includeFiles, "api/_full/**");
  assert.equal(v.outputDirectory, "public", "only site/public/ is static; api/_full/ is never a URL");
  for (const s of ["/api/_full/:path*", "/api/%5Ffull/:path*", "/api/%5ffull/:path*"]) assert.ok(v.redirects.some((x) => x.source === s), s);
  assert.ok(v.rewrites.some((x) => x.source === "/for/:token/" && x.destination === "/index.html"));
});
