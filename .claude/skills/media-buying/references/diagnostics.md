# Funnel diagnostics

"CPA is high" is a symptom with four possible causes, and each has a different
fix. Changing the budget fixes none of them. Walk the stages in order; the first
one that deviates from the account's own baseline by the largest multiple is the
one to work on.

```
spend → impressions → clicks → landing views → conversions → approved
         └ CPM ┘      └ CTR ┘   └ LP rate ┘     └  CR  ┘      └  A  ┘
```

## Stage 1 — CPM: is traffic itself expensive?

Compare against the same geo/placement/period in the same account, not against
industry numbers.

| Reading | Likely cause | Fix |
|---|---|---|
| CPM up 2-3× vs baseline | auction pressure (seasonality, competitors) or audience too narrow | widen audience, change placement mix, reconsider the geo window |
| CPM high only on new account | no pixel history, low account trust | expect 1-2 weeks of worse numbers; don't retune thresholds for it |
| CPM high + low delivery + policy flags | account quality | fix the underlying policy issue; more budget makes it worse |
| CPM normal | not the problem | go to stage 2 |

## Stage 2 — CTR: does the creative earn attention?

Link CTR, not "all CTR" — all-CTR counts reactions and profile taps and will
happily hide a dead hook.

Below `~0.8%` link CTR in most feed placements the creative is not working, and
no downstream fix compensates: cheap clicks from a bad hook are cheap because
they're worthless. This is R3's whole justification.

The fix is a new **angle**, not a new colour. If three angles in a row read the
same, the problem is one level up — the offer isn't interesting to this
audience, and the audience should change, not the creative.

## Stage 3 — LP rate and CR: does the page hold them?

Landing page views divided by link clicks is the leak nobody looks at. Losing
30-50% between click and page view means the page is too slow, geo-blocked, or
broken on the device mix that's actually arriving — check mobile specifically,
it's most of the traffic.

Conversion rate on the page then depends on:

- **Creative-to-page match.** The page must continue the ad's promise. The
  single most common CR killer is a creative that sells one thing and a page
  that presents another.
- **Speed.** Every extra second costs conversions; test on throttled mobile,
  not on the desktop it was built on.
- **Form friction.** Each field removed is measurable CR. Ask only for what the
  call center genuinely needs.
- **Prelander.** When the offer needs context, a prelander raises CR; when it
  doesn't, it's a step that leaks. Test both, don't assume.

## Stage 4 — Approve: are the conversions real?

Falling approve with stable CPA is the most dangerous pattern in this business:
every dashboard stays green while the actual margin goes negative, because `T`
is derived from `A` and `A` moved.

| Reading | Likely cause | Fix |
|---|---|---|
| Approve down on one geo | traffic quality or call center coverage in that geo | check hours of operation, language, retry policy |
| Approve down after scaling | budget reached a worse audience segment | that's the marginal-CPA signal — stop the ladder |
| Approve down after a creative change | new angle attracts curiosity, not intent | revert or re-qualify in the creative |
| Approve stable | economics intact | recompute `T` anyway if payout changed |

Recompute `T` whenever payout or approve moves more than ~10%, and restate the
whole threshold table from the new `T` rather than adjusting individual rules.

## Where breakdowns beat rules

Meta's automated rules can only kill a whole ad set. Most bleeding is not evenly
distributed inside it — it concentrates in one placement, one geo, one age band
or a few hours of the day. Pull the same insights with `breakdowns` (see
`marketing-api.md`), find the segment carrying the loss, and exclude that segment
instead of killing the ad set. Typical finds, in rough order of frequency:

1. Audience Network / Reels spending at 3-5× the feed's CPA.
2. One geo in a multi-geo ad set carrying the entire overspend.
3. Night hours with clicks and no conversions because nobody answers the phone.
4. An age band far outside the buyer profile that the algorithm keeps testing.

Each of these is invisible in the ad-set-level number that rules see, which is
the main argument for running the API autopilot alongside the rules rather than
instead of them.
