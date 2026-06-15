#!/usr/bin/env python3
"""Regenerate data.json for the Family World Cup portal from FamilyWorldCup2026.xlsx.

data.json is the LIVE data source the portal fetches on load. After any change to
the spreadsheet (results or picks), run:  python3 regenerate_data.py
Then publish (commit/push or upload data.json). The portal picks it up automatically.
"""
import openpyxl, json, os, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "FamilyWorldCup2026.xlsx")
OUT  = os.path.join(HERE, "data.json")

# Player -> (Pred-Home col, Pred-Away col) in the Match Predictions sheet
PCOLS = [("Ewan","I","J"),("Nana","L","M"),("Emrys","O","P"),("Nonno","R","S"),
         ("Nonna","U","V"),("Boompa","X","Y"),("Xavier","AA","AB"),
         ("Autumn","AD","AE"),("River","AG","AH")]
CHAMPS = {"Ewan":"Spain","Nana":"France","Nonno":"Brazil","Boompa":"France"}
PHOTOS = {"Nonno":"nonno-bobblehead.jpg","Emrys":"emrys-bobblehead.jpg",
          "Nana":"nana-bobblehead.jpg","Nonna":"nonna-bobblehead.jpg",
          "Boompa":"boompa-bobblehead.jpg","Autumn":"autumn-bobblehead.jpg",
          "River":"river-bobblehead.jpg","Xavier":"xavier-bobblehead.jpg",
          "Ewan":"ewan-bobblehead.jpg"}

def compute_ranks(standings):
    """Rank purely by points (ties share a rank), matching the front-end logic."""
    s = sorted(standings, key=lambda x: (-x["matchPts"], -x["exact"], -x["correct"], x["name"]))
    ranks, rank = {}, 1
    for i, x in enumerate(s):
        if i > 0 and x["matchPts"] < s[i-1]["matchPts"]:
            rank = i + 1
        ranks[x["name"]] = rank
    return ranks

def pts(ph, pa, ah, aa):
    if None in (ph, pa, ah, aa): return None
    if ph == ah and pa == aa: return 8
    sign = lambda x, y: (x > y) - (x < y)
    return 3 if sign(ph, pa) == sign(ah, aa) else 0

def main():
    wb = openpyxl.load_workbook(XLSX)
    ws = wb["Match Predictions"]

    # Results come from results.json (owned & auto-filled by the GitHub Action) merged
    # with any scores typed directly into the spreadsheet's G/H columns. results.json wins.
    rstore = {}
    rpath = os.path.join(HERE, "results.json")
    if os.path.exists(rpath):
        try:
            rstore = {int(k): v for k, v in json.load(open(rpath, encoding="utf-8")).items()}
        except Exception:
            rstore = {}

    # Family-submitted picks (from the Google Sheet via fetch_picks.py) override the
    # spreadsheet's pick cells per player+match.
    pjson = {}
    ppath = os.path.join(HERE, "picks.json")
    if os.path.exists(ppath):
        try:
            pjson = json.load(open(ppath, encoding="utf-8")) or {}
        except Exception:
            pjson = {}

    results = {}
    for r in range(4, 108):
        n = r - 3
        g, h = ws["G"+str(r)].value, ws["H"+str(r)].value
        if n in rstore:
            results[n] = rstore[n]
        elif g is not None and h is not None:
            results[n] = [g, h]
    # "generated" = date of the first match with no result yet (the next slate to pick)
    generated = None
    for r in range(4, 108):
        if (r - 3) not in results:
            d = ws["B"+str(r)].value
            generated = d.strftime("%Y-%m-%d") if d else None
            break
    mres = {n: (results[n][0], results[n][1]) if n in results else (None, None)
            for n in range(1, 105)}

    standings = []
    for name, hc, ac in PCOLS:
        picks, mp, ex, cor = [], 0, 0, 0
        pj = pjson.get(name, {})
        for r in range(4, 108):
            n = r-3
            ov = pj.get(str(n))
            if ov:
                ph, pa = ov[0], ov[1]
            else:
                ph, pa = ws[hc+str(r)].value, ws[ac+str(r)].value
            if ph is None and pa is None: continue
            ah, aa = mres[n]; p = pts(ph, pa, ah, aa)
            picks.append({"n": n, "ph": ph, "pa": pa, "pts": p})
            if p is not None:
                mp += p
                if p == 8: ex += 1
                if p > 0: cor += 1
        standings.append({"name": name, "matchPts": mp, "exact": ex, "correct": cor,
                          "champ": CHAMPS.get(name), "photo": PHOTOS.get(name), "picks": picks})

    # Load the existing data.json once: keep probabilities, and use its rank
    # snapshots to work out day-over-day leaderboard movement.
    old = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f) or {}
        except Exception:
            old = {}
    probs = old.get("probs", {}) or {}

    # Day-over-day movement: prevRanks is the baseline (the ranks as of the last
    # day we ran). On the first run of a new day, yesterday's final ranks become
    # the new baseline; multiple runs the same day keep the same baseline.
    today_str = datetime.date.today().isoformat()
    cur_ranks = compute_ranks(standings)
    prev_ranks = old.get("prevRanks")
    old_today = old.get("ranksToday")
    if old_today and old_today.get("date") != today_str:
        prev_ranks = old_today

    data = {"generated": generated, "standings": standings,
            "results": results, "photos": PHOTOS, "probs": probs,
            "prevRanks": prev_ranks,
            "ranksToday": {"date": today_str, "ranks": cur_ranks}}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Wrote {OUT}: {len(standings)} players, {len(results)} results, "
          f"{len(probs)} probs kept, generated={generated}")

if __name__ == "__main__":
    main()
