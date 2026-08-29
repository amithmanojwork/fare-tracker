"""Render data/history.csv into docs/index.html, a static fare board.

Run straight after tracker.py. GitHub Pages serves the docs/ folder, so the
board is a URL you can keep open on your phone.
"""

import csv
import html
import json
import os
from collections import defaultdict
from datetime import date, datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
HISTORY_PATH = os.path.join(ROOT, "data", "history.csv")
OUTPUT_PATH = os.path.join(ROOT, "docs", "index.html")

MAX_POINTS = 40


def read_rows():
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH, newline="", encoding="utf-8") as handle:
        rows = []
        for row in csv.DictReader(handle):
            try:
                row["price"] = float(row["price"])
            except (TypeError, ValueError):
                continue
            rows.append(row)
        return rows


def sparkline(prices, target):
    """Inline SVG trend strip with a dashed line marking the target price."""
    if len(prices) < 2:
        return '<div class="spark spark--empty">not enough readings yet</div>'

    width, height, pad = 300, 44, 4
    low = min(min(prices), target)
    high = max(max(prices), target)
    span = (high - low) or 1
    step = width / (len(prices) - 1)

    def y_for(value):
        return round(height - pad - ((value - low) / span) * (height - 2 * pad), 1)

    points = " ".join(
        f"{round(index * step, 1)},{y_for(value)}" for index, value in enumerate(prices)
    )
    target_y = y_for(target)
    last_x = round((len(prices) - 1) * step, 1)
    last_y = y_for(prices[-1])
    tone = "good" if prices[-1] <= target else "watch"
    fill_points = f"0,{height} {points} {last_x},{height}"

    return (
        f'<svg class="spark" viewBox="0 0 {width} {height}" '
        f'preserveAspectRatio="none" role="img" '
        f'aria-label="Price trend over the last {len(prices)} checks">'
        f'<polygon points="{fill_points}" class="spark-fill" />'
        f'<line x1="0" y1="{target_y}" x2="{width}" y2="{target_y}" '
        f'class="spark-target" />'
        f'<polyline points="{points}" class="spark-line" />'
        f'<circle cx="{last_x}" cy="{last_y}" r="4" class="dot dot--{tone}" />'
        f"</svg>"
    )


def build_card(route, rows, currency):
    history = sorted(rows, key=lambda item: item["checked_at"])[-MAX_POINTS:]
    prices = [row["price"] for row in history]
    target = route["target_price"]

    if not history:
        return (
            f'<article class="route route--empty">'
            f'<header class="route-head"><h2>{html.escape(route["label"])}</h2></header>'
            f'<p class="note">No readings yet. The first run fills this in.</p>'
            f"</article>"
        )

    best_row = min(rows, key=lambda item: item["price"])
    latest = history[-1]
    delta = latest["price"] - prices[-2] if len(prices) > 1 else 0

    if best_row["price"] <= target:
        state_label, tone = "Good Price", "good"
    elif best_row["price"] <= target * 1.15:
        state_label, tone = "Almost There", "watch"
    else:
        state_label, tone = "Too Expensive", "high"

    latest_price = f"{currency} {round(latest['price']):,}"
    if delta < 0:
        move = (
            f'<span class="move move--down">latest {latest_price} '
            f"&#9660;{abs(round(delta)):,}</span>"
        )
    elif delta > 0:
        move = (
            f'<span class="move move--up">latest {latest_price} '
            f"&#9650;{round(delta):,}</span>"
        )
    else:
        move = f'<span class="move move--flat">latest {latest_price}, flat</span>'

    return f"""<article class="route">
  <header class="route-head">
    <h2>{html.escape(route["label"])}</h2>
    <span class="flag flag--{tone}">{state_label}</span>
  </header>
  <p class="note">{html.escape(route.get("note", ""))}</p>
  <div class="figure">
    <span class="currency">{currency}</span>
    <span class="price">{round(best_row["price"]):,}</span>
    {move}
  </div>
  <dl class="facts">
    <div><dt>Cheapest date</dt><dd>{html.escape(best_row["outbound_date"])}</dd></div>
    <div><dt>Carrier</dt><dd>{html.escape(best_row["airlines"] or "—")}</dd></div>
    <div><dt>Stops</dt><dd>{html.escape(str(best_row["stops"]))}</dd></div>
    <div><dt>Your target</dt><dd>{currency} {target:,}</dd></div>
  </dl>
  {sparkline(prices, target)}
  <p class="meta">{len(rows)} readings &middot; last checked {html.escape(latest["checked_at"][:10])}</p>
</article>"""


