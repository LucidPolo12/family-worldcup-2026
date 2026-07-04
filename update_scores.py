#!/usr/bin/env python3
"""Auto-record finished results into results.json using The Odds API /scores endpoint.

Covers the GROUP STAGE **and** the KNOCKOUT rounds, so scores flow in without any
manual entry. Knockout pairings are resolved from the bracket (feeders + results
already recorded), so a round becomes matchable as soon as the previous round is in.

Why results.json (not the spreadsheet): the .xlsx is a binary file you edit by hand,
so having the automation write it too would cause Git merge conflicts. Instead the
Action writes a small text file, results.json, which merges cleanly. regenerate_data.py
combines results.json with any scores you typed into the spreadsheet's G/H columns.

Scoring basis: the app scores knockout games on the final score after all playing time
(90 min or extra time); penalty KICKS are not added to the score. The Odds API final
score matches that. For a game that ends LEVEL (a shootout), only the score is recorded
here — the API can't say who won the shootout, so the "Advancing (H/A)" side must be set
by hand in the spreadsheet (verify_app.py flags any that are missing). Decisive knockout
games (incl. those decided in extra time) need nothing extra — the higher score wins.

Safety rules:
- Never changes a result already known (idempotent).
- Only records a knockout game once BOTH its teams are known from the bracket.

Key: env ODDS_API_KEY (GitHub Actions secret) or local odds_key.txt.
CI order:  update_scores.py -> regenerate_data.py -> fetch_odds.py -> commit/push.
"""
import json, os, re, urllib.request, unicodedata, openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.join(HERE, "FamilyWorldCup2026.xlsx")
WCP  = os.path.join(HERE, "WorldCupPicks.html")
RES  = os.path.join(HERE, "results.json")
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

# Bracket feeder map (which two matches feed each knockout slot) — same as the site.
FEED = {89:('W74','W77'),90:('W73','W75'),91:('W76','W78'),92:('W79','W80'),
        93:('W83','W84'),94:('W81','W82'),95:('W86','W88'),96:('W85','W87'),
        97:('W89','W90'),98:('W93','W94'),99:('W91','W92'),100:('W95','W96'),
        101:('W97','W98'),102:('W99','W100'),103:('L101','L102'),104:('W101','W102')}

def match_index(store):
    """(home, away) -> match number, for every match whose teams are known:
    group stage + Round of 32 straight from the fixtures, later rounds resolved
    from the bracket using results recorded so far."""
    fix = json.loads(re.search(r"const FIX = (\[.*?\]);", open(WCP, encoding="utf-8").read(), re.S).group(1))
    idx = {}
    for f in fix:
        st = f.get("stage", "")
        if (st.startswith("Group") or st == "Round of 32") and "TBD" not in (f["h"], f["a"]):
            idx[(f["h"], f["a"])] = f["n"]

    results = {int(k): v for k, v in store.items()}
    r32 = {f["n"]: (f["h"], f["a"]) for f in fix if f.get("stage") == "Round of 32"}
    tcache, ocache = {}, {}
    def adv(n):
        r = results.get(n)
        if not r: return None
        if r[0] > r[1]: return 'H'
        if r[1] > r[0]: return 'A'
        return r[2] if len(r) > 2 and r[2] in ('H', 'A') else None
    def teams(n):
        if n in tcache: return tcache[n]
        res = r32.get(n) if n in r32 else (feed(FEED[n][0]), feed(FEED[n][1]))
        tcache[n] = res; return res
    def feed(tok):
        w, l = outcome(int(tok[1:]))
        return w if tok[0] == 'W' else l
    def outcome(n):
        if n in ocache: return ocache[n]
        ocache[n] = (None, None)
        t, r, o = teams(n), results.get(n), (None, None)
        if t and t[0] and t[1] and r:
            s = adv(n)
            if s == 'H': o = (t[0], t[1])
            elif s == 'A': o = (t[1], t[0])
        ocache[n] = o; return o
    for n in range(89, 105):
        t = teams(n)
        if t and t[0] and t[1]:
            idx[(t[0], t[1])] = n
    return idx

