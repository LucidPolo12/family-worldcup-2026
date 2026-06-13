# Auto-Publish Setup — GitHub + Netlify

Goal: change a result or pick → it appears on the live site automatically, no manual upload.

How it works: the site reads **`data.json`** on load. The script `regenerate_data.py` rebuilds
`data.json` from `FamilyWorldCup2026.xlsx`. GitHub stores the files; Netlify watches GitHub and
re-publishes the moment anything is pushed. So the loop becomes: **update spreadsheet → regenerate →
push → live**.

---

## One-time setup (≈15 min)

### 1. Create a GitHub repo (private)
- Go to github.com → New repository.
- Name it e.g. `family-worldcup-2026`. Choose **Private** (keeps the spreadsheet out of public view).
- Create it (no README needed).

### 2. Push this folder to the repo
From this folder in a terminal:
```
git init
git add .
git commit -m "Family World Cup portal"
git branch -M main
git remote add origin https://github.com/<your-username>/family-worldcup-2026.git
git push -u origin main
```
(If git asks you to sign in, use your GitHub account / a personal access token.)

### 3. Connect Netlify to the repo
- Netlify → **Add new site → Import an existing project → GitHub** → pick the repo.
- **Build command:** leave blank. **Publish directory:** `.` (the repo root).
- Deploy. Netlify gives you a URL; you can keep your existing
  `familyworldcupchallenge2026.netlify.app` name (Site settings → Domain).

That's it — pushes to `main` now auto-publish.

---

## The update loop (every time results/picks change)
```
python3 regenerate_data.py          # rebuilds data.json from the spreadsheet
git add data.json FamilyWorldCup2026.xlsx
git commit -m "Update results"
git push
```
Netlify republishes in ~30–60s. No more dragging folders.

## Optional: make the daily task push automatically
Once the repo exists, the daily scoring task can run `regenerate_data.py` and `git push`
on its own using a stored GitHub token — ask Claude to wire this up and it becomes fully
hands-off. (Until then, the one `git push` above is the only manual step.)

## Notes
- `data.json` is the live data; the big inline block in `index.html` is just an offline fallback.
- Opening `index.html` directly as a file still works (uses the fallback); the `data.json`
  refresh only kicks in when served over http (local server or Netlify).
- Keep the repo **private** so the spreadsheet isn't publicly browsable. The published site is
  still public, which is fine — it only exposes the same scores everyone already sees.
