# Meta Marketing API operations

Everything Meta's automated rules can't express lives here: per-placement and
per-geo kills, hour-of-day analysis, real ROI from tracker postbacks, automatic
duplication of winners, and sub-30-minute reaction.

Pin an explicit API version in one constant (`GRAPH_API_VERSION`) and check the
changelog before bumping it — field names and defaults shift between versions,
and a silent bump is how a working autopilot starts reading empty arrays.

## Contents
- [Access setup](#access-setup)
- [Reading performance](#reading-performance)
- [Breakdowns](#breakdowns)
- [Write operations](#write-operations)
- [Rate limits](#rate-limits)
- [Safety rails](#safety-rails)

## Access setup

Agents and scripts are not people and don't get added as users. The correct
mechanism is a **System User** in Business Manager. The order below matters —
two of the steps are where setups reliably stall.

**Prerequisite.** Admin on the Business Manager itself (not merely on the ad
account), and the ad account already inside that BM. An ad account outside the
BM cannot be assigned to a system user.

**1. Create an app.** Tokens are always issued on behalf of an app; without one
the generate-token dialog shows an empty dropdown. `developers.facebook.com` →
My Apps → Create App → type **Business** → Add Product → **Marketing API** →
Settings → Basic → set Business Account to the BM.

Development mode is fine. For ad accounts the system user holds a role on
through the BM, `ads_management` works under Standard Access — App Review is
only needed to operate accounts outside the business.

**2. Link the app to the BM.** Business settings → Accounts → **Apps** → Add →
Add an app ID.

**3. Create the system user.** Business settings → Users → **System users** →
Add. Role **Employee** — sufficient for campaign management, and it withholds
control over people and payment methods.

**4. Assign assets — both of them.**

| Asset | Permission |
|---|---|
| Apps → the app from step 1 | **Develop app** |
| Ad accounts → the accounts it operates | **Manage campaigns** |
| Pixels (if reads are needed) | View |

Assigning the *app* as an asset is the step most often skipped. Linking it to
the BM in step 2 is not enough: without the asset assignment the token dialog
still shows no app to pick.

**5. Generate.** On the system user → Generate new token → pick the app →
**Token expiration: Never** (a 60-day token dies unattended, at night, mid-loop)
→ tick `ads_management` and `ads_read` (`business_management` only if BM-level
reads are genuinely needed) → copy immediately. It is shown once.

**6. Verify before trusting it.**

```bash
curl -s "https://graph.facebook.com/debug_token?input_token=$TOK&access_token=$TOK"
curl -s "https://graph.facebook.com/$V/me/adaccounts?fields=name,account_status,currency,timezone_name&access_token=$TOK"
curl -s "https://graph.facebook.com/$V/act_<ID>/insights?fields=spend,impressions,ctr&date_preset=yesterday&access_token=$TOK"
```

Expect `is_valid: true`, both scopes present, `expires_at: 0`. An empty
`adaccounts` list means step 4 was not completed; error `#200` means the account
is assigned without Manage campaigns; `#803` on an insights call usually means
the `act_` prefix is missing or a business ID was used instead of an account ID.

Note the account's `timezone_name` from that second call — every rule schedule
and every `time_range` in this system is interpreted in it, not in the
operator's local zone.

**7. Store it as a secret.** Environment variables for interactive sessions, the
CI secret store for the autopilot. Never in the repo, never in a commit, never
in a chat message — a leaked `ads_management` token lets someone else spend the
account's budget. Rotate when someone leaves the team, and keep one token per
environment so a compromised one can be revoked without stopping everything.

## Reading performance

```
GET /{GRAPH_API_VERSION}/act_<AD_ACCOUNT_ID>/insights
  level=adset
  fields=campaign_name,adset_id,adset_name,spend,impressions,clicks,ctr,cpm,
         frequency,actions,cost_per_action_type
  time_range={"since":"2026-09-15","until":"2026-09-17"}
  action_attribution_windows=["1d_click"]
  limit=500
```

Notes that decide whether the numbers are usable:

- `date_preset=today` exists but rolls over on the **ad account's** time zone;
  for anything that triggers spending decisions, pass explicit `time_range` so
  the window is unambiguous.
- `actions` is an array of `{action_type, value}` — pick the specific
  conversion type the campaign optimises for. Summing all action types counts
  page views and link clicks as conversions and makes every CPA look excellent.
- `action_attribution_windows` must match the rule doctrine: `1d_click` for fast
  conversions, `7d_click,1d_view` for slow ones. The default is not always what
  the UI shows, so set it explicitly.
- Insights are eventually consistent. The last 1-3 hours under-report; a kill
  decision made on the most recent hour will over-kill.
- For large accounts use the async job pattern (`POST .../insights` returns a
  `report_run_id`, poll it) rather than paging a huge synchronous response.

## Breakdowns

This is where the money hides — the ad-set number that rules see averages over
segments with wildly different CPAs.

| `breakdowns` | Finds |
|---|---|
| `publisher_platform,platform_position` | Audience Network / Reels burning at multiples of feed CPA |
| `country` | one geo carrying the whole overspend in a multi-geo ad set |
| `age,gender` | bands far outside the buyer profile |
| `hourly_stats_aggregated_by_advertiser_time_zone` | hours with clicks and no answered calls |
| `impression_device` | devices where the landing page is broken |

Not all breakdowns combine — Meta rejects some pairs, and some can't be used with
certain action-attribution settings. Query one axis at a time; it's also easier
to act on.

Acting on a breakdown finding means editing `targeting` (excluding a placement
or geo) or splitting the ad set. Both reset the learning phase, so the finding
has to be worth it: exclude when the losing segment is a large share of spend,
otherwise note it and apply the exclusion at the next natural restart.

## Write operations

```
POST /{V}/<ADSET_ID>            status=PAUSED
POST /{V}/<ADSET_ID>            daily_budget=<minor units>
POST /{V}/<CAMPAIGN_ID>/copies  deep_copy=true, status_option=PAUSED
POST /{V}/act_<ID>/adsets       <full adset spec>
```

- **`daily_budget` is in minor currency units** — `2200` means $22.00. This is
  the single most expensive off-by-100 in the API; every budget write should go
  through one helper that does the conversion and asserts a sane range.
- Budget changes re-enter the learning phase. One change per ad set per day,
  which is exactly why the ladder is `+20%/day` and not continuous.
- Duplicates land paused (`status_option=PAUSED`) and start at TEST budget under
  a TEST name — a proven creative on an unproven audience is an unproven bundle.
- Pausing is reversible and cheap; deleting is neither. The autopilot pauses,
  never deletes.

## Rate limits

Ads API limits are per-app and per-ad-account, and the response header
`X-Business-Use-Case-Usage` reports current utilisation as percentages. Read it
and back off above ~75% rather than waiting for errors.

Practical shape for a 15-minute cron: one insights call per level per window,
cached to disk, then decisions computed locally. Fan-out calls per ad set are
what actually trips the limit. On error code 17 or 613, exponential backoff; on
80004, slow the whole loop rather than retrying the single call.

## Safety rails

Any script that can spend or stop money carries these, without exception — the
failure mode is not a stack trace, it's a paused account or an emptied budget:

1. **`--dry-run` that prints every intended call** with the metric values that
   triggered it, reviewed before the first live run.
2. **A cap on actions per run** (e.g. no more than 20 pauses, no budget change
   above +25% in one step). A logic bug then costs one bounded batch instead of
   the account.
3. **Never operate below minimum spend.** Skip any ad set with less than `1×T`
   spent in the window; deciding on thin data is worse than not deciding.
4. **Log the reason with the action** — thresholds, actual values, window, and
   the response. Without it nobody can audit whether a kill was correct, and an
   unauditable autopilot gets switched off after the first surprise.
5. **Idempotency.** Re-running the same window must not double-apply a budget
   change; record what was applied per ad set per day and check before writing.
6. **Kill switch.** One env var or file that disables all writes, so the loop can
   be stopped without a deploy.
