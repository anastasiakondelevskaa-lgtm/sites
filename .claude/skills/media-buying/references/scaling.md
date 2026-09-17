# Scaling

A bundle earns scaling when it holds `CPA_3d ≤ T` over at least 5 conversions.
Below that volume the number is noise and scaling amplifies the noise, not the
result.

## Vertical: more budget, same ad set

`+20% per day, once per day.` The limit is not superstition — each budget change
re-enters the learning phase, and Meta re-explores the audience at the new spend
level. Two increases in one day stack two explorations on top of each other and
the ad set spends the day paying for discovery instead of conversions.

```
day 1  $18   CPA $5.10   → +20%
day 2  $22   CPA $5.40   → +20%
day 3  $26   CPA $5.20   → +20%
day 4  $31   CPA $7.90   → hold (no cut yet, one day is noise)
day 5  $31   CPA $5.60   → resume
```

Hold — don't cut — on the first bad day after an increase; that day is usually
the learning re-entry, not decay. Cut only if the second day confirms it, which
is exactly what R7 does on a 3-day window.

The ladder ends where the audience ends. When each increase produces
proportionally more spend but flat conversions and rising frequency, the ad set
has bought everyone reachable at that bid. Further budget buys worse users. Stop
and go horizontal.

## Horizontal: more surfaces, same winner

Each of these is a fresh learning phase and pays its own tuition, so run them one
axis at a time — otherwise a bad result can't be attributed to anything:

1. **New audience** — different interest cluster, lookalike, or broad with the
   same creative. Cheapest and usually first.
2. **New geo** — same angle, localised. Re-derive `T` first: payout and approve
   differ per geo, so the thresholds are different numbers even for the same
   offer.
3. **New placement** — a bundle strong in feed often dies in Reels and vice
   versa; treat each as a separate test with its own creative crop.
4. **New account / BM** — capacity and risk spreading, not optimisation. Only
   once the bundle is proven; a fresh account has no pixel history and will post
   worse numbers for the first days.

Duplicates start at the TEST floor with test budget, even though the creative is
proven — a proven creative on an unproven audience is an unproven bundle. It
gets promoted by R5 like everything else.

## CBO vs ABO

Test in **ABO**: equal budgets per ad set is the only way to learn which audience
works, because CBO will starve an ad set before it produces enough data to judge.

Scale in **CBO** once 3+ ad sets are proven: hand the allocation to Meta and let
it shift within the winning set. CBO with one proven and four unproven ad sets is
just an expensive way to fund the unproven ones.

When consolidating proven ad sets into a CBO campaign, set the campaign budget to
roughly the sum of what the proven ad sets already spend — starting far above it
resets everything into learning at once.

## Refresh before decay, not after

Frequency `> 2.5` with decaying CTR on the same audience means the creative is
spent. By the time CPA reflects it, the money is already gone. The signal to
watch is CTR trend against the ad set's own first-week baseline, not an absolute
number.

Refresh means a new angle on the same offer, not a recolour. Keep the winning
ad set structure and rotate creative into it — the structure carries the pixel
signal and the accumulated social proof, which a brand-new ad set doesn't have.

## When to stop scaling

Stop when marginal CPA exceeds `T`, even if average CPA still looks fine. The
average hides the last increment: an ad set at $100/day with average CPA $5.50
may be buying its last $20 at $11. Compute marginal CPA across the increase —
`(spend_after − spend_before) / (conv_after − conv_before)` — and let that, not
the average, decide the next step.
