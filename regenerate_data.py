#!/usr/bin/env python3
"""Regenerate data.json for the Family World Cup portal from FamilyWorldCup2026.xlsx.

data.json is the LIVE data source the portal fetches on load. After any change to
the spreadsheet (results or picks), run:  python3 regenerate_data.py
Then publish (commit/push or upload data.json). The portal picks it up automatically.
"""
import openpyxl, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "FamilyWorldCup2026.xlsx")
OUT  = os.path.join(HERE, "data.json")

# Player -> (Pred-Home col, Pred-Away col) in the Match Predictions sheet
PCOLS = [("Ewan","I","J"),("Nana","L","M"),("Emrys","O","P"),("Nonno","R","S"),
         ("Nonna","U","V"),("Boompa","X","Y"),("Xavier","AA","AB"),
         ("Autumn","AD","AE"),("River","AG","AH")]
CHAMPS = {"Ewan":"Spain","Nana":"France","Nonno":"Brazil","Boompa":"France"}
PHOTOS = {"Nonno":"nonno-bobblehead.jpg","Emrys":"emrys-bobblehead.jpg",
          "Nana":"nana-bobblehead.jpg","Nonna":"nonna-bobblehead.jpg"}

def pts(ph, pa, ah, aa):
    if None in (ph, pa, ah, aa): return None
    if ph == ah and pa == aa: return 8
    sign = lambda x, y: (x > y) - (x < y)
    return 3 if sign(ph, pa) == sign(ah, aa) else 0

def main():
    wb = openpyxl.load_workbook(XLSX)
    ws = wb["Match Predictions"]
    results = {}
    generated = None
    for r in range(4, 108):
        g, h = ws["G"+str(r)].value, ws["H"+str(r)].value
        if g is not None and h is not None:
            results[r-3] = [g, h]
        elif generated is None:
            d = ws["B"+str(r)].value          # first unplayed match's date = next slate
            generated = d.strftime("%Y-%m-%d") if d else None
    mres = {r-3: (ws["G"+str(r)].value, ws["H"+str(r)].value) for r in range(4, 108)}

    standings = []
    for name, hc, ac in PCOLS:
        picks, mp, ex, cor = [], 0, 0, 0
        for r in range(4, 108):
            ph, pa = ws[hc+str(r)].value, ws[ac+str(r)].value
            if ph is None and pa is None: continue
            n = r-3; ah, aa = mres[n]; p = pts(ph, pa, ah, aa)
            picks.append({"n": n, "ph": ph, "pa": pa, "pts": p})
            if p is not None:
                mp += p
                if p == 8: ex += 1
                if p > 0: cor += 1
        standings.append({"name": name, "matchPts": mp, "exact": ex, "correct": cor,
                          "champ": CHAMPS.get(name), "photo": PHOTOS.get(name), "picks": picks})

    # Preserve win/draw/win probabilities written by fetch_odds.py (don't wipe them)
    probs = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                probs = json.load(f).get("probs", {}) or {}
        except Exception:
            probs = {}

    data = {"generated": generated, "standings": standings,
            "results": results, "photos": PHOTOS, "probs": probs}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Wrote {OUT}: {len(standings)} players, {len(results)} results, "
          f"{len(probs)} probs kept, generated={generated}")

if __name__ == "__main__":
    main()
