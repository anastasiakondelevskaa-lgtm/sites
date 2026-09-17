# Account and campaign structure

Structure exists to make decisions cheap: every rule, report and promotion in
this system keys off names and hierarchy. Sloppy naming means rules can't be
scoped and reports can't be grouped, so the whole doctrine degrades into manual
staring at a dashboard.

## Naming

```
Campaign :  <FLOOR> | <vertical> | <geo> | <objective>
Ad set   :  <FLOOR> | <vertical> | <geo> | <audience> | <angle>
Ad       :  <creative-id> | <format> | <angle> | <iteration>
```

`FLOOR` is `TEST` or `SCALE` and is the field every automated rule filters on.
It must be the first token so filters stay simple and unambiguous.

Never rename mid-flight except for the deliberate `TEST → SCALE` promotion —
that rename *is* the policy change, and renaming for any other reason silently
moves an ad set between rule sets.

## Hierarchy

```
Business Manager
├── Ad account (per vertical or per risk pool)
│   ├── Campaign TEST  | ...   (ABO, equal budgets, short leash)
│   └── Campaign SCALE | ...   (CBO once 3+ proven ad sets)
├── Pixel (one per domain; never share across unrelated offers)
└── Domain verification (own the domain you advertise)
```

One ad account per vertical keeps pixel signal clean — a pixel trained on two
unrelated conversion types optimises for neither. It also bounds the blast
radius if an account is restricted.

## Test discipline

- One variable per test. New audience *and* new creative *and* new geo in one ad
  set produces a number that can't be attributed to anything.
- 3-5 ads per ad set, let Meta allocate. Splitting creatives across ad sets at
  test budgets never reaches significance.
- Minimum evaluable spend is `3×T`. Reading a result below that is reading noise;
  most "this bundle doesn't work" verdicts at `$5` spent are wrong.
- Log every test, including the failures, with angle + audience + CTR + CPA. The
  graveyard is what stops the same losing angle being relaunched next quarter.

## Pixel and tracking hygiene

- Server-side events (CAPI) alongside the browser pixel — browser-only tracking
  under-reports, and every rule in this system reads reported conversions, so
  under-reporting directly causes wrongful kills.
- Deduplicate CAPI and pixel events by event ID, or conversions double-count and
  CPA reads better than reality.
- One conversion event per campaign objective. Optimising for a mix teaches the
  algorithm nothing.
- If a tracker (Keitaro/Binom) is the source of truth, reconcile it against Meta
  weekly per campaign. A gap over ~15% means rules are deciding on a proxy that
  has drifted, and decisions should move to the API layer.

## Account health

Longevity is an economic variable — a restricted account costs every bundle it
carried plus the pixel history. Practically:

- Keep the ad, the prelander and the offer consistent with each other; most
  policy trouble is a mismatch, not malice.
- Warm new accounts gradually; a brand-new BM opening at high daily spend is the
  classic restriction trigger.
- Keep domains, pages and payment methods clean and separated by risk pool, so
  one restriction doesn't cascade.
- Fix the underlying policy issue rather than working around review. Bundles
  that only survive by hiding from review distort every threshold here, because
  their measured CPA never includes the cost of the eventual ban.
