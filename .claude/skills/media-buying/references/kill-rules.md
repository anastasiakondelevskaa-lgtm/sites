# Kill rules and Meta automated rules

All thresholds are multiples of `T` (target CPA). Worked column assumes `T = $6`,
test ad set budget `B = 3×T = $18`.

## Contents
- [Floor 1 — TEST](#floor-1--test)
- [Floor 2 — SCALE](#floor-2--scale)
- [Threshold formulas](#threshold-formulas)
- [Settings that make rules lie](#settings-that-make-rules-lie)
- [Failure modes](#failure-modes)

## Floor 1 — TEST

Scope: ad sets whose name contains `TEST`. Level: ad set.

| # | Name | Conditions | Time range | Frequency | Action | Worked (T=$6) |
|---|---|---|---|---|---|---|
| R1 | Kill-zero | Spent ≥ `1.5×T` AND Results = 0 | Today | Continuously | Turn off | $9, 0 conv |
| R2 | Kill-cost | Spent ≥ `2×T` AND Cost per result > `1.5×T` | Today | Continuously | Turn off | $12, CPA>$9 |
| R3 | Junk filter | Impressions ≥ 2000 AND CTR(link) < 0.8% AND Results = 0 | Today | Continuously | Turn off | — |
| R4 | 3-day cleanup | Spent ≥ `5×T` AND Cost per result > `T` | Last 3 days | Daily 03:00 | Turn off | $30, CPA>$6 |
| R5 | Promotion flag | Spent ≥ `3×T` AND Cost per result ≤ `T` AND Results ≥ 5 | Last 3 days | Daily 02:00 | Notification | $18, CPA≤$6 |

R3 is the highest-leverage rule and the one most often missing. It cuts empty
creatives before they reach the R1 threshold — a creative that can't earn a
click won't earn a conversion, and waiting for `1.5×T` to prove it costs roughly
a third of the testing budget for nothing.

R5 deliberately neither kills nor scales. It says a bundle has earned promotion;
a human (or the autopilot) renames `TEST |` → `SCALE |`, which moves it under the
other rule set. That rename is the moment the bundle stops being disposable.

## Floor 2 — SCALE

Scope: ad sets whose name contains `SCALE`. Level: ad set.

| # | Name | Conditions | Time range | Frequency | Action | Worked (T=$6) |
|---|---|---|---|---|---|---|
| R6 | Emergency stop | Spent ≥ `3×T` AND Results = 0 | Today | Continuously | Turn off | $18, 0 conv |
| R7 | Soft cut | Spent ≥ `4×T` AND Cost per result > `1.3×T` | Last 3 days | Daily 03:00 | Budget −25% | $24, CPA>$7.80 |
| R8 | Ladder up | Cost per result ≤ `0.85×T` AND Results ≥ 6 | Last 3 days | Daily 02:00 | Budget +20%, cap | CPA≤$5.10 |
| R9 | Finisher | Spent ≥ `10×T` AND Cost per result > `1.5×T` | Last 7 days | Daily 03:00 | Turn off | $60, CPA>$9 |

There is intentionally no same-day burn rule here beyond R6 at `3×T`. A proven
bundle running 3-5 conversions/day will have empty days — that's Poisson noise,
not death. Killing on it converts a working asset into a restart, and a restart
costs the learning phase again.

R7 cuts budget instead of killing. A bundle at `1.3×T` is not profitable but is
still close; shrinking it keeps the pixel signal and the social proof on the
creative alive while the loss is bounded. R9 is what finally ends it if a week
of that doesn't recover.

R7 and R8 cannot both fire (CPA is either ≤`0.85×T` or >`1.3×T`). Preserve that
dead band when retuning — if the windows touch, the budget oscillates nightly
and the ad set never exits learning.

## Threshold formulas

```
T   = target CPA = payout × approve × (1 − margin)
B   = test ad set daily budget      = 3 × T
R1  kill-zero (today)               spend ≥ 1.5×T,  results = 0
R2  kill-cost (today)               spend ≥ 2×T,    CPA_today > 1.5×T
R4  cleanup (3d)                    spend ≥ 5×T,    CPA_3d   > 1.0×T
R5  promote (3d)                    spend ≥ 3×T,    CPA_3d   ≤ 1.0×T, results ≥ 5
R6  emergency (today, SCALE)        spend ≥ 3×T,    results = 0
R7  soft cut (3d, SCALE)            spend ≥ 4×T,    CPA_3d   > 1.3×T  → −25%
R8  ladder (3d, SCALE)              CPA_3d ≤ 0.85×T, results ≥ 6      → +20%/day
R9  finisher (7d, SCALE)            spend ≥ 10×T,   CPA_7d   > 1.5×T
```

Tightening R1 below `1.5×T` looks like saving money and usually isn't: at `1×T`
a normal ad set gets killed before a single conversion is statistically likely,
so the account never accumulates winners. Loosen it (to `2×T`) when conversions
are slow to report, tighten it (to `1.2×T`) only when volume is high enough that
a bundle either converts early or not at all.

## Why the kill thresholds sit where they do

Conversions arrive as a Poisson process, so a zero is not proof of death — it
has a calculable probability even on a healthy ad set. At true CPA `T`, spend
`X` implies `X/T` expected conversions and the chance of observing zero anyway
is `e^(−X/T)`:

| Spend | Expected | Chance a **working** ad set shows zero |
|---|---|---|
| `1.5×T` | 1.5 | 22% |
| `2×T` | 2 | 14% |
| `3×T` | 3 | 5% |
| `4×T` | 4 | 1.8% |
| `5×T` | 5 | 0.7% |
| `10×T` | 10 | 0.005% |

This single table settles most threshold arguments:

**Where to put kill-zero.** At `1.5×T` roughly one healthy ad set in five dies
on its first day. Whether that's acceptable is an arithmetic question, not a
matter of taste: on ten test ad sets of which two work, `1.5×T` saves `4×T` on
junk and loses 0.44 of a winner, `2×T` spends that `4×T` and loses 0.27. Below
roughly `T = $10` the winner is worth far more than the difference, so use
`2×T`. At high `T`, where a test itself is expensive, `1.5×T` starts to pay.

**Why a proven ad set gets more rope, not less.** A week-old ad set on `3×T`
daily budget will show a blank day about once every three weeks purely from
variance. A rule that kills on it destroys a working asset on schedule.

**Why the emergency threshold must scale with budget.** On `10×T` of daily
spend, zero is a 1-in-20,000 event — effectively impossible by chance, so it
almost always means something actually broke and fast reaction is justified.
The same absolute threshold that is prudent at `3×T` is negligent at `10×T`.
When budgets move materially, the SCALE emergency stop moves with them.

**Why kill-cost rules need `Results ≥ 2`.** A single expensive conversion sets
a CPA that is one sample wide. Requiring two before acting on cost costs a few
dollars of patience and removes most false kills.

## Settings that make rules lie

**Attribution window.** Set per rule. Fast conversions (lead, registration) →
`1-day click`. Leaving `7-day click` makes the rule evaluate against a tail that
hasn't arrived yet, so it reads a live ad set as dead and kills it. Slow
conversions (purchase, deposit) → `7-day click, 1-day view`, and accept that
same-day rules will be noisy.

**Account time zone.** Rule schedules run on the ad account's time zone, not the
operator's. A "daily 03:00" cleanup scheduled against the wrong zone evaluates a
partial day and kills on incomplete data.

**"Continuously" is every ~30 minutes.** Between checks, an ad set keeps
spending: roughly $0.40-1 at $18/day, up to ~$5 at $150/day. That's why SCALE
thresholds are absolute money, not percentages of budget — a percentage rule on
a large budget lets a dead bundle burn a real sum inside one check interval.

**Rules never turn anything back on.** A killed ad set stays killed. Don't build
a `Turn on` rule to resurrect: it revives junk on partial data, at night, with
nobody watching. Resurrection is a morning decision made against 3-day numbers.

**Results ≠ tracker conversions.** Rules read the pixel. If approve, hold or
dedup live in a tracker or the network's API, every rule here is optimising a
proxy. Keep the proxy honest by measuring the gap weekly (pixel conversions vs
tracker conversions per campaign); when the gap exceeds ~15%, move the decision
logic to the API autopilot, which can read the real numbers.

## Failure modes

- **Killing inside the learning phase.** Nothing should fire in the first 2
  hours or below `0.5×T` spent. Because `1.5×T` is half of a `3×T` budget, R1
  naturally lands 4-6 hours in — verify that holds if the budget changes.
- **Rule scope silently widening.** Created from a filter, saved as "all active
  ad sets". Re-open every rule after saving and check the scope line.
- **Stacked rules on the same object.** A TEST-scoped and an account-wide rule
  both matching one ad set produce order-dependent outcomes. One floor, one rule
  set, no overlap.
- **Retuning on a single bad day.** Thresholds move when the economics move
  (payout, approve, margin) — not because yesterday was red.
