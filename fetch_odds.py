#!/usr/bin/env python3
"""Fetch pre-match win/draw/win probabilities for upcoming World Cup games and
merge them into data.json (the "probs" field). Source: The Odds API (free tier).

Setup (one time):
  1. Get a free API key at https://the-odds-api.com  (free tier = 500 requests/month).
  2. Put the key in a file next to this script named  odds_key.txt  (one line),
     OR set the environment variable  ODDS_API_KEY.
     (odds_key.txt is gitignored, so the key never leaves your machine / never goes public.)

Run AFTER regenerate_data.py:
    python3 regenerate_data.py
    python3 fetch_odds.py
Then commit & push data.json. The portal shows the W/D/W bars on upcoming games.

The public site only ever reads the finished probabilities in data.json — the key is
used here at fetch time only and is never embedded in any published file.
"""
import json, os, re, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data.json")

# --- API key (local only) ---
KEY = os.environ.get("ODDS_API_KEY")
keyfile = os.path.join(HERE, "odds_key.txt")
if not KEY and os.path.exists(keyfile):
    KEY = open(keyfile, encoding="utf-8").read().strip()
if not KEY:
    raise SystemExit("No API key. Create odds_key.txt or set ODDS_API_KEY. "
                     "Get a free key at https://the-odds-api.com")

def get(url):
    return json.loads(urllib.request.urlopen(url, timeout=30).read())

# Map bookmaker team names -> the names used in the spreadsheet/portal.
ALIAS = {
    "United States": "USA", "USA": "USA",
    "Korea Republic": "South Korea", "South Korea": "South Korea",
    "Turkey": "Türkiye", "Türkiye": "Türkiye", "Turkiye": "Türkiye",
    "Czech Republic": "Czechia", "Czechia": "Czechia",
    "Côte d'Ivoire": "Ivory Coast", "Cote d'Ivoire": "Ivory Coast", "Ivory Coast": "Ivory Coast",
    "Democratic Republic of the Congo": "DR Congo", "Congo DR": "DR Congo", "DR Congo": "DR Congo",
    "Cabo Verde": "Cape Verde", "Cape Verde": "Cape Verde",
    "Curacao": "Curaçao", "Curaçao": "Curaçao",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina", "Bosnia and Herzegovina": "Bosnia and Herzegovina",
}
def norm(name):
    return ALIAS.get((name or "").strip(), (name or "").strip())

def find_sport_key():
    sports = get(f"https://api.the-odds-api.com/v4/sports/?apiKey={KEY}&all=true")
    # prefer an active FIFA World Cup soccer sport
    cands = [s for s in sports if "soccer" in s["key"]
             and "world cup" in s["title"].lower()
             and "women" not in s["title"].lower()
             and "qualif" not in s["title"].lower()]
    cands.sort(key=lambda s: (not s.get("active", False),))
    if cands:
        print("Using sport:", cands[0]["key"], "—", cands[0]["title"],
              "(active)" if cands[0].get("active") else "(inactive)")
        return cands[0]["key"]
    print("WARNING: no FIFA World Cup sport found; defaulting to soccer_fifa_world_cup")
    return "soccer_fifa_world_cup"

def fixtures_index():
    """(home, away) -> match number, for group-stage games with real team names."""
    txt = open(os.path.join(HERE, "WorldCupPicks.html"), encoding="utf-8").read()
    fix = json.loads(re.search(r"const FIX = (\[.*?\]);", txt, re.S).group(1))
    idx = {}
    for f in fix:
        if f.get("h") and f.get("a") and "TBD" not in (f["h"], f["a"]) and "Group" not in f["h"]:
            idx[(f["h"], f["a"])] = f["n"]
    return idx

def novig(dh, dd, da):
    ih, idr, ia = 1/dh, 1/dd, 1/da
    s = ih + idr + ia
    return {"h": round(ih/s, 4), "d": round(idr/s, 4), "a": round(ia/s, 4)}

def main():
    data = json.load(open(DATA, encoding="utf-8"))
    idx = fixtures_index()
    sport = find_sport_key()
    events = get(f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
                 f"?apiKey={KEY}&regions=us,uk,eu&markets=h2h&oddsFormat=decimal")
    probs = data.get("probs", {}) or {}
    matched, unmatched = 0, []
    for ev in events:
        home, away = norm(ev.get("home_team", "")), norm(ev.get("away_team", ""))
        n = idx.get((home, away)) or idx.get((away, home))
        hs, ds, aw = [], [], []
        for bk in ev.get("bookmakers", []):
            for mk in bk.get("markets", []):
                if mk.get("key") != "h2h":
                    continue
                o = {}
                for x in mk.get("outcomes", []):
                    o["Draw" if x["name"] == "Draw" else norm(x["name"])] = x["price"]
                if home in o and away in o and "Draw" in o:
                    hs.append(o[home]); ds.append(o["Draw"]); aw.append(o[away])
        if n and hs:
            avg = lambda L: sum(L)/len(L)
            probs[str(n)] = novig(avg(hs), avg(ds), avg(aw))
            matched += 1
        elif not n:
            unmatched.append(f'{ev.get("home_team")} vs {ev.get("away_team")} ({ev.get("commence_time","")[:10]})')
    data["probs"] = probs
    json.dump(data, open(DATA, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"\nUpdated probs for {matched} matches; {len(probs)} total in data.json.")
    if unmatched:
        print(f"\n{len(unmatched)} API events did NOT match a fixture (send these to Claude to add name aliases):")
        for u in unmatched:
            print("  -", u)

if __name__ == "__main__":
    main()
