# 🏆 Family World Cup 2026 — Knockout Upgrades Plan

*Designed 2026-06-25 · Marco (organiser)*

---

## Context: current system baseline

| Stage | Matches | Correct result | Exact score |
|---|---|---|---|
| Group Stage | 72 | 3 pts | 8 pts |
| All knockout rounds | 32 | 3 pts | 8 pts (same — no escalation yet) |

Pre-tournament podium: Champion 50 · Runner-up 35 · 3rd place 20 · 4th place 10 (max 115 pts)

The three upgrades below build excitement through the knockout rounds, add a new Golden Boot mini-game, and give the bracket a connected visual tree.

---

## Upgrade 1 · Escalating Knockout Match Points

### The idea
The closer a match is to the Final, the more it's worth to predict correctly. This creates genuine tension in the final two weeks — a last-minute guess can change the whole leaderboard.

### Proposed point table

| Round | Matches | Correct result | Exact score |
|---|---|---|---|
| Group Stage | 72 | **3** | **8** |
| Round of 32 | 16 | **5** | **12** |
| Round of 16 | 8 | **8** | **18** |
| Quarterfinals | 4 | **12** | **25** |
| Semifinals | 2 | **18** | **35** |
| Third Place | 1 | **12** | **25** |
| **Final** | 1 | **25** | **50** |

### Why these numbers
- Each round roughly doubles the "correct result" value, making the jump feel meaningful.
- The exact-score bonus stays proportionally larger than the result bonus (so nailing the score still pays off big — 50 pts for an exact Final is a huge swing).
- Third Place is treated like a Quarterfinal (same prestige, late in tournament).
- The Final alone can swing the leaderboard by 50 pts — anyone in the top 3 stays in play right to the end.

### Maximum possible match points (if a player picks every game correctly/exactly)
| Round | Max exact pts |
|---|---|
| Group (72 games) | 576 |
| R32 (16 games) | 192 |
| R16 (8 games) | 144 |
| QF (4 games) | 100 |
| SF (2 games) | 70 |
| 3rd/Final (2 games) | 75 |
| **Knockout total** | **581** |

The knockout stage becomes worth roughly the same as the entire group stage — so late entrants or unlucky early pickers still have a path back.

### Implementation changes needed

**`regenerate_data.py` — `pts()` function**
Currently: `def pts(ph, pa, ah, aa): ... return 8 or 3 or 0`

Change to a stage-aware version that looks up the match number, identifies its stage from the FIX data, and applies the right multiplier:

```python
STAGE_PTS = {
    "Group Stage":  (3, 8),
    "Round of 32":  (5, 12),
    "Round of 16":  (8, 18),
    "Quarterfinal": (12, 25),
    "Semifinal":    (18, 35),
    "Third Place":  (12, 25),
    "Final":        (25, 50),
}

def pts(ph, pa, ah, aa, stage="Group Stage"):
    if None in (ph, pa, ah, aa): return None
    correct_pts, exact_pts = STAGE_PTS.get(stage, (3, 8))
    if ph == ah and pa == aa: return exact_pts
    sign = lambda x, y: (x > y) - (x < y)
    return correct_pts if sign(ph, pa) == sign(ah, aa) else 0
```

The match-stage lookup uses the existing match list (`matches` in `data.json`), keying on match number `n`.

**`data.json`** — no schema changes needed; points per pick (`pts` field) simply update with the new values.

**`index.html`** — the scoring legend / info box needs updating to show the escalating table. The `pts()` calculation in the front-end JS (used for "sealed until kickoff" display) also needs the same stage-aware logic.

**Tie-breaker order** stays unchanged: most exact scores → most correct outcomes → correct champion → shared victory.

---

## Upgrade 2 · Golden Boot / Top Scorer Picks

### The idea
Before the knockouts lock (same deadline as Podium picks: **Thu Jul 9, first QF kickoff**), each player names their **top 3 scorers** for the tournament. Points are awarded at the end of the tournament based on the official FIFA Golden Boot standings.

### Pick format
Each player submits an **ordered list of 3 player names**:
1. Pick #1 — who they think wins the Golden Boot
2. Pick #2 — second highest scorer
3. Pick #3 — third highest scorer

(Unordered variant also possible — see options below)

### Scoring — Option A: Ordered (recommended)

| Your pick | Finishes as... | Points |
|---|---|---|
| Pick #1 (Golden Boot) | Actual Golden Boot winner | **40 pts** |
| Pick #1 (Golden Boot) | Top-3 scorer (not #1) | 10 pts |
| Pick #2 or #3 | Actual Golden Boot winner | 20 pts |
| Pick #2 or #3 | Top-3 scorer | 10 pts |
| Any pick | Not a top-3 scorer | 0 pts |

**Maximum: 60 pts** (40 + 10 + 10 for three top-3 scorers, with pick #1 being the correct Golden Boot winner)

### Scoring — Option B: Unordered (simpler)
Pick any 3 players. If they finish in the official top 5 scorers: 15 pts each (max 45 pts). If one of your 3 is the actual Golden Boot winner: +10 bonus (max 55 pts).

### Tie-breaking rule for Golden Boot standings
FIFA's official standings use goals scored, then assists, then minutes played. We use the same order. If two players tie in all three, both count as the same rank (both qualify for "top 3" if they're in the top 3 band).

### Lock deadline
**Thu Jul 9 at first QF kickoff (4:00 PM ET)** — same as Podium picks. Players who haven't submitted get 0 pts for this category.

### Implementation changes needed

