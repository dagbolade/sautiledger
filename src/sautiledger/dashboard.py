"""Admin analytics dashboard: the whole fleet on one page — sessions,
outcomes, daily activity, and per-session export links. Read-only,
token-gated in api.py, styled like the app so it feels like the same
product from the operator's side.
"""

from __future__ import annotations

import html
from datetime import datetime


def _pct(part: int, whole: int) -> str:
    return f"{round(100 * part / whole)}%" if whole else "–"


def build_dashboard_html(sessions, outcomes, by_day, modes: dict, token: str) -> str:
    total_utt = sum(r["n"] for r in outcomes)
    logged = next((r["n"] for r in outcomes if r["outcome"] == "logged"), 0)
    clarified = next((r["n"] for r in outcomes if r["outcome"] == "clarify"), 0)
    asr_failed = sum(r["n"] for r in outcomes if r["outcome"].startswith("asr"))
    voice = modes.get("voice", 0)
    sales_total = sum(r["sales_total"] or 0 for r in sessions)
    clips = sum(r["retained_clips"] or 0 for r in sessions)
    generated = datetime.now().strftime("%d %b %Y, %H:%M:%S")

    def tile(label: str, value: str, sub: str = "") -> str:
        return (f'<div class="tile"><div class="k">{label}</div>'
                f'<div class="v">{value}</div>'
                f'<div class="k">{sub}</div></div>')

    tiles = "".join([
        tile("Sessions", str(len(sessions))),
        tile("Transactions", str(sum(r["transactions"] for r in sessions)),
             f"&#8358;{sales_total:,} sales"),
        tile("Utterances", str(total_utt),
             f"{_pct(voice, total_utt)} by voice"),
        tile("First-try logged", _pct(logged, logged + clarified),
             f"{clarified} clarifies"),
        tile("ASR failures", str(asr_failed)),
        tile("Consented clips", str(clips)),
    ])

    max_day = max((r["n"] for r in by_day), default=1)
    day_bars = "".join(
        f'<div class="bar-row"><span class="bar-label">{r["day"]}</span>'
        f'<span class="bar" style="width:{max(4, round(100 * r["n"] / max_day))}%">'
        f'{r["n"]}</span></div>'
        for r in reversed(list(by_day))
    ) or '<p class="quiet">No usage yet.</p>'

    outcome_rows = "".join(
        f'<tr><td>{html.escape(r["outcome"])}</td><td class="num">{r["n"]}</td>'
        f'<td class="num">{_pct(r["n"], total_utt)}</td></tr>'
        for r in outcomes
    ) or '<tr><td colspan="3">No usage yet.</td></tr>'

    def links(sid: str) -> str:
        q = f"session={sid}&token={token}"
        return (f'<a href="/admin/export?{q}&what=usage">usage</a> · '
                f'<a href="/admin/export?{q}&what=transactions">txns</a> · '
                f'<a href="/admin/statement?{q}">statement</a> · '
                f'<a href="/admin/audio?{q}">clips</a>')

    session_rows = "".join(
        f'<tr><td><code>{html.escape(r["session_id"][:8])}</code></td>'
        f'<td class="num">{r["transactions"]}</td>'
        f'<td class="num">&#8358;{(r["sales_total"] or 0):,}</td>'
        f'<td class="num">{r["utterances"]}</td>'
        f'<td class="num">{r["voice_utterances"]}</td>'
        f'<td class="num">{r["logged"]}</td>'
        f'<td class="num">{r["clarified"]}</td>'
        f'<td class="num">{r["asr_failures"]}</td>'
        f'<td class="num">{r["retained_clips"]}</td>'
        f'<td>{(r["last_ts"] or "")[:16].replace("T", " ")}</td>'
        f'<td class="links">{links(r["session_id"])}</td></tr>'
        for r in sessions
    ) or '<tr><td colspan="11">No sessions yet.</td></tr>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>SautiLedger admin</title>
<style>
  :root {{ --bg:#f5f1e8; --card:#fff; --line:#e5ded0; --ink:#1c2434;
           --muted:#77808f; --green:#0d9d64; --green-deep:#0a7a4e;
           --amber:#b7791f; }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--ink); padding:24px;
          font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
          max-width:1080px; margin:0 auto; font-size:15px; line-height:1.45; }}
  header {{ display:flex; align-items:baseline; justify-content:space-between;
            margin-bottom:18px; flex-wrap:wrap; gap:6px; }}
  h1 {{ font-size:1.25rem; font-weight:800; }}
  h1 .dot {{ display:inline-block; width:10px; height:10px; border-radius:50%;
             background:var(--green); margin-right:8px; }}
  .stamp {{ color:var(--muted); font-size:0.8rem; }}
  .tiles {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
            gap:12px; margin-bottom:20px; }}
  .tile {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
           padding:14px 16px; box-shadow:0 6px 18px rgba(28,36,52,0.06); }}
  .tile .k {{ font-size:0.66rem; text-transform:uppercase; letter-spacing:0.1em;
              color:var(--muted); font-weight:700; }}
  .tile .v {{ font-size:1.55rem; font-weight:800; font-variant-numeric:tabular-nums; }}
  section {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
             padding:16px 18px; margin-bottom:16px;
             box-shadow:0 6px 18px rgba(28,36,52,0.06); }}
  h2 {{ font-size:0.72rem; text-transform:uppercase; letter-spacing:0.1em;
        color:var(--muted); margin-bottom:10px; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.86rem; }}
  th, td {{ text-align:left; padding:6px 8px; border-bottom:1px solid #f0ece2; }}
  th {{ font-size:0.66rem; text-transform:uppercase; letter-spacing:0.08em;
        color:var(--muted); }}
  td.num, th.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  code {{ background:var(--bg); border-radius:6px; padding:1px 6px; font-size:0.8rem; }}
  a {{ color:var(--green-deep); font-weight:600; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  .links {{ white-space:nowrap; font-size:0.8rem; }}
  .bar-row {{ display:flex; align-items:center; gap:10px; margin:4px 0; }}
  .bar-label {{ flex:0 0 84px; font-size:0.78rem; color:var(--muted);
                font-variant-numeric:tabular-nums; }}
  .bar {{ background:var(--green); color:#fff; border-radius:6px; padding:2px 8px;
          font-size:0.78rem; font-weight:700; min-width:26px;
          font-variant-numeric:tabular-nums; }}
  .quiet {{ color:var(--muted); }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  @media (max-width:720px) {{ .grid2 {{ grid-template-columns:1fr; }}
    .table-wrap {{ overflow-x:auto; }} }}
</style></head><body>
<header>
  <h1><span class="dot"></span>SautiLedger &mdash; field operations</h1>
  <span class="stamp">Refreshes every minute &middot; generated {generated}</span>
</header>
<div class="tiles">{tiles}</div>
<div class="grid2">
  <section><h2>Utterances per day</h2>{day_bars}</section>
  <section><h2>Outcomes</h2>
    <table><thead><tr><th>Outcome</th><th class="num">Count</th>
    <th class="num">Share</th></tr></thead><tbody>{outcome_rows}</tbody></table>
  </section>
</div>
<section><h2>Sessions</h2><div class="table-wrap">
  <table><thead><tr><th>Book</th><th class="num">Txns</th><th class="num">Sales</th>
  <th class="num">Utt.</th><th class="num">Voice</th><th class="num">Logged</th>
  <th class="num">Clarify</th><th class="num">ASR fail</th><th class="num">Clips</th>
  <th>Last active</th><th>Export</th></tr></thead>
  <tbody>{session_rows}</tbody></table>
</div></section>
</body></html>"""
