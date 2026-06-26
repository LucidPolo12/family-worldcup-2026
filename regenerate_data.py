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

# Escalating knockout point values: (correct result pts, exact score pts)
STAGE_PTS = {
    "Group Stage":  (3,  8),
    "Round of 32":  (5,  12),
    "Round of 16":  (8,  18),
    "Quarterfinal": (12, 25),
    "Semifinal":    (18, 35),
    "Third Place":  (12, 25),
    "Final":        (25, 50),
}

def match_stage(n):
    """Return the stage name for match number n (1-104)."""
    if n <= 72:  return "Group Stage"
    if n <= 88:  return "Round of 32"
    if n <= 96:  return "Round of 16"
    if n <= 100: return "Quarterfinal"
    if n <= 102: return "Semifinal"
    if n == 103: return "Third Place"
    return "Final"

def compute_ranks(standings):
    """Rank purely by points (ties share a rank), matching the front-end logic."""
    s = sorted(standings, key=lambda x: (-x["matchPts"], -x["exact"], -x["correct"], x["name"]))
    ranks, rank = {}, 1
    for i, x in enumerate(s):
        if i > 0 and x["matchPts"] < s[i-1]["matchPts"]:
            rank = i + 1
        ranks[x["name"]] = rank
    return ranks

def pts(ph, pa, ah, aa, n=1):
    """Return (points, is_exact). Points is None if result not yet known."""
    if None in (ph, pa, ah, aa): return None, False
    correct_pts, exact_pts = STAGE_PTS[match_stage(n)]
    if ph == ah and pa == aa: return exact_pts, True
    sign = lambda x, y: (x > y) - (x < y)
    return (correct_pts if sign(ph, pa) == sign(ah, aa) else 0), False

def score_golden_boot(gb, top_scorers):
    """Score Golden Boot picks against the official top-3 scorer list.

    top_scorers: list of player names in rank order (index 0 = Golden Boot winner).
    Scoring: pick1 exact (rank 1) = 40pts; pick1 in top-3 = 10pts;
             pick2/3 hits rank-1 = 20pts; pick2/3 in top-3 = 10pts.
    Returns 0 if top_scorers not yet populated.
    """
    if not top_scorers or not gb:
        return 0
    total = 0
    for pick_pos, pick_key in enumerate(["pick1", "pick2", "pick3"], 1):
        player = gb.get(pick_key, "").strip()
        if not player:
            continue
        try:
            actual_rank = top_scorers.index(player) + 1   # 1-based
        except ValueError:
            continue   # player not in top scorers list
        if actual_rank > 3:
            continue   # only top 3 count
        if pick_pos == 1 and actual_rank == 1:
            total += 40   # nailed the Golden Boot winner exactly
        elif pick_pos == 1:
            total += 10   # pick1 got a top-3 scorer (not #1)
        elif actual_rank == 1:
            total += 20   # pick2/3 named the actual Golden Boot winner
        else:
            total += 10   # pick2/3 got a top-3 scorer
    return total

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

    # Load existing data.json early: need topScorers before the standings loop,
    # and probs + rank snapshots for the output.
    old = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                old = json.load(f) or {}
        except Exception:
            old = {}
    probs = old.get("probs", {}) or {}
    top_scorers = old.get("topScorers") or []

    standings = []
    for name, hc, ac in PCOLS:
        picks, mp, ex, cor = [], 0, 0, 0
        pj = pjson.get(name, {})
        for r in range(4, 108):
            n = r - 3
            ov = pj.get(str(n))
            if ov:
                ph, pa = ov[0], ov[1]
            else:
                ph, pa = ws[hc+str(r)].value, ws[ac+str(r)].value
            if ph is None and pa is None: continue
            ah, aa = mres[n]
            p, is_exact = pts(ph, pa, ah, aa, n)
            picks.append({"n": n, "ph": ph, "pa": pa, "pts": p})
            if p is not None:
                mp += p
                if is_exact: ex += 1
                if p > 0: cor += 1

        # Champion & Podium picks, auto-synced from Google Sheet via fetch_picks.py.
        podium = pj.get("podium") or {}
        champ = podium.get("champ") or CHAMPS.get(name)
        gb = pj.get("goldenBoot") or {}
        gb_pts = score_golden_boot(gb, top_scorers)
        standings.append({"name": name, "matchPts": mp, "exact": ex, "correct": cor,
                          "champ": champ, "podium": podium, "goldenBoot": gb, "gbPts": gb_pts,
                          "photo": PHOTOS.get(name), "picks": picks})

    # Day-over-day movement: prevRanks is yesterday's final ranks; ranksToday
    # is the current run. Multiple runs the same day keep the same baseline.
    today_str = datetime.date.today().isoformat()
    cur_ranks = compute_ranks(standings)
    prev_ranks = old.get("prevRanks")
    old_today = old.get("ranksToday")
    if old_today and old_today.get("date") != today_str:
        prev_ranks = old_today

    data = {
        "generated": generated,
        "standings": standings,
        "results": results,
        "photos": PHOTOS,
        "probs": probs,
        "prevRanks": prev_ranks,
        "ranksToday": {"date": today_str, "ranks": cur_ranks},
        "stagePts": {k: {"correct": v[0], "exact": v[1]} for k, v in STAGE_PTS.items()},
        "topScorers": top_scorers,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Wrote {OUT}: {len(standings)} players, {len(results)} results, "
          f"{len(probs)} probs kept, generated={generated}")

if __name__ == "__main__":
    main()
