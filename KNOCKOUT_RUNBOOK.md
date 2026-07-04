# Knockout Runbook — Family World Cup 2026

The app runs itself. **Scores are fetched automatically** — the GitHub Action pulls
finished results (group stage **and** knockouts) from the Odds API three times a day
and rebuilds everything. You do not enter scores.

## Per game — the whole routine

Nothing, for the vast majority of games. The bot records the score and the whole app
(bracket, Next up, Today, Our Picks, Match Center, Pick Off, standings, Champion/Podium
& Golden Boot lists) updates on its own within a few hours.

### The one exception: a penalty shootout

No score feed can say who won a shootout, so a **knockout game that ends level** is the
only thing that ever needs a human. When it happens:

1. Open **FamilyWorldCup2026.xlsx** → **Match Predictions** sheet, find the match's row
   (row number = match number + 3, e.g. Match 95 is row 98).
2. In the **Advancing (H/A)** column put `H` if the home (left) team won the shootout,
   or `A` if the away (right) team did. (You can leave the score alone — the bot fills it.)
3. Save, commit **FamilyWorldCup2026.xlsx** in GitHub Desktop, and Push.

`verify_app.py` will tell you exactly which match, if any, is waiting on this — so you
never have to go looking. Everything else is automatic.

## What updates automatically from that one score

- **Bracket** — the winner drops into the next round's slot (R16 → QF → SF → Final).
- **Next up, Today's Games, Our Picks, Match Center** — show the real teams as
  soon as the matchup is decided.
- **The Pick Off & standings** — advance points + exact-score bonuses, penalties
  included, for every round through the Final.
- **Champion & Podium dropdowns** — a team drops off the moment it's eliminated.
- **Golden Boot dropdown** — a scorer drops off when his team is knocked out.

## The only optional manual touch

Golden Boot **goal counts**. Eliminations are automatic, but if you want the list
to reflect *new* goals scored (or add a new 2+ goal scorer), edit the `GB_PLAYERS`
list near the bottom of **WorldCupPicks.html**. This is a content refresh, not a
fix — nothing breaks if you skip it.

## 30-second safety check (recommended before you post the leaderboard)

Run this in the project folder:

```
python3 verify_app.py
```

It's read-only and flags exactly the things that have tripped us up:

- a penalty game missing its **Advancing (H/A)** letter (the "Egypt scored 0" bug),
- a bracket slot that can't resolve,
- **data.json** lagging behind the latest results (usually just "push to rebuild"),
- a corrupted **picks.json**.

`PASS` = safe to post. `FAIL` = fix the listed line first.

## Two gotchas to remember

- **Penalty winner is mandatory** for any level knockout game — without the
  `H`/`A` letter, the bracket stalls and shootout-callers score 0.
- If GitHub Desktop ever shows **picks.json** as changed on its own, **discard it**
  (right-click → Discard). It's maintained automatically; a local change to it is
  almost always a corrupted copy that would wipe everyone's picks from scoring.
