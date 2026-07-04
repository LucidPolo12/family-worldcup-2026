#!/usr/bin/env python3
"""Family World Cup 2026 — post-update sanity check.

Run this after entering any knockout result (and pushing) to confirm the whole
app will progress correctly, so you don't have to eyeball each section.

  python3 verify_app.py

It is READ-ONLY (never writes data.json or the xlsx). It mirrors the app's own
bracket + scoring logic and reports PASS / WARN / FAIL for the things that have
bitten us before: penalty advancing side, bracket resolution, list pruning,
data.json freshness, and picks.json integrity.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
def load(name):
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)

problems, warnings, notes = [], [], []

# ---- load data (bad JSON is itself a failure) --------------------------------
try: results = {int(k): v for k, v in load("results.json").items()}
except Exception as e: print("FAIL: results.json is not valid JSON:", e); sys.exit(1)
try: picks = load("picks.json")
except Exception as e: print("FAIL: picks.json is not valid JSON (would wipe all family picks):", e); sys.exit(1)
try: data = load("data.json")
except Exception as e: data = {}; warnings.append("data.json missing/invalid (the Action rebuilds it on push)")

# picks.json completeness
EXPECT_PLAYERS = {"Ewan","Nana","Emrys","Nonno","Nonna","Boompa","Xavier","Autumn","River"}
missing_players = EXPECT_PLAYERS - set(picks.keys())
if missing_players: problems.append("picks.json missing players: " + ", ".join(sorted(missing_players)))

# ---- fixtures (teams + feeders) ---------------------------------------------
# R32 home/away come from the xlsx-independent fixture list embedded here so the
# check stands alone. Teams that reach R32 (matches 73-88):
R32 = {
 73:("South Africa","Canada"),74:("Germany","Paraguay"),75:("Netherlands","Morocco"),
 76:("Brazil","Japan"),77:("France","Sweden"),78:("Ivory Coast","Norway"),
 79:("Mexico","Ecuador"),80:("England","DR Congo"),81:("USA","Bosnia and Herzegovina"),
 82:("Belgium","Senegal"),83:("Portugal","Croatia"),84:("Spain","Austria"),
 85:("Switzerland","Algeria"),86:("Argentina","Cape Verde"),87:("Colombia","Ghana"),
 88:("Australia","Egypt"),
}
FEED = {89:('W74','W77'),90:('W73','W75'),91:('W76','W78'),92:('W79','W80'),
        93:('W83','W84'),94:('W81','W82'),95:('W86','W88'),96:('W85','W87'),
        97:('W89','W90'),98:('W93','W94'),99:('W91','W92'),100:('W95','W96'),
        101:('W97','W98'),102:('W99','W100'),103:('L101','L102'),104:('W101','W102')}
STAGE_NAME = {**{n:"Round of 32" for n in range(73,89)},
              **{n:"Round of 16" for n in range(89,97)},
              **{n:"Quarterfinal" for n in range(97,101)},
              101:"Semifinal",102:"Semifinal",103:"Third Place",104:"Final"}

def advancing(n):
    """Side that advanced: 'H'/'A' or None if unknown."""
    r = results.get(n)
    if not r: return None
    if r[0] > r[1]: return 'H'
    if r[1] > r[0]: return 'A'
    return r[2] if len(r) > 2 and r[2] in ('H','A') else None

_teams, _outcome = {}, {}
def teams(n):
    if n in _teams: return _teams[n]
    if n in R32: res = {'h':R32[n][0], 'a':R32[n][1]}
    else:
        f = FEED[n]
        res = {'h':feed_side(f[0]), 'a':feed_side(f[1])}
    _teams[n] = res; return res
def feed_side(tok):
    win, n = tok[0]=='W', int(tok[1:])
    oc = outcome(n)
    return (oc['winner'] if win else oc['loser'])
def outcome(n):
    if n in _outcome: return _outcome[n]
    _outcome[n] = {'winner':None,'loser':None}
    t, r = teams(n), results.get(n)
    out = {'winner':None,'loser':None}
    if t['h'] and t['a'] and r:
        side = advancing(n)
        if side == 'H': out = {'winner':t['h'],'loser':t['a']}
        elif side == 'A': out = {'winner':t['a'],'loser':t['h']}
    _outcome[n] = out; return out

# ---- CHECK 1: every completed KO game has a determinable advancing side ------
for n in range(73, 105):
    r = results.get(n)
    if not r: continue
    if advancing(n) is None:
        problems.append(f"Match {n} ({STAGE_NAME[n]}) is a draw {r[0]}-{r[1]} with NO advancing side recorded "
                        f"-> set the 'Advancing (H/A)' cell in the spreadsheet. Pick-Off & bracket will be wrong until then.")

# ---- CHECK 2: bracket resolves wherever both feeders are decided -------------
for n in range(89, 105):
    t = teams(n)
    both_feeders_decided = all(results.get(int(tok[1:])) is not None for tok in FEED[n])
    if both_feeders_decided and (not t['h'] or not t['a']):
        problems.append(f"Match {n} ({STAGE_NAME[n]}) can't resolve its teams even though both feeders are played "
                        f"-> likely a missing advancing side upstream.")

# ---- CHECK 3: data.json freshness (has the Action run since last result?) ----
if data:
    dres = {int(k):v for k,v in (data.get("results") or {}).items()}
    stale = [n for n in results if n not in dres]
    if stale:
        warnings.append("data.json is behind results.json for match(es) " + ",".join(map(str,sorted(stale))) +
                        " -> commit/push so the Action regenerates it (or it's mid-deploy).")
    dadv = data.get("advancing") or {}
    for n in range(73,105):
        if advancing(n) and str(n) not in dadv and n in dres:
            warnings.append(f"data.json has match {n} but no advancing side -> Egypt-style Pick-Off bug; needs regenerate.")

# ---- Report resolved bracket + list sizes (informational) -------------------
def show(n):
    t = teams(n); h = t['h'] or ('?'+FEED.get(n,('?','?'))[0]); a = t['a'] or ('?'+FEED.get(n,('?','?'))[1])
    r = results.get(n); sc = f"  [{r[0]}-{r[1]}]" if r else ""
    return f"  M{n} {STAGE_NAME[n]:12} {h} vs {a}{sc}"
print("="*64); print("RESOLVED BRACKET (as the app will show it)"); print("="*64)
for rng,label in [(range(89,97),"Round of 16"),(range(97,101),"Quarterfinals"),
                  (range(101,103),"Semifinals"),(range(103,105),"3rd / Final")]:
    print(f"-- {label} --")
    for n in rng: print(show(n))

# remaining teams (Champion/Podium eligibility)
all_group = set()
for h,a in R32.values(): all_group.add(h); all_group.add(a)
elim = set()
for n in range(73,105):
    lo = outcome(n)['loser']
    if lo: elim.add(lo)
remaining = sorted(all_group - elim)
notes.append(f"Champion/Podium eligible teams (still alive among R32 sides): {len(remaining)} -> {', '.join(remaining)}")

print("\n"+"="*64); print("RESULT"); print("="*64)
for p in problems: print("FAIL:", p)
for w in warnings: print("WARN:", w)
for nline in notes: print("note:", nline)
if not problems and not warnings: print("PASS: everything consistent — safe to deploy/post.")
elif not problems: print("\nOK with warnings (usually just 'push to rebuild data.json').")
else: print("\nACTION NEEDED — fix the FAIL lines above before posting the leaderboard.")
sys.exit(1 if problems else 0)
