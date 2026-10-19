// GET /api/data?zip=55104&pk=ramsey:332923310063  (password in x-password or ?pw=)
//   -> { pk, comps: [{addr, city, date, price, sf, yb, ppsf}], n }
// The comp set is the paid slice. It is bundled with this function as api/_full/comps/<zip>.json.gz
// (scripts/deploy.py uploads private/bundle/), never under a public URL (site/vercel.json redirects
// /api/_full/* away). The free page already holds the headline and the first comp.
const fs = require("fs");
const path = require("path");
const zlib = require("zlib");
const { access } = require("./_lib");

const DIR = process.env.FULL_DIR || path.join(__dirname, "_full", "comps");
const cache = new Map(); // zip -> parsed bundle, per warm instance

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "private, no-store");
  const a = await access(req);
  if (!a.ok) {
    if (a.unpaid) return res.status(402).json({ error: "That password's payment hasn't gone through yet. If you just paid, wait a minute and try again." });
    if (a.error) return res.status(502).json({ error: "Couldn't check the password right now. Try again in a minute." });
    return res.status(401).json({ error: "That password didn't match. Check the email from Brick & Mortar, or reply to it for help." });
  }
  const zip = String(req.query.zip || "");
  const pk = String(req.query.pk || "");
  if (!/^\d{5}$/.test(zip) || !/^[a-z]+:[A-Za-z0-9-]{4,24}$/.test(pk)) return res.status(400).json({ error: "bad zip or parcel" });
  const file = path.join(DIR, `${zip}.json.gz`);
  if (!fs.existsSync(file)) return res.status(404).json({ error: "no such zip" });
  let b = cache.get(zip);
  if (!b) { b = JSON.parse(zlib.gunzipSync(fs.readFileSync(file))); cache.set(zip, b); }
  const idx = b.comps[pk];
  if (!idx) return res.status(404).json({ error: "no such home" });
  const comps = idx.map((i) => {
    const [addr, city, date, price, sf, yb] = b.sales[i];
    return { addr, city, date, price, sf, yb, ppsf: Math.round((price / sf) * 100) / 100 };
  });
  res.setHeader("X-Access", a.kind);
  console.log(`[unlock] ${a.kind} ${a.nonce} ${pk}`);
  res.status(200).json({ pk, n: comps.length, comps });
};