# ---- ESPN shootout resolution -----------------------------------------------
# The Odds API can't say who won a penalty shootout, so for a knockout game that
# ends LEVEL we ask ESPN's free scoreboard which side went through (each competitor
# carries winner:true, and shootoutScore for the shootout tally). This fills the
# advancing side automatically — the last piece that used to be manual.
ESPN_ROOT = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
ESPN_ALIAS = {"United States":"USA","Korea Republic":"South Korea","Turkey":"Türkiye",
    "Czech Republic":"Czechia","Côte d'Ivoire":"Ivory Coast","IR Iran":"Iran",
    "Bosnia & Herzegovina":"Bosnia and Herzegovina","Cabo Verde":"Cape Verde","Congo DR":"DR Congo"}
def _strip(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()
_ALIAS_C = {_strip(k): _strip(v) for k, v in ESPN_ALIAS.items()}
def _canon(s):
    st = _strip(s); return _ALIAS_C.get(st, st)

def _espn_winner_side(H, A, home_canon):
    """Return 'H'/'A' for the side ESPN says advanced, mapped to OUR home/away."""
    win = None
    for c in (H, A):
        if c.get("winner") is True: win = c
    if win is None:
        try:
            hs, as_ = int(H.get("shootoutScore")), int(A.get("shootoutScore"))
            win = H if hs > as_ else (A if as_ > hs else None)
        except (TypeError, ValueError):
            win = None
    if win is None: return None
    return 'H' if _canon(win["team"]["displayName"]) == home_canon else 'A'

def resolve_shootouts(store, idx):
    """For LEVEL knockout games with no advancing side yet, set it from ESPN."""
    need = [n for n in range(73, 105)
            if str(n) in store and len(store[str(n)]) == 2 and store[str(n)][0] == store[str(n)][1]]
    if not need:
        return []
    fix = json.loads(re.search(r"const FIX = (\[.*?\]);", open(WCP, encoding="utf-8").read(), re.S).group(1))
    n2date = {f["n"]: f.get("date") for f in fix}
    n2pair = {v: k for k, v in idx.items()}          # match number -> (home, away)
    dates = sorted({n2date.get(n) for n in need if n2date.get(n)})
    applied = []
    for d in dates:
        try:
            payload = json.loads(urllib.request.urlopen(ESPN_ROOT + "?dates=" + d.replace("-", ""), timeout=30).read())
        except Exception:
            continue
        for ev in payload.get("events", []):
            try:
                cs = ev["competitions"][0]["competitors"]
                H = next(c for c in cs if c.get("homeAway") == "home")
                A = next(c for c in cs if c.get("homeAway") == "away")
                names = {_canon(H["team"]["displayName"]), _canon(A["team"]["displayName"])}
            except Exception:
                continue
            for n in need:
                if str(n) not in store or len(store[str(n)]) != 2:
                    continue
                pr = n2pair.get(n)
                if not pr or names != {_canon(pr[0]), _canon(pr[1])}:
                    continue
                side = _espn_winner_side(H, A, _canon(pr[0]))
                if side:
                    store[str(n)] = [store[str(n)][0], store[str(n)][1], side]
                    applied.append(f"M{n}: {pr[0] if side=='H' else pr[1]} advanced on penalties")
    return applied

def main():
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

    idx = match_index(store)   # group + resolved-knockout pairings

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
        known.add(n)   # so a later-round slot can resolve within this same run
        note = " (LEVEL — set Advancing (H/A) by hand)" if (hs == as_ and n >= 73) else ""
        wrote.append(f"M{n}: {home} {hs}-{as_} {away}{note}")

    # Fill in penalty-shootout advancing sides from ESPN for any level KO game.
    try:
        pens = resolve_shootouts(store, idx)
    except Exception:
        pens = []

    if wrote or pens:
        json.dump(store, open(RES, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"Auto-recorded {len(wrote)} new result(s):")
    for w in wrote:
        print("  +", w)
    if not wrote:
        print("  (nothing new to score)")
    if pens:
        print(f"Resolved {len(pens)} shootout advancing side(s) via ESPN:")
        for p in pens:
            print("  +", p)

if __name__ == "__main__":
    main()
