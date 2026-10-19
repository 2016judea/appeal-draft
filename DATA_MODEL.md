# Data model: the residential assessment appeal draft

Written 2026-10-18 from the need alone, before the data was opened (BUSINESS.md rule 5).
The need: a Twin Cities homeowner types their address and gets the value to argue for,
the recorded sales that back it, the county's appeal window, and the one-page draft they
hand the local board. The step taken over is writing the appeal.

## Entities

### Home (the subject parcel)
| field | question it answers for the homeowner |
|---|---|
| parcel_key, county, pin | which record is mine; the PID the board's form asks for |
| house, street, city, zip | the address I type, and the one printed on the letter |
| lat, lon | how far away each comparable sale is |
| fin_sq_ft, year_built, use class | what "a home like mine" means when picking comps |
| homestead | which appeal route and which Tax Court division I can use |
| assessment_year (mkt_year) | which notice this value is from |
| emv_total (current) | the assessor's number I am arguing against (blue) |
| emv_prior (previous year) | how much it jumped, which is why I opened this |
| total_tax (payable this cycle) | what a cut is worth to me per year |
| own last sale date, price | whether my own purchase already argues the point |

### Sale (a recorded arm's-length sale nearby)
| field | question it answers |
|---|---|
| parcel_key of the sold home, address | which house, so the board can look it up |
| sale_date, sale_price | when and for how much |
| fin_sq_ft, year_built of the sold home | is it like mine |
| price_per_sqft | the one number the comparison runs on |
| sale_price / its EMV | was it arm's length (throws out family transfers, garage stalls, partial interests) |
| distance_miles to the subject | nearer wins |

### Comp set (subject → 3–5 sales)
| field | question it answers |
|---|---|
| rank, why chosen (distance, size, age, recency) | why these five and not others |
| comp $/sqft, subject sqft × median comp $/sqft | the value to argue for (green) |
| zip median sale $/sqft × subject sqft, n sales | what the market around me says in general (sand) |
| gap = emv / target − 1 | is the assessor above the sales, and by how much |

### Appeal window (one per county, per assessment year)
| field | question it answers |
|---|---|
| notice mailed (month) | when the number arrives |
| open book / local board window | when I can walk in |
| county board date and sign-up deadline | the second step |
| Tax Court petition deadline (April 30 of the pay year) | the last door, and which division (small claims for homesteads) |
| applies_to assessment year, payable year | which value this window is for |
| source_url, read_on | where this came from and when, so a stale date is visible |

### Appeal letter (one page)
Fields the local board's form asks for, filled from the above: to (board / assessor,
city), property address, PID, owner (typed by the homeowner), current EMV, requested
value, basis (the comp table), contact, date. Plus a box of the county's steps and dates.

## Joins
Home ⟶ Sale by zip (same market) and by distance (lat/lon); Sale ⟶ its own Home for
sqft, year_built and EMV; Home ⟶ Appeal window by county and assessment year.

## Free vs paid
Free: the headline (blue, sand, green) and one comp. Paid: the full comp set, the letter
with the county's fields and dates, the PDF.

## Reality check (filled in after opening the data, same day)

Source: `~/Desktop/bricks/data/closed_system.duckdb`, read-only. `parcel_snapshot`
(assessor rolls by `mkt_year`; vintage `metrogis_current` for the suburbs, Minneapolis
assessor files for Hennepin), `sale`, `address_index`.

| field | status |
|---|---|
| Home: all fields | filled for Ramsey, Anoka, Dakota, Scott, Washington (2026 or 2025 assessment) and Minneapolis (2025 assessment). **Hennepin outside Minneapolis: no snapshot, not served.** Carver: no `mkt_year`, not served. |
| emv_prior | filled by self-join on `mkt_year − 1`; Ramsey's `county_ramsey_2026_08` vintage has no sqft, so the current row is `metrogis_current`. |
| Minneapolis current value | the 2025 assessment (payable 2026). The 2026 notice (March 2026) is not in the store; the page says which year it shows and lets the owner type the number from their notice. |
| Sale: price_per_sqft, arm's length | filled: `sale` joined to the sold parcel's snapshot for sqft; sale/EMV outside 0.5–2.0 dropped. Sales since 2024-07-01. |
| Sale: distance | filled from parcel lat/lon. |
| Condos | excluded: the sold-parcel sqft and $/sqft are not comparable to houses and the condo-garage parcels pollute the ratio. Townhouses included. |
| Time adjustment of older sales | **not done.** Comps are ranked by recency among other things; prices are not indexed to the assessment date. Said on the page. |
| Appeal window | filled per county from the county assessor pages, URL and read date in `data/deadlines.json`. |
| Owner name | public record, but not printed: the owner types it on the letter. |

What this product is not: the commercial assessment screen killed 2026-09-24 (the
assessor passes the IAAO ratio tests in aggregate). This is the per-parcel residential
tail: the homes whose own EMV sits above what nearby sales of homes like them say, which
an aggregate ratio study cannot see.

Added 2026-10-19 after the second pass:
- **Lot size / water frontage: not in the comp rule.** The rule matches sqft, age and distance,
  so a lake lot or acreage reads low against its comps. Unfilled field: land (`emv_land` exists
  on the roll; a land-adjusted comp is the next build).
- **Backtest:** 30,224 homes that sold since 2025-01 (never their own comp): median sale = 1.00×
  target, 53% within ±10%. `meta.json → backtest`, recomputed per build.
- **Hennepin sale dates are month-grain** (every row is the 1st): printed as YYYY-MM.
