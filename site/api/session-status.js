// GET /api/session-status?session_id=cs_... -> { paid, email, mailed, password? }
// The return page. If the webhook has not emailed the password yet, this sends it (after a
// short wait so the two don't both send) and also hands the password back to the one browser
// that holds Stripe's session id, so a slow email never strands a buyer.
const { stripe, sendPasswordOnce, unlocked, PRODUCT } = require("./_lib");
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

module.exports = async (req, res) => {
  const id = String(req.query.session_id || "");
  if (!/^cs_(test|live)_[A-Za-z0-9]+$/.test(id)) return res.status(400).json({ error: "bad session id" });
  try {
    const s = await stripe(`checkout/sessions/${id}`);
    if (s.metadata?.product !== PRODUCT) return res.status(404).json({ error: "not found" });
    const paid = unlocked(s);
    let mail = null;
    if (paid) {
      if (!s.metadata?.pw_emailed) await wait(4000);
      try { mail = await sendPasswordOnce(s, { who: "status" }); } catch (e) { console.error("[status] mail:", e.message); mail = { sent: false, error: e.message.slice(0, 200) }; }
    }
    res.setHeader("Cache-Control", "private, no-store");
    res.status(200).json({ paid, status: s.status, email: s.customer_details?.email || null,
      mailed: !!(mail?.sent || /already/.test(mail?.why || "")), ...(paid ? { password: s.metadata.password } : {}) });
  } catch (e) {
    console.error("[status]", e.message);
    res.status(502).json({ error: "Could not check the payment. Refresh in a minute." });
  }
};