**`picks.json`** — new field per player: `"golden_boot": ["Player A", "Player B", "Player C"]`
Submitted via the same Google Sheet mechanism as Podium picks.

**`regenerate_data.py`** — read `golden_boot` picks from `picks.json`, add a `goldenBoot` field to each player's standings object. Add `gbPts` to the standings output (0 until tournament ends, then scored manually by Marco after FIFA confirms top scorers).

**`data.json`** — new field: `"topScorers": [{"name": "Player", "goals": 7, "assists": 2}, ...]` (populated manually by Marco after the Final).

**`index.html`** — new "Golden Boot" section in the leaderboard sidebar and a picks-reveal card (same sealed-until-kickoff mechanic as match picks).

**Spreadsheet** — new tab "Golden Boot Picks" with columns: Player | Pick 1 | Pick 2 | Pick 3 | GB Pts

### Group chat messaging
Announce it as a new mini-game when knockouts begin (Jun 28). Give the family until Jul 9 to submit picks. Reveal everyone's picks publicly on Jul 9 at QF lockout.

---

## Upgrade 3 · Connected Knockout Bracket Tree

### The idea
Replace the current stacked match cards with a proper left-to-right bracket tree: R32 → R16 → QF → SF → Final, with SVG connector lines showing which match feeds which. Teams advance visually as results come in.

### Visual design

```
R32 (×16)     R16 (×8)     QF (×4)      SF (×2)      FINAL
┌──────┐
│ M73  ├──┐
└──────┘  ├──┐
┌──────┐  │  │
│ M74  ├──┘  ├──┐
└──────┘     │  │
             │  ├──┐
┌──────┐     │  │  │
│ M75  ├──┐  │  │  │
└──────┘  ├──┘  │  ├──┐
┌──────┐  │     │  │  │
│ M76  ├──┘     └──┘  │       ┌──────┐
└──────┘              │       │      │
                      │       │FINAL │
                      ├──────►│      │
                      │       └──────┘
                      │
     ... (mirror bracket for the other half)
```

Each match card shows:
- Teams (with flag emoji or country code)
- Score if played, "vs" if upcoming
- Date + time (ET)
- Family predictions (revealed after kickoff, blurred before)
- Points scored per player on that match (small badges)

### Layout approach
**Mobile-first horizontal scroll** — the bracket is wide; on desktop it spans the full width, on mobile the user swipes right. Each column (round) is a fixed-width flex column.

**SVG connector lines** — drawn between match cards using absolutely-positioned `<svg>` overlays. Lines animate (dash-draw) when a match result is entered. Winner's line glows in gold.

### Colour coding
- Upcoming match: default card (dark background)
- Match played, result known: winner side highlighted in gold
- Your prediction correct: green tick badge on the card
- Your prediction exact: gold star badge

### Implementation approach

**Data structure** — the bracket tree is deterministic from the match list. Matches 73–88 are R32, 89–96 R16, 97–100 QF, 101–102 SF, 103 3rd Place, 104 Final. The feed relationships (which R32 pair feeds which R16 match) follow the fixed FIFA 2026 bracket seeding and are hardcoded as a `BRACKET_TREE` constant.

**HTML/JS** — a `renderBracket()` function builds the DOM from `data.json` matches and then draws SVG lines between card elements using their `getBoundingClientRect()` positions. Lines are re-drawn on window resize.

**Predicted team names** — for knockouts, picks are currently stored as scores (e.g., "2-1"), not team names. The bracket needs to show who the player thinks wins each match. This requires either: (a) inferring winner from the predicted score, or (b) adding a separate "predicted winner" field per knockout pick. Option (a) is simpler.

**Third-place branch** — shown as a separate small branch below the main tree, fed by the two SF losers.

### Current bracket CSS classes to migrate/extend
- `.kofinal` — the Final card (already has premium gold styling)
- `.bracketGrid` / `#bracketGrid` — the container (currently renders stacked cards, to be replaced with the tree layout)

---

## Summary: what needs to change

| File | Change |
|---|---|
| `regenerate_data.py` | Stage-aware `pts()` function; read `golden_boot` from picks.json; emit `gbPts` + `goldenBoot` fields |
| `update_scores.py` | No change needed (only handles group stage auto-scoring) |
| `picks.json` | New `"golden_boot"` field per player (added via Google Sheet / fetch_picks) |
| `data.json` | New `topScorers` field (populated by Marco at end of tournament); `gbPts` per player |
| `index.html` | (1) Stage-aware scoring display + legend update; (2) Golden Boot picks section; (3) Full bracket tree rewrite of `#bracketGrid` |
| `google-apps-script.gs` | Add Golden Boot pick row/column to the submission sheet |
| `FamilyWorldCup2026.xlsx` | New "Golden Boot Picks" tab |

---

## Suggested rollout order

1. **Now (Jun 25–27):** Announce the new knockout scoring multipliers to the family via group chat. Lock it in as official rules.
2. **Jun 28 (R32 starts):** Deploy the updated `pts()` function. Confirm first R32 match scores correctly with escalated points.
3. **Jun 28–Jul 8:** Golden Boot picks open. Family submits via Google Sheet. Collect picks.
4. **Jul 9 (QF kickoff):** Podium + Golden Boot picks lock. Reveal everyone's Golden Boot picks in group chat.
5. **Jul 9+ (anytime):** Deploy the connected bracket tree in `index.html`.
6. **Jul 19 (after Final):** Marco manually scores Golden Boot picks based on FIFA official top scorers. `regenerate_data.py` run with final `topScorers` data.

---

*All point values are proposals — adjust before announcing to the family.*
