#!/usr/bin/env python3
"""Auto-record finished GROUP-STAGE results into results.json using The Odds API
/scores endpoint (same key as fetch_odds.py).

Why results.json (not the spreadsheet): the .xlsx is a binary file you edit by hand,
so having the automation write it too would cause Git merge conflicts. Instead the
Action writes a small text file, results.json, which merges cleanly. regenerate_data.py
combines results.json with any scores you typed into the spreadsheet's G/H columns.

Safety rules:
- GROUP STAGE only (knockout results are entered by hand — our scoring uses regulation
  time only, and the API's final score can include extra time / penalties).
- Never changes a result already known (idempotent).

Key: env ODDS_API_KEY (GitHub Actions secret) or local odds_key.txt.
CI order:  update_scores.py -> regenerate_data.py -> fetch_odds.py -> commit/push.
"""
import json, os, re, urllib.request, openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "FamilyWorldCup2026.xlsx")
RES = os.path.join(HERE, "results.json")
SPORT = "soccer_fifa_world_cup"

KEY = os.environ.get("ODDS_API_KEY")
kf = os.path.join(HERE, "odds_key.txt")
if not KEY and os.path.exists(kf):
    KEY = open(kf, encoding="utf-8").read().strip()
if not KEY:
    raise SystemExit("No API key (set ODDS_API_KEY or create odds_key.txt).")

ALIAS = {
    "United States": "USA", "Korea Republic": "South Korea", "Turkey": "Türkiye",
    "Turkiye": "Türkiye", "Czech Republic": "Czechia", "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast", "Democratic Republic of the Congo": "DR Congo",
    "Congo DR": "DR Congo", "Cabo Verde": "Cape Verde", "Curacao": "Curaçao",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
}
def norm(n): return ALIAS.get((n or "").strip(), (n or "").strip())

def group_index():
    """(home, away) -> match number, GROUP STAGE only."""
    txt = open(os.path.join(HERE, "WorldCupPicks.html"), encoding="utf-8").read()
    fix = json.loads(re.search(r"const FIX = (\[.*?\]);", txt, re.S).group(1))
    return {(f["h"], f["a"]): f["n"] for f in fix
            if f.get("stage", "").startswith("Group") and "TBD" not in (f["h"], f["a"])}

def main():
    idx = group_index()

    # what's already known: results.json plus any scores already typed in the spreadsheet
    store = {}
    if os.path.exists(RES):
        try:
            store = json.load(open(RES, encoding="utf-8"))
        except Exception:
            store = {}
    known = set(int(k) for k in store)
    try:
        ws = openpyxl.load_workbook(XLSX)["Match Predictions"]
        for r in range(4, 108):
            if ws["G"+str(r)].value is not None and ws["H"+str(r)].value is not None:
                known.add(r - 3)
    except Exception:
        pass

    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/scores/?apiKey={KEY}&daysFrom=3"
    events = json.loads(urllib.request.urlopen(url, timeout=30).read())

    wrote = []
    for ev in events:
        if not ev.get("completed") or not ev.get("scores"):
            continue
        home, away = norm(ev.get("home_team", "")), norm(ev.get("away_team", ""))
        n = idx.get((home, away))
        if not n or n in known:
            continue
        sc = {norm(s["name"]): s.get("score") for s in ev["scores"]}
        try:
            hs, as_ = int(sc[home]), int(sc[away])
        except (KeyError, TypeError, ValueError):
            continue
        store[str(n)] = [hs, as_]
        wrote.append(f"M{n}: {home} {hs}-{as_} {away}")

    if wrote:
        json.dump(store, open(RES, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"Auto-recorded {len(wrote)} new group-stage result(s):")
    for w in wrote:
        print("  +", w)
    if not wrote:
        print("  (nothing new to score)")

if __name__ == "__main__":
    main()
