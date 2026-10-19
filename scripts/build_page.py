#!/usr/bin/env python3
"""Write site/public/index.html from this template, site/offer.json, site/public/data/meta.json and data/deadlines.json.

The page opens on a real Saint Paul home (site/public/data/example.json, picked by scripts/build.py) with
the three numbers already drawn, so a visitor sees the answer before typing. /for/<token>/ is a
rewrite to this same page; the token's own home comes from /data/for/<token>.json.

Generated output: never hand-edit site/public/index.html; edit this and re-run.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OFFER = json.loads((ROOT / "site/offer.json").read_text())
META = json.loads((ROOT / "site/public/data/meta.json").read_text())
DEAD = json.loads((ROOT / "data/deadlines.json").read_text())
POSTHOG = (ROOT / "scripts/posthog_snippet.html").read_text().replace("__SITE__", OFFER["product"])

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Appeal Draft</title>
<meta name="description" content="Type a Twin Cities address. See the county's value next to what homes like yours sold for, the one number to argue for, and the one-page appeal to hand the board.">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='7' fill='%232457c5'/><rect x='8' y='14' width='16' height='3' fill='%23f7f1e3'/><rect x='8' y='20' width='10' height='3' fill='%23c9973f'/></svg>">
__POSTHOG__
<style>
:root{--bg:#f7f3ea;--paper:#fffdf8;--ink:#17150f;--muted:#6b6557;--rule:#e0d8c6;--assessor:#2457c5;--sales:#c9973f;--target:#2e7d4f;--on:#fff;--mono:ui-monospace,SFMono-Regular,Menlo,monospace;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;--serif:Georgia,"Times New Roman",serif}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#15130e;--paper:#1e1c15;--ink:#f0ebe0;--muted:#a7a08f;--rule:#38342a;--assessor:#6f95ea;--sales:#d9ac5a;--target:#5fb37f}}
:root[data-theme=dark]{--bg:#15130e;--paper:#1e1c15;--ink:#f0ebe0;--muted:#a7a08f;--rule:#38342a;--assessor:#6f95ea;--sales:#d9ac5a;--target:#5fb37f}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 var(--sans)}
.wrap{max-width:1040px;margin:0 auto;padding:22px 16px 64px}
.eyebrow{font:500 12px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
h1{font:400 clamp(27px,5.2vw,46px)/1.1 var(--serif);margin:8px 0 14px;letter-spacing:-.01em;max-width:24ch}
.lede{margin:0 0 18px;max-width:52ch;color:var(--muted)}
form.find{display:grid;grid-template-columns:1fr;gap:8px;margin:0 0 18px}
@media (min-width:640px){form.find{grid-template-columns:minmax(0,3fr) minmax(0,1fr) auto}}
input{font:16px var(--sans);padding:12px;border:1px solid var(--rule);border-radius:9px;background:var(--paper);color:var(--ink);min-height:46px;width:100%}
button,.btn{font:600 16px var(--sans);border:0;border-radius:9px;padding:12px 18px;cursor:pointer;background:var(--ink);color:var(--bg);min-height:46px;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:8px}
button.ghost{background:transparent;color:var(--ink);border:1px solid var(--rule)}
button:disabled{opacity:.55;cursor:wait}
.hint{font-size:13px;color:var(--muted)}
.card{background:var(--paper);border:1px solid var(--rule);border-radius:14px;padding:16px;margin:0 0 14px}
.addr{font:400 clamp(20px,3.6vw,28px)/1.2 var(--serif);margin:0 0 2px}
.sub{color:var(--muted);font-size:14px;margin:0 0 14px}
.nums{display:grid;grid-template-columns:1fr;gap:12px;margin:0 0 6px}
@media (min-width:720px){.nums{grid-template-columns:1fr 1fr 1fr}}
.num{border-left:5px solid var(--c);padding:2px 0 2px 12px}
.num .lbl{font-size:13px;color:var(--muted)}
.num .v{font:600 clamp(26px,5vw,34px)/1.1 var(--mono);color:var(--c);letter-spacing:-.02em}
.num .how{font-size:13px;color:var(--muted);margin-top:4px}
.bars{margin:14px 0 6px}
.bar{display:grid;grid-template-columns:7.5em 1fr;align-items:center;gap:10px;margin:6px 0;font-size:13px;color:var(--muted)}
.bar i{display:block;height:14px;border-radius:4px;background:var(--c);min-width:2px}
.verdict{font:400 clamp(19px,3.2vw,24px)/1.3 var(--serif);margin:16px 0 4px}
.verdict b{color:var(--target)}
.verdict.backs b{color:var(--assessor)}
.verdict.call b{color:var(--sales)}
.tax{color:var(--muted);margin:0 0 10px}
.k{display:inline-block;font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;border-radius:4px;padding:3px 7px;color:var(--on);background:var(--target)}
table{width:100%;border-collapse:collapse;font-size:14px;margin:8px 0}
th,td{text-align:left;padding:8px 6px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font:500 11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
td.r,th.r{text-align:right;font-variant-numeric:tabular-nums}
tr.lock td{color:var(--muted)}
.lockbox{border:1px dashed var(--target);border-radius:12px;padding:14px;margin:12px 0}
.lockbox h3{font:400 22px/1.2 var(--serif);margin:0 0 6px}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px}
.pw{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.pw input{flex:1;min-width:0;font-family:var(--mono)}
#checkout{margin-top:12px}
.steps{padding-left:20px;margin:6px 0}
.steps li{margin:4px 0}
.notice{background:color-mix(in srgb,var(--assessor) 10%,var(--paper));border:1px solid color-mix(in srgb,var(--assessor) 35%,var(--rule));border-radius:10px;padding:12px;margin:10px 0;font-size:15px}
.notice input{max-width:14em;display:inline-block;min-height:40px;padding:8px 10px;margin:6px 6px 0 0}
.letter{background:#fff;color:#111;border:1px solid var(--rule);border-radius:4px;padding:28px 28px 22px;font:14px/1.45 Georgia,serif;margin:12px 0}
.letter h2{font:400 22px/1.2 Georgia,serif;margin:0 0 2px}
.letter .meta{font-size:13px;color:#555;margin:0 0 14px}
.letter table{font-size:13px}
.letter th,.letter td{border-bottom:1px solid #ddd;padding:5px 4px;color:#111}
.letter .fill{border-bottom:1px solid #111;min-width:12em;display:inline-block;padding:0 4px}
.letter .box{border:1px solid #111;padding:10px 12px;margin-top:16px;font-size:12.5px}
.letter .box ol{margin:4px 0 0;padding-left:18px}
.err{color:#b3261e;font-size:14px;margin:6px 0}
.foot{margin-top:40px;border-top:1px solid var(--rule);padding-top:12px;font-size:13px;color:var(--muted);max-width:76ch}
.foot a,.card a{color:inherit}
details summary{cursor:pointer;color:var(--muted);font-size:14px}
@media print{body{background:#fff}.wrap>*:not(#letterwrap){display:none!important}#letterwrap{display:block!important}.letter{border:0;padding:0;margin:0;font-size:12.5px}.letter .noprint{display:none}}
</style>
<script>window.va=window.va||function(){(window.vaq=window.vaq||[]).push(arguments)};</script><script defer src="/_vercel/insights/script.js"></script>
</head><body><main class="wrap">
<div class="eyebrow">Twin Cities · your home's assessed value, checked against recorded sales</div>
<h1>Is the county's number for your home too high? Here is what to argue for.</h1>
<p class="lede">Type your address. You get the county's value next to what homes like yours actually sold for, the one number to ask the board for, and the one-page appeal to hand them.</p>
<p class="hint" id="nextwin">Next appeal window: notices go out __NEXT_NOTICES__, local boards meet __NEXT_BOARDS__.</p>
<form class="find" id="find">
 <input id="addr" placeholder="Street address, e.g. 1234 Maple St" autocomplete="street-address" aria-label="Street address">
 <input id="zip" placeholder="ZIP" inputmode="numeric" pattern="[0-9]*" maxlength="5" autocomplete="postal-code" aria-label="ZIP">
 <button type="submit" id="go">Check my home</button>
</form>
<p class="err" id="err" hidden></p>
<section class="card" id="home" hidden>
 <p class="addr" id="hAddr"></p>
 <p class="sub" id="hSub"></p>
 <div id="yearNote"></div>
 <div class="nums">
  <div class="num" style="--c:var(--assessor)"><div class="lbl" id="lblA">The county says it is worth</div><div class="v" id="vA"></div><div class="how" id="howA"></div></div>
  <div class="num" style="--c:var(--target)"><div class="lbl">Homes like yours sold for</div><div class="v" id="vT"></div><div class="how" id="howT"></div></div>
  <div class="num" style="--c:var(--sales)"><div class="lbl">Your ZIP's sales say</div><div class="v" id="vZ"></div><div class="how" id="howZ"></div></div>
 </div>
 <div class="bars" id="bars"></div>
 <p class="verdict" id="verdict"></p>
 <p class="tax" id="tax"></p>
 <table id="comps"><thead><tr><th>Sold home</th><th>Sold</th><th class="r">Price</th><th class="r">Sq ft</th><th class="r">$/sq ft</th></tr></thead><tbody id="compBody"></tbody></table>
 <div class="lockbox" id="lock">
  <h3 id="lockH">The other comps, your appeal letter and the PDF: $__PRICE__, once</h3>
  <p class="hint" id="lockP">Every comparable sale behind the green number, the one-page appeal filled in with your county's fields and dates, ready to print or save as a PDF. One home. No account.</p>
  <div class="row"><button id="buy">Unlock for $__PRICE__</button><span class="hint">Card or Link, through Stripe.</span></div>
  <div id="checkout"></div>
  <div class="pw"><input id="pwIn" placeholder="Have a password? XXXX-XXXX-XXXX" autocomplete="off" aria-label="Password"><button class="ghost" id="pwGo" type="button">Unlock</button></div>
  <p class="hint" id="pwMsg"></p>
 </div>
 <div id="letterwrap" hidden>
  <div class="row noprint" style="margin:14px 0 6px"><button id="print">Print or save as PDF</button><span class="hint">Fill in your name and phone on the letter first; the fields are typeable.</span></div>
  <div class="letter" id="letter"></div>
 </div>
 <h3 style="font:400 20px/1.2 var(--serif);margin:18px 0 4px">When you can appeal</h3>
 <div id="window"></div>
</section>
<details class="card"><summary>How the numbers are made</summary>
 <p>The county's value is the estimated market value on the assessor's roll (<span id="mCounties"></span>). "Homes like yours" are recorded arm's-length sales since <span id="mSince"></span> of homes within 25% of your finished square feet and 25 years of your build year, within 2 miles, nearest and most alike first; the green number is their median price per square foot times your square feet. Sales under $50,000, or far off the sold home's own value (outside 0.5 to 2 times), are left out as family transfers or partial interests. Your ZIP's number is the median $/sq ft of every such sale in the ZIP. Prices are not adjusted for time. Condos are not covered. <span id="mCounts"></span></p>
 <p>Minneapolis homes show the 2025 assessment; the other counties show their latest roll. Built <span id="mBuilt"></span> from county assessor and recorder data via <a href="https://brickandmortar.dev">Brick &amp; Mortar</a>.</p>
</details>
<footer class="foot">This is a draft for your own appeal, not legal advice. The board decides. Built by <a href="https://brickandmortar.dev">Brick &amp; Mortar</a>, Minneapolis. <a href="https://randomaidan.substack.com">Why we build these</a>.</footer>
</main>
<script src="https://js.stripe.com/v3/"></script>
<script>
const OFFER=__OFFER__;const META=__META__;const DEAD=__DEAD__;
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const money=n=>n==null?"—":"$"+Math.round(n).toLocaleString("en-US");
const pct=x=>Math.round(Math.abs(x)*100)+"%";
const TOKEN=(location.pathname.match(/^\/for\/([a-z0-9]{4,24})/)||[])[1]||"";
let VARIANT="";
const track=(name,data={})=>{data={...data,token:TOKEN,variant:VARIANT};try{window.va("event",{name,data})}catch(e){}try{if(window.posthog&&posthog.capture)posthog.capture(name,data)}catch(e){}};
let PW=null;try{PW=localStorage.getItem("pw:"+OFFER.product)}catch(e){}
let CUR=null;   // {zip, row, zipdata}
let OVERRIDE=null; // the owner typed the value from a newer notice
const ZIPS={};
const shardOf=a=>{const m=String(a).trim().match(/^\d/);return m?m[0]:"0"};
async function zipData(z,sh){const k=z+"-"+sh;if(ZIPS[k])return ZIPS[k];const r=await fetch(`/data/zip/${k}.json`);if(!r.ok)throw new Error("We don't have "+z+" yet. We cover Ramsey, Anoka, Dakota, Scott, Washington and Minneapolis.");return ZIPS[k]=await r.json()}
const ABBR={street:"st",avenue:"ave",av:"ave",road:"rd",drive:"dr",lane:"ln",court:"ct",circle:"cir",boulevard:"blvd",place:"pl",terrace:"ter",trail:"trl",parkway:"pkwy",highway:"hwy",north:"n",south:"s",east:"e",west:"w",northeast:"ne",northwest:"nw",southeast:"se",southwest:"sw",saint:"st"};
const norm=s=>String(s).toLowerCase().replace(/[.,#]/g," ").replace(/\s+/g," ").trim().split(" ").map(w=>ABBR[w]||w);
function findRow(rows,q){const t=norm(q);const num=t.find(w=>/^\d+[a-z]?$/.test(w));if(!num)return{err:"Start with the house number, like 1234 Maple St."};const words=t.filter(w=>w!==num&&!/^\d{5}$/.test(w));let best=null,bs=0;
 for(const r of rows){const a=norm(r[1]);if(a[0]!==num)continue;const rest=a.slice(1);let s=1;for(const w of words)if(rest.includes(w))s+=2;if(words.length&&rest[0]&&words.includes(rest[0]))s+=3;if(s>bs){bs=s;best=r}}
 if(!best)return{err:`No home at number ${num} in that ZIP. Check the number, or the ZIP on your tax statement.`};if(words.length&&bs<3)return{err:`No ${esc(words.join(" "))} at number ${num} in that ZIP. Check the street name.`};return{row:best}}
function bar(label,v,max,c){return `<div class="bar" style="--c:${c}"><span>${label}</span><i style="width:${Math.max(2,Math.round(v/max*100))}%"></i></div>`}
function compRow(c,lock){return `<tr${lock?' class="lock"':''}><td>${esc(c.addr)}<br><span class="hint">${esc(c.city)}${c.miles!=null?` · ${c.miles} mi`:""}</span></td><td>${esc(c.date.slice(0,7))}</td><td class="r">${money(c.price)}</td><td class="r">${c.sf.toLocaleString("en-US")}</td><td class="r">$${Math.round(c.price/c.sf)}</td></tr>`}
function render(){const {zip,row,zipdata}=CUR;const [pk,addr,city,sf,yb,emv0,prior,tax,hs,ay,target,ppsf,ncomps,first,ownD,ownP,pin]=row;const county=zipdata.county;const emv=OVERRIDE||emv0;
 $("home").hidden=false;$("hAddr").textContent=`${addr}, ${city}`;$("hSub").textContent=`${sf.toLocaleString("en-US")} finished sq ft · built ${yb||"n/a"} · ${hs?"homestead":"non-homestead"} · ${DEAD.counties[county].name} PID ${pin}`;
 const cty=DEAD.counties[county];const old=ay<2026;
 $("lblA").textContent=`${cty.name.split(" (")[0]} says it is worth`;$("vA").textContent=money(emv);
 $("howA").textContent=(OVERRIDE?`from your notice. The ${ay} roll had ${money(emv0)}`:`${ay} assessment, taxes payable ${ay+1}`)+(prior?` · ${emv0>=prior?"up":"down"} ${pct(emv0/prior-1)} from ${money(prior)} the year before`:"");
 $("yearNote").innerHTML=old?`<div class="notice">This is the <b>${ay}</b> value. Your <b>2026</b> notice (mailed March 2026) is not in our records yet. Type the estimated market value from it and the comparison updates: <input id="ov" inputmode="numeric" placeholder="e.g. 395000" value="${OVERRIDE||""}"> <button class="ghost" type="button" id="ovGo" style="min-height:40px;padding:8px 12px">Use it</button></div>`:"";
 if(old){$("ovGo").onclick=()=>{const v=parseInt(String($("ov").value).replace(/[^0-9]/g,""),10);OVERRIDE=v>20000?v:null;track("override_value",{set:!!OVERRIDE});render()}}
 const zp=zipdata.ppsf,zv=zp?Math.round(zp*sf/100)*100:null;
 $("vT").textContent=money(target);$("howT").textContent=target?`median $${Math.round(ppsf)}/sq ft across ${ncomps} sales of homes like yours, × your ${sf.toLocaleString("en-US")} sq ft`:`fewer than 3 sales of homes like yours within 2 miles since ${META.sales_since.slice(0,7)}`;
 $("vZ").textContent=money(zv);$("howZ").textContent=zv?`median $${Math.round(zp)}/sq ft over ${zipdata.n_sales.toLocaleString("en-US")} sales in ${zip} since ${new Date(META.sales_since+"T12:00").toLocaleDateString("en-US",{month:"short",year:"numeric"})}, × your sq ft`:`fewer than 10 qualifying sales in ${zip}`;
 const max=Math.max(emv,target||0,zv||0);$("bars").innerHTML=bar("county",emv,max,"var(--assessor)")+(target?bar("homes like yours",target,max,"var(--target)"):"")+(zv?bar("your ZIP",zv,max,"var(--sales)"):"");
 let kind="none",gap=null;if(target){gap=emv/target-1;kind=gap<0.03?"backs":gap<0.10?"call":"argue"}
 const V=$("verdict");V.className="verdict "+kind;
 V.innerHTML=kind==="argue"?`Argue for <b>${money(target)}</b>. The county is ${pct(gap)} above what sales of homes like yours say.`:kind==="call"?`A little high: <b>${pct(gap)}</b> above the sales. Worth a call to the assessor before the board.`:kind==="backs"?`Sales <b>back the county's number</b>${gap<0?` (it is ${pct(gap)} under them)`:""}. An appeal is unlikely to help.`:`Not enough nearby sales of homes like yours to say.`;
 const saving=tax&&target&&target<emv?Math.round(tax*(1-target/emv)/10)*10:0;
 $("tax").textContent=saving?`About $${saving.toLocaleString("en-US")} a year in property tax at today's rate (your bill is $${tax.toLocaleString("en-US")}), every year the lower value holds.`:(tax?`Your bill this year is $${tax.toLocaleString("en-US")}.`:"");
 if(ownD&&ownP)$("tax").textContent+=` You bought it ${ownD.slice(0,7)} for ${money(ownP)}.`;
 const body=$("compBody");body.innerHTML="";
 if(first){body.innerHTML=compRow({addr:first[0],city:first[1],date:first[2],price:first[3],sf:first[4],miles:first[5]});if(ncomps>1)body.innerHTML+=`<tr class="lock"><td colspan="5">+ ${ncomps-1} more sales like it · unlock with the letter</td></tr>`}
 $("comps").hidden=!first;$("lock").hidden=!target;$("letterwrap").hidden=true;
 $("window").innerHTML=windowHtml(county,ay);
 if(PW&&target)unlock(PW,"stored")}
function windowHtml(county,ay){const c=DEAD.counties[county],n=DEAD.statewide.next;return `<ol class="steps">${c.steps.map(s=>`<li>${esc(s)}</li>`).join("")}</ol><p class="hint">Last cycle, ${esc(c.last_cycle)} Assessor: ${esc(c.assessor_phone)}. <a href="${esc(c.url)}" rel="noopener">County page</a>, read ${esc(c.read_on)}.</p><p><b>As of ${new Date(META.built+"T12:00").toLocaleDateString("en-US",{month:"long",year:"numeric"})}:</b> the boards for the 2026 value have closed. A Tax Court petition on the 2026 value is open until <b>${esc(n.tax_court_for_2026_value)}</b> (homesteads can use the Small Claims Division). The next board window opens with the <b>${esc(n.notices)}</b> notice: local boards ${esc(n.local_boards)}, county boards ${esc(n.county_boards)}. ${ay<2026?"The 2025 value shown here could only be appealed until April 30, 2026; use the letter for your 2026 or 2027 notice.":""}</p>`}
function letterHtml(comps){const {zip,row,zipdata}=CUR;const [pk,addr,city,sf,yb,emv0,prior,tax,hs,ay,target,ppsf,ncomps,first,ownD,ownP,pin]=row;const emv=OVERRIDE||emv0;const c=DEAD.counties[zipdata.county];
 const med=comps.map(x=>x.price/x.sf).sort((a,b)=>a-b);const m=med.length%2?med[(med.length-1)/2]:(med[med.length/2-1]+med[med.length/2])/2;const ask=Math.round(m*sf/100)*100;const gap=emv/ask-1;const yr=OVERRIDE?2026:ay;
 return `<h2>Request for review of estimated market value</h2><p class="meta">${yr} assessment · ${esc(c.name.split(" (")[0])} · ${new Date().toLocaleDateString("en-US",{month:"long",day:"numeric",year:"numeric"})}</p>
<p>To: ${esc(c.name.split(" (")[0])} Assessor's Office and the Local Board of Appeal and Equalization, ${esc(city)}</p>
<p><b>Property:</b> ${esc(addr)}, ${esc(city)}, MN ${esc(zip)} &nbsp; <b>PID:</b> ${esc(pin)}<br><b>Owner:</b> <span class="fill" contenteditable="true">&nbsp;</span> &nbsp; <b>Phone or email:</b> <span class="fill" contenteditable="true">&nbsp;</span></p>
<p><b>Current estimated market value:</b> ${money(emv)}<br><b>Requested estimated market value:</b> ${money(ask)}</p>
<p><b>Basis.</b> The ${comps.length} most comparable recorded arm's-length sales since ${new Date(META.sales_since+"T12:00").toLocaleDateString("en-US",{month:"long",year:"numeric"})}: homes within 25% of this home's ${sf.toLocaleString("en-US")} finished square feet and 25 years of its ${yb||""} build year, within two miles, from county records.</p>
<table><thead><tr><th>Address</th><th>Sold</th><th class="r">Price</th><th class="r">Sq ft</th><th class="r">$/sq ft</th></tr></thead><tbody>${comps.map(x=>`<tr><td>${esc(x.addr)}, ${esc(x.city)}</td><td>${esc(x.date)}</td><td class="r">${money(x.price)}</td><td class="r">${x.sf.toLocaleString("en-US")}</td><td class="r">$${(x.price/x.sf).toFixed(0)}</td></tr>`).join("")}</tbody></table>
<p>Median ${money(m).replace(/\$/,"$")}${""}/sq ft × ${sf.toLocaleString("en-US")} sq ft = <b>${money(ask)}</b>. The current value is ${pct(gap)} ${gap>=0?"above":"below"} what these sales support${ownD&&ownP?`; the property itself sold ${ownD.slice(0,7)} for ${money(ownP)}`:""}. I ask the Board to set the ${yr} estimated market value at ${money(ask)}.</p>
<p style="margin-top:22px">Signature: <span class="fill" style="min-width:18em">&nbsp;</span> &nbsp; Date: <span class="fill" contenteditable="true">&nbsp;</span></p>
<div class="box"><b>How to use this (${esc(c.name.split(" (")[0])}).</b><ol>${c.steps.map(s=>`<li>${esc(s)}</li>`).join("")}</ol>Tax Court petition on the 2026 value: by ${esc(DEAD.statewide.next.tax_court_for_2026_value)}. Next notices: ${esc(DEAD.statewide.next.notices)}; local boards ${esc(DEAD.statewide.next.local_boards)}. Assessor ${esc(c.assessor_phone)}. Source: ${esc(c.url)} (read ${esc(c.read_on)}). Comparable sales from county recorder and assessor data via brickandmortar.dev; prices not adjusted for time.</div>`}
async function unlock(pw,via){const {zip,row}=CUR;const r=await fetch(`/api/data?zip=${zip}&pk=${encodeURIComponent(row[0])}`,{headers:{"x-password":pw}});
 if(!r.ok){const j=await r.json().catch(()=>({}));if(r.status===401){PW=null;try{localStorage.removeItem("pw:"+OFFER.product)}catch(e){}}$("pwMsg").textContent=j.error||"That didn't unlock.";return false}
 const j=await r.json();PW=pw;try{localStorage.setItem("pw:"+OFFER.product,pw)}catch(e){}
 const body=$("compBody");body.innerHTML=j.comps.map(c=>compRow(c)).join("");
 $("lock").innerHTML=`<h3><span class="k">Unlocked</span> Your comps and letter</h3><p class="hint">Your password works on any device: enter it under "Have a password?".</p>`;
 $("letter").innerHTML=letterHtml(j.comps);$("letterwrap").hidden=false;track("unlock",{via});return true}
$("find").onsubmit=async e=>{e.preventDefault();$("err").hidden=true;const z=$("zip").value.trim(),a=$("addr").value.trim();
 if(!/^\d{5}$/.test(z)){return showErr("Add your 5-digit ZIP so we load the right street list.")}
 if(!a){return showErr("Type your street address.")}
 const b=$("go");b.disabled=true;b.textContent="Looking…";
 try{const zd=await zipData(z,shardOf(a));const f=findRow(zd.homes,a);if(f.err){showErr(f.err);track("home_not_found",{zip:z})}else{OVERRIDE=null;CUR={zip:z,row:f.row,zipdata:zd};render();track("home_found",{zip:z});$("home").scrollIntoView({behavior:"smooth",block:"start"})}}
 catch(err){showErr(err.message)}
 b.disabled=false;b.textContent="Check my home"};
function showErr(m){$("err").textContent=m;$("err").hidden=false}
$("pwGo").onclick=async()=>{const ok=await unlock($("pwIn").value.trim(),"typed");if(!ok&&!$("pwMsg").textContent)$("pwMsg").textContent="That password didn't match."};
let CO=null;
$("buy").onclick=async()=>{track("checkout_open");if(CO){$("checkout").scrollIntoView({behavior:"smooth"});return}const b=$("buy");b.disabled=true;
 try{const r=await fetch("/api/checkout",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({token:TOKEN,pk:CUR.row[0],zip:CUR.zip,sh:CUR.zipdata.shard})});const j=await r.json();if(!j.clientSecret)throw 0;
 const st=Stripe(OFFER.stripe_pk);CO=await st.initEmbeddedCheckout({fetchClientSecret:async()=>j.clientSecret});CO.mount("#checkout")}catch(e){$("pwMsg").textContent="Checkout couldn't start. Try again in a minute."}b.disabled=false};
$("print").onclick=()=>{track("print");window.print()};
async function load(pk,zip,sh){const zd=await zipData(zip,sh);const row=zd.homes.find(r=>r[0]===pk);if(!row)throw new Error("home missing");CUR={zip,row,zipdata:zd};$("addr").value=row[1];$("zip").value=zip;render()}
(async()=>{const u=new URLSearchParams(location.search);const sid=u.get("paid"),pw=u.get("pw"),qpk=u.get("pk");
 let ex=null;if(TOKEN){try{const r=await fetch(`/data/for/${TOKEN}.json`);if(r.ok){ex=await r.json();VARIANT=ex.variant||""}}catch(e){}}
 if(!ex){try{ex=await (await fetch("/data/example.json")).json()}catch(e){}}
 if(qpk&&/^[a-z]+:[A-Za-z0-9-]+$/.test(qpk)&&u.get("zip")&&u.get("sh")){ex={pk:qpk,zip:u.get("zip"),shard:u.get("sh")}}
 $("mCounties").textContent=Object.values(META.counties).map(c=>`${c.name}: ${c.assessment_year}`).join("; ");$("mSince").textContent=new Date(META.sales_since+"T12:00").toLocaleDateString("en-US",{month:"long",year:"numeric"});$("mBuilt").textContent=META.built;
 $("mCounts").textContent=`Across ${META.homes.toLocaleString("en-US")} homes and ${META.sales.toLocaleString("en-US")} sales, the county sits 10% or more above the comparable sales on ${Math.round(META.argue/META.homes*100)}% of homes, and the sales back the county on ${Math.round(META.backs/META.homes*100)}%.`+(META.backtest&&META.backtest.n?` Checked against ${META.backtest.n.toLocaleString("en-US")} homes that sold themselves since January 2025 (a home is never its own comp): ${Math.round(META.backtest.within_10pct*100)}% sold within 10% of this number, so treat a gap under 10% as a phone call, not a fight.`:"");
 try{if(ex&&ex.pk&&ex.zip)await load(ex.pk,ex.zip,ex.shard||"0")}catch(e){}
 if(pw){await unlock(pw,"link")}
 if(sid){const r=await fetch("/api/session-status?session_id="+encodeURIComponent(sid));const j=await r.json();if(j.paid){track("paid");if(j.password){await unlock(j.password,"paid");$("pwMsg").textContent=`Paid. Your password is ${j.password}; it is also in the email and the Stripe receipt sent to ${j.email||"you"}.`}}}
 track("preview_open")})();
</script></body></html>"""


def main():
    html = (TEMPLATE.replace("__POSTHOG__", POSTHOG).replace("__PRICE__", str(OFFER["price_usd"])).replace("__NEXT_NOTICES__", DEAD["statewide"]["next"]["notices"]).replace("__NEXT_BOARDS__", DEAD["statewide"]["next"]["local_boards"])
            .replace("__OFFER__", json.dumps({k: OFFER[k] for k in ("product", "name", "price_usd", "stripe_pk")}))
            .replace("__META__", json.dumps(META, separators=(",", ":"))).replace("__DEAD__", json.dumps(DEAD, separators=(",", ":"))))
    (ROOT / "site/public/index.html").write_text(html)
    print(f"wrote site/public/index.html ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
