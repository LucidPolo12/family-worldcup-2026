# Knockout "Advance + Exact Score" upgrade — deploy steps

*Built 2026-06-28. Group-stage scoring and picks are completely untouched.*

## What changed (5 files)
- **regenerate_data.py** — new knockout scoring: **advance points** (you named the team that
  goes through, penalties included) **plus** an **exact-score bonus**. R32 = 5 + 7 = 12; later
  rounds keep the announced totals (R16 18, QF 25, SF 35, 3rd 25, Final 50). Group stage unchanged.
  Emits a new `advancing` map and a per-pick `adv` field to `data.json`.
- **fetch_picks.py** — reads a new `predAdv` column; stores it as the 3rd element of a tied knockout pick.
- **google-apps-script.gs** — receiver now writes/back-fills a `predAdv` column.
- **WorldCupPicks.html** — knockout cards relabel the score field, auto-confirm the advancing team
  on a decisive score, and require a "Who advances on penalties?" choice on a tie.
- **index.html** — shows who each player backed, scores with the new badge, notes penalty shootouts,
  and the bracket now flows on past a shootout. Scoring help text updated.

## Scoring (knockouts)
| Round | Advance | Exact-score bonus | Max |
|---|---|---|---|
| Round of 32 | 5 | 7 | 12 |
| Round of 16 | 8 | 10 | 18 |
| Quarterfinal | 12 | 13 | 25 |
| Semifinal | 18 | 17 | 35 |
| Third Place | 12 | 13 | 25 |
| Final | 25 | 25 | 50 |

Advance and exact-score are independent and add up. The **exact score is the final score after all
playing time** (90 min or extra time); **penalty-kick goals are never added** to the score.

## Steps for you
1. **Push the code.** Commit & push the 5 files. The GitHub Action re-runs `regenerate_data.py`
   (so `data.json` picks up the new scoring + `advancing` + `adv` fields) and Cloudflare Pages
   redeploys `index.html` + `WorldCupPicks.html`. Verify with a cache-bust:
   `https://family-worldcup-2026.pages.dev/data.json?v=<timestamp>`.
2. **Re-deploy the Apps Script** (REQUIRED for penalty picks to save): Picks sheet → Extensions →
   Apps Script → paste the updated `google-apps-script.gs` → Deploy → Manage deployments → edit →
   **New version** → Deploy. It auto-adds the `predAdv` header. *Until you do this, a tied-score
   knockout pick can't record who advances and would score the advance part as 0.*
3. **Add the advancing column to the sheet** (one-time, optional but recommended): in
   **Match Predictions**, put header **`Advancing (H/A)`** in cell **AJ3**. You only fill it when a
   knockout game ends **level and is decided on penalties** — type **H** if the home team advanced,
   **A** if the away team advanced. Decisive games need nothing (the higher score advances
   automatically). *(You can also record it in `results.json` as a 3rd element: `"89":[1,1,"H"]`.)*
4. **Enter Match 73 (Canada 1–0).** It's decisive, so no advancing entry is needed — just the score.
   Row 76: home = Group A 2nd, away = Group B 2nd. If **Canada was the home side**, set G76=1, H76=0;
   if **Canada was the away side**, set G76=0, H76=1. (Tell me which and I'll confirm the scoring.)

## Verified
All six of your test scenarios pass, group-stage scoring is unchanged, later-round maxes are correct,
and a full integration test confirms the advancing map, the additive scoring, the tied-pick edge case
(exact score + wrong penalty pick = score bonus only), and the manual-override paths.
