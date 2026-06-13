#!/usr/bin/env python3
"""Ingest family-submitted picks from the published Google Sheet (CSV) into picks.json.

picks.json shape: { "Ewan": {"5":[0,2], "6":[3,1]}, "Nana": {...}, ... }
regenerate_data.py overlays these on top of any picks already in the spreadsheet.

Rules:
- Keep the LATEST submission per (name, match) by timestamp.
- IGNORE any pick whose submission timestamp is at/after that match's kickoff
  (server-side lock — a late edit can't change a pick once the game has started).

The published-CSV URL comes from env PICKS_CSV_URL (a GitHub Actions secret/variable)
or a local file picks_csv.txt. If neither is set, the script exits quietly (no-op),
so the pipeline still works before the sheet is wired up.
"""
import json, os, re, csv, io, urllib.request, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "picks.json")

URL = os.environ.get("PICKS_CSV_URL")
cf = os.path.join(HERE, "picks_csv.txt")
if not URL and os.path.exists(cf):
    URL = open(cf, encoding="utf-8").read().strip()
if not URL:
    print("No PICKS_CSV_URL set — skipping picks ingest (nothing to do).")
    raise SystemExit(0)

# Kickoff times (ET) from WorldCupPicks.html, to enforce the lock by timestamp.
def ko_table():
    txt = open(os.path.join(HERE, "WorldCupPicks.html"), encoding="utf-8").read()
    fix = json.loads(re.search(r"const FIX = (\[.*?\]);", txt, re.S).group(1))
    return {f["n"]: (f["date"], f["ko"]) for f in fix}

def ko_instant(date_str, ko):
    m = re.match(r"(\d+):(\d+)\s*(AM|PM)", ko or "", re.I)
    if not m:
        return None
    hh = int(m.group(1)) % 12
    if m.group(3).upper() == "PM":
        hh += 12
    mm = int(m.group(2))
    d = datetime.date.fromisoformat(date_str)
    if hh < 6:                       # 12 AM games belong to the next calendar day
        d += datetime.timedelta(days=1)
    return datetime.datetime(d.year, d.month, d.day, hh, mm,
                             tzinfo=datetime.timezone(datetime.timedelta(hours=-4)))  # EDT

def parse_ts(s):
    s = (s or "").strip()
    for fmt in ("%m/%d/%Y %H:%M:%S", "%m/%d/%Y %H:%M", "%Y-%m-%d %H:%M:%S",
                "%m/%d/%Y, %H:%M:%S"):
        try:
            # Sheet timestamps are in the script's timezone; assume Eastern to compare with kickoffs
            return datetime.datetime.strptime(s, fmt).replace(
                tzinfo=datetime.timezone(datetime.timedelta(hours=-4)))
        except ValueError:
            continue
    return None

def main():
    raw = urllib.request.urlopen(URL, timeout=30).read().decode("utf-8", "replace")
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        print("Empty sheet."); return
    header = [h.strip().lower() for h in rows[0]]
    def col(name):
        return header.index(name) if name in header else None
    ci = {k: col(k) for k in ("timestamp", "name", "match", "predh", "preda")}
    kos = ko_table()

    # latest valid pick per (name, match)
    latest = {}   # (name, n) -> (ts, [h, a])
    for r in rows[1:]:
        try:
            name = r[ci["name"]].strip()
            n = int(float(r[ci["match"]]))
            ph = int(float(r[ci["predh"]])); pa = int(float(r[ci["preda"]]))
        except (ValueError, IndexError, TypeError):
            continue
        ts = parse_ts(r[ci["timestamp"]]) if ci["timestamp"] is not None else None
        # enforce kickoff lock
        if ts and n in kos:
            ki = ko_instant(*kos[n])
            if ki and ts >= ki:
                continue
        latest[(name, n)] = (ts, [ph, pa])   # sheet rows are in append order, so last wins

    picks = {}
    for (name, n), (ts, score) in latest.items():
        picks.setdefault(name, {})[str(n)] = score

    json.dump(picks, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
    total = sum(len(v) for v in picks.values())
    print(f"Ingested {total} picks across {len(picks)} players -> picks.json")

if __name__ == "__main__":
    main()
