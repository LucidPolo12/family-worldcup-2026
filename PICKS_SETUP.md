# Self-Service Picks — Google Sheet setup

Goal: family taps **Submit** on the pick page → picks land in a Google Sheet you own →
the GitHub Action folds them into the standings automatically. No more relaying texts.

You'll create one Sheet + paste one small script, then hand Claude one URL and add one
GitHub secret. ~10 minutes, one time.

---

## 1. Make the Sheet
- Go to **sheets.google.com** → blank spreadsheet. Name it e.g. **Family WC Picks**.
- Rename the bottom tab from `Sheet1` to **`Picks`** (double-click the tab).
- In row 1 type these 5 headers (one per cell): `timestamp` `name` `match` `predH` `predA`.

## 2. Add the receiver script
- In that Sheet: **Extensions → Apps Script**.
- Delete whatever's there, paste the entire contents of **`google-apps-script.gs`** (in your project folder), and **Save** (disk icon).
- Click **Deploy → New deployment** → gear icon → **Web app**.
  - **Description:** picks receiver
  - **Execute as:** **Me**
  - **Who has access:** **Anyone**
  - **Deploy**. Approve the permissions prompt (it's your own script).
- Copy the **Web app URL** it shows (ends in `/exec`). → **Send this URL to Claude.**

## 3. Publish the sheet as CSV (for the Action to read)
- Back in the Sheet: **File → Share → Publish to web**.
- Under "Link": pick the **Picks** tab, and format **Comma-separated values (.csv)**.
- Click **Publish** → **OK**. Copy the URL it gives (contains `output=csv`).

## 4. Add that CSV URL as a GitHub secret
- GitHub repo **family-worldcup-2026 → Settings → Secrets and variables → Actions → New repository secret**.
- **Name:** `PICKS_CSV_URL`  **Value:** the CSV URL from step 3 → **Add secret**.

---

## What Claude does with your Web App URL
- Pastes it into `WorldCupPicks.html` (`SCRIPT_URL`) so the Submit button posts to your script, then commits/pushes.

## Test it
1. Open the live pick page, choose a name, tap a couple scores, hit **Submit ✅** → you should see "Picks submitted!".
2. Check the **Picks** Google Sheet — new rows should appear.
3. On GitHub → Actions → **Run workflow** → confirm it's green and a `picks.json` commit appears; the site standings then reflect the submitted picks.

## Champion & Podium ("final four") picks — auto-sync
The 🏆 Champion & Podium tab rides the **same** Sheet and pipeline — **no new sheet or secret needed**. Champion/Runner-up/3rd/4th land in the Picks tab as rows with a text code in the `match` column (`CHAMP`/`RUN`/`THIRD`/`FOURTH`) and the team name in `predH`; the Action folds them into each player's standings and shows them on the leaderboard automatically.
- **One thing to do:** re-deploy the updated `google-apps-script.gs`. In the Apps Script editor: paste the new file contents → **Save** → **Deploy → Manage deployments → (edit, pencil) → Version: New version → Deploy**. (Editing the existing deployment keeps the same `/exec` URL, so nothing else changes.)
- Podium picks lock server-side at **noon CDT, Sun Jun 28 2026** — any edit submitted at/after that is ignored, same idea as the per-game kickoff lock.

## Notes
- Until the URL + secret are set, nothing breaks: the Submit button falls back to the old "copy & send" text, and the Action's picks step is skipped.
- A pick submitted **after** a game kicks off is ignored automatically (lock by timestamp).
- You keep full oversight: the Google Sheet is yours to view or correct any time, and
  the spreadsheet (`FamilyWorldCup2026.xlsx`) still works as a manual override/backup.
