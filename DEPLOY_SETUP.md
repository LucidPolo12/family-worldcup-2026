# Hosting & Auto-Publish — GitHub + Cloudflare Pages

**Live site:** https://family-worldcup-2026.pages.dev
**Host:** Cloudflare Pages (free, unlimited). *Netlify is retired — the old
`familyworldcupchallenge2026.netlify.app` URL is dead; don't use it.*

How it works: Cloudflare Pages is linked to the GitHub repo **family-worldcup-2026**
(account LucidPolo12) and **auto-deploys branch `main` on every push** — build command
blank, output directory root. The page reads **`data.json`** on load for live data
(standings, results, odds, photos); the inline data in `index.html` is just an offline fallback.

---

## The automatic pipeline (hands-off)
Two GitHub Actions keep everything current and publish themselves:

- **Daily World Cup update** (`daily.yml`) — ~8am/1pm/6pm CT: records finished group-stage
  scores (`update_scores.py` → `results.json`), rebuilds `data.json` (`regenerate_data.py`),
  refreshes win/draw/win odds (`fetch_odds.py`), commits & pushes.
- **Picks refresh (fast)** (`picks-refresh.yml`) — every ~5 min: pulls family picks from the
  Google Sheet (`fetch_picks.py` → `picks.json`), rebuilds `data.json`, commits & pushes.

Every push triggers a Cloudflare deploy, so results, standings, group tables, odds and
submitted picks all appear on the live site by themselves.

Secrets live in GitHub (repo → Settings → Secrets and variables → Actions): `ODDS_API_KEY`
and `PICKS_CSV_URL`. They are encrypted, never in the code.

## Manual touches (the only things done by hand)
- **Knockout-round results:** enter by hand (our scoring uses regulation time only).
  Put the score in the spreadsheet's G/H columns (or `results.json`), run
  `python regenerate_data.py`, then commit & push.
- **Changing picks for the family:** they self-serve in the app; the spreadsheet stays a
  manual override/baseline if ever needed.

## Update loop, if you ever edit by hand
```
python regenerate_data.py        # rebuild data.json from the spreadsheet + results.json + picks.json
```
Then in GitHub Desktop: **Fetch/Pull** (catch the bots' commits) → **Commit** → **Push origin**.
Cloudflare republishes in ~30–60s.

## Notes
- Opening `index.html` directly as a file still works (uses the offline fallback); the
  `data.json` refresh only kicks in when served over http (local server or Cloudflare).
- Keep the repo's secrets in GitHub Actions only — never paste keys into the code.