STYLES = """
:root {
  --bg: #eef1f8;
  --card: #ffffff;
  --card-border: #eef0f6;
  --ink: #14161f;
  --dim: #767b8c;
  --faint: #a3a8b8;
  --blue: #3467f0;
  --blue-soft: #eaf0fe;
  --good: #1fa971;
  --good-soft: #e4f7ee;
  --watch: #d99a1b;
  --watch-soft: #fdf3de;
  --high: #e1503c;
  --high-soft: #fdeae7;
  --shadow: 0 16px 34px -18px rgba(20, 30, 70, 0.28);
  --radius: 22px;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 0 0 64px;
  background: var(--bg);
  color: var(--ink);
  font-family: "Google Sans Flex", "Google Sans", system-ui, -apple-system, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}
.topbar {
  height: 96px;
  background: radial-gradient(120% 220% at 20% -40%, #3a4fb0 0%, #0e1442 60%, #060814 100%);
  position: relative;
  overflow: hidden;
}
.topbar::after {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(1.5px 1.5px at 10% 30%, rgba(255,255,255,.55) 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 35% 60%, rgba(255,255,255,.4) 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 60% 20%, rgba(255,255,255,.5) 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 80% 50%, rgba(255,255,255,.35) 50%, transparent 51%),
    radial-gradient(1.5px 1.5px at 92% 75%, rgba(255,255,255,.5) 50%, transparent 51%);
}
.wrap {
  max-width: 900px;
  margin: -56px auto 0;
  padding: 0 20px;
  position: relative;
}
.masthead {
  background: var(--card);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 26px 28px;
  margin-bottom: 20px;
}
.masthead h1 {
  font-family: "Google Sans Flex", "Google Sans", system-ui, sans-serif;
  font-weight: 700;
  font-size: 34px;
  line-height: 1.1;
  margin: 0;
  color: var(--ink);
}
.masthead p { margin: 8px 0 0; color: var(--dim); font-size: 13.5px; }
.countdown {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--blue-soft);
  color: var(--blue);
  font-weight: 600;
  font-size: 12.5px;
}
.board {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 18px;
}
.route {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 24px 24px 22px;
}
.route--empty { display: flex; flex-direction: column; justify-content: center; min-height: 160px; }
.route-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.route h2 {
  font-family: "Google Sans Flex", "Google Sans", system-ui, sans-serif;
  font-weight: 700;
  font-size: 21px;
  line-height: 1.25;
  margin: 0;
  color: var(--ink);
}
.flag {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  padding: 5px 11px;
  border-radius: 999px;
  white-space: nowrap;
}
.flag--good { color: var(--good); background: var(--good-soft); }
.flag--watch { color: var(--watch); background: var(--watch-soft); }
.flag--high { color: var(--high); background: var(--high-soft); }
.note { color: var(--dim); font-size: 13px; margin: 8px 0 0; }
.figure { display: flex; align-items: baseline; gap: 8px; margin: 18px 0 14px; flex-wrap: wrap; }
.figure .move { flex-basis: 100%; }
.currency { font-size: 14px; font-weight: 600; color: var(--faint); }
.price {
  font-weight: 800;
  font-size: 40px;
  line-height: 1;
  letter-spacing: -0.01em;
  font-variant-numeric: tabular-nums;
  color: var(--ink);
}
.move { font-size: 12.5px; font-weight: 600; }
.move--down { color: var(--good); }
.move--up { color: var(--high); }
.move--flat { color: var(--dim); }
.facts { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 0 0 18px; }
.facts div {
  background: #f7f8fc;
  border-radius: 12px;
  padding: 9px 12px;
}
.facts dt {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--faint);
}
.facts dd { margin: 3px 0 0; font-size: 14px; font-weight: 600; font-variant-numeric: tabular-nums; }
.spark { width: 100%; height: 52px; display: block; }
.spark--empty { color: var(--dim); font-size: 12px; height: auto; }
.spark-fill { fill: var(--blue-soft); stroke: none; }
.spark-line { fill: none; stroke: var(--blue); stroke-width: 2.25; stroke-linecap: round; vector-effect: non-scaling-stroke; }
.spark-target { stroke: var(--watch); stroke-width: 1.25; stroke-dasharray: 3 4; vector-effect: non-scaling-stroke; }
.dot--good { fill: var(--good); }
.dot--watch { fill: var(--watch); }
.meta {
  font-size: 11.5px;
  color: var(--faint);
  margin: 12px 0 0;
}
footer {
  color: var(--dim);
  font-size: 12px;
  margin-top: 6px;
  padding: 20px 4px 0;
}
@media (max-width: 380px) { .facts { grid-template-columns: 1fr; } .price { font-size: 34px; } }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
"""


def main():
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        config = json.load(handle)

    rows = read_rows()
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["route_id"]].append(row)

    cards = "\n".join(
        build_card(route, grouped.get(route["id"], []), config["currency"])
        for route in config["routes"]
    )

    days_left = (date.fromisoformat(config["window_start"]) - date.today()).days
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fare board &middot; Bengaluru to Milan</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Google+Sans+Flex:wght@100..900&display=swap" rel="stylesheet">
<style>{STYLES}</style>
</head>
<body>
<div class="topbar"></div>
<div class="wrap">
  <header class="masthead">
    <h1>Bengaluru &rarr; Milan</h1>
    <p>Business class hunt &middot; travel window {config["window_start"]} to {config["window_end"]}
       &middot; <span class="countdown">{days_left} days out</span></p>
  </header>
  <div class="board">
  {cards}
  </div>
  <footer>
    Built {stamp}. Prices in {config["currency"]}, cheapest seen per route.
    Dashed line marks your target. Always reconfirm on the airline's own site before booking.
  </footer>
</div>
</body>
</html>
"""

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as handle:
        handle.write(document)
    print(f"Wrote {OUTPUT_PATH} from {len(rows)} readings.")


if __name__ == "__main__":
    main()
