// POST /api/checkout { token?, pk? } -> { clientSecret } for Stripe embedded Checkout.
// One price, once (site/offer.json). The buyer's password is minted here so it rides in the
// session metadata and the invoice footer; the webhook (via stripe-router) emails it.
const { SITE, PRODUCT, OFFER, stripe, newPassword } = require("./_lib");

module.exports = async (req, res) => {
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });
  try {
    const { nonce, password } = newPassword();
    const b = typeof req.body === "object" && req.body ? req.body : {};
    const token = /^[a-z0-9]{6,16}$/.test(b.token || "") ? b.token : "";
    const pk = /^[a-z]+:[A-Za-z0-9-]{4,24}$/.test(b.pk || "") ? b.pk : "";
    const zip = /^\d{5}$/.test(b.zip || "") ? b.zip : "", sh = /^[0-9]$/.test(b.sh || "") ? b.sh : "0";
    const name = `${OFFER.name}: full comps and the appeal letter`;
    const back = `${SITE}/${token ? `for/${token}/` : ""}?paid={CHECKOUT_SESSION_ID}${pk && zip ? `&pk=${encodeURIComponent(pk)}&zip=${zip}&sh=${sh}` : ""}`;
    const s = await stripe("checkout/sessions", {
      method: "POST",
      form: {
        ui_mode: "embedded_page",
        mode: "payment",
        "line_items[0][quantity]": "1",
        "line_items[0][price_data][currency]": "usd",
        "line_items[0][price_data][unit_amount]": String(OFFER.price_usd * 100),
        "line_items[0][price_data][product_data][name]": name,
        "line_items[0][price_data][product_data][description]": OFFER.checkout_line,
        "payment_method_types[0]": "card",
        "payment_method_types[1]": "link",
        customer_creation: "always",
        "invoice_creation[enabled]": "true",
        "invoice_creation[invoice_data][description]": name,
        "invoice_creation[invoice_data][custom_fields][0][name]": "Password",
        "invoice_creation[invoice_data][custom_fields][0][value]": password,
        "invoice_creation[invoice_data][footer]": `Your password: ${password}. Open it at ${SITE}/?pw=${password}. Brick & Mortar · aidan@brickandmortar.dev`,
        "invoice_creation[invoice_data][metadata][product]": PRODUCT,
        "metadata[product]": PRODUCT,
        "metadata[site]": SITE,
        "metadata[pw_nonce]": nonce,
        "metadata[password]": password,
        "metadata[token]": token,
        "metadata[pk]": pk,
        "payment_intent_data[metadata][product]": PRODUCT,
        "payment_intent_data[metadata][pw_nonce]": nonce,
        "payment_intent_data[description]": name,
        return_url: back,
      },
    });
    res.status(200).json({ clientSecret: s.client_secret });
  } catch (e) {
    console.error("[checkout]", e.message);
    res.status(502).json({ error: "Checkout could not start. Please try again in a minute." });
  }
};
