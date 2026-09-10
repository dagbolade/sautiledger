"""Bank-readiness statement: a trader's ledger as an artefact a lender
doing MANUAL review can read — real computed figures only. Deliberately
unglamorous: no score, no rating, no model. The page prints cleanly, so
"Save as PDF" in any browser produces the document.
"""

from __future__ import annotations

import html
from pathlib import Path
from datetime import datetime

_SIGNS = {"NGN": "₦", "KES": "KSh ", "USD": "$"}

DISCLAIMER = ("This is transaction history, not a credit assessment. "
              "It is designed to be legible to a lender doing manual review, "
              "not to plug into any specific bank's API.")


def _fmt(amount: int, sign: str) -> str:
    return f"${amount / 100:,.2f}" if sign == "$" else f"{sign}{amount:,}"


def statement_stats(rows) -> dict:
    """Real arithmetic over non-voided rows — nothing inferred."""
    sales = [r for r in rows if r["type"] == "sale"]
    expenses = [r for r in rows if r["type"] == "expense"]
    sales_total = sum(r["amount"] or 0 for r in sales)
    expense_total = sum(r["amount"] or 0 for r in expenses)
    sales_days = {r["ts"][:10] for r in sales}
    active_days = {r["ts"][:10] for r in rows}
    return {
        "sales_total": sales_total,
        "expense_total": expense_total,
        "net": sales_total - expense_total,
        "sales_count": len(sales),
        "expense_count": len(expenses),
        "active_days": len(active_days),
        "sales_days": len(sales_days),
        "avg_daily_sales": round(sales_total / len(sales_days)) if sales_days else 0,
        "credit_open": sum(r["amount"] or 0 for r in rows
                           if r["payment_status"] == "credit"),
    }


def build_statement_html(rows, currency: str, period_label: str,
                         period_days: int, owner_label: str) -> str:
    sign = _SIGNS.get(currency, currency + " ")
    stats = statement_stats(rows)
    stylesheet = (Path(__file__).resolve().parents[2] / "static" / "statement.css").read_text(encoding="utf-8")
    generated = datetime.now().strftime("%d %B %Y, %H:%M")

    def table_rows() -> str:
        out = []
        for r in rows:
            what = html.escape(r["item"] or "entry")
            if r["quantity"] and r["unit"]:
                what += f" ({r['quantity']} {html.escape(str(r['unit']))})"
            elif r["quantity"]:
                what += f" (x{r['quantity']})"
            kind = "Sale" if r["type"] == "sale" else "Expense"
            status = "on credit" if r["payment_status"] == "credit" else "paid"
            out.append(
                f"<tr><td>{html.escape(r['ts'][:10])}</td><td>{what}</td><td>{kind}</td>"
                f"<td>{status}</td><td class='num'>{_fmt(r['amount'] or 0, sign)}</td></tr>"
            )
        return "\n".join(out)

    consistency = (f"Sales recorded on {stats['sales_days']} of {period_days} days "
                   f"in this period; {stats['active_days']} day"
                   f"{'s' if stats['active_days'] != 1 else ''} with ledger activity.")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SautiLedger statement</title>
<style>{stylesheet}</style></head><body>
<div class="screen-actions"><a href="/">← Back to my book</a><button onclick="window.print()">Print / Save as PDF</button></div>
<article class="paper">
<header>
  <div><p class="brand">SautiLedger <span>BUSINESS RECORDS</span></p><h1>Trading statement</h1></div>
  <div class="meta">{html.escape(owner_label)}<br>{html.escape(period_label)}<br>
  Generated {generated}</div>
</header>
<p class="intro">A clear record of your trading activity.</p>
<div class="totals">
  <div class="stat"><div class="k">Total sales</div>
    <div class="v">{_fmt(stats['sales_total'], sign)}</div>
    <div class="k">{stats['sales_count']} transaction{'s' if stats['sales_count'] != 1 else ''}</div></div>
  <div class="stat"><div class="k">Total expenses</div>
    <div class="v">{_fmt(stats['expense_total'], sign)}</div>
    <div class="k">{stats['expense_count']} transaction{'s' if stats['expense_count'] != 1 else ''}</div></div>
  <div class="stat"><div class="k">Sales less expenses</div>
    <div class="v">{_fmt(stats['net'], sign)}</div></div>
  <div class="stat"><div class="k">Average daily sales</div>
    <div class="v">{_fmt(stats['avg_daily_sales'], sign)}</div>
    <div class="k">across {stats['sales_days']} selling day{'s' if stats['sales_days'] != 1 else ''}</div></div>
</div>
<p class="balance-note">Sales include transactions on credit. Sales less expenses is not a cash balance or a calculation of profit.</p>
<p class="consistency">{consistency}
{f"Credit outstanding: {_fmt(stats['credit_open'], sign)}." if stats['credit_open'] else ""}</p>
<h2>Transaction history</h2>
<div class="table-wrap"><table>
  <thead><tr><th>Date</th><th>Entry</th><th>Type</th><th>Status</th>
  <th class="num">Amount</th></tr></thead>
  <tbody>
  {table_rows() if rows else '<tr><td colspan="5">No transactions in this period.</td></tr>'}
  </tbody>
</table></div>
<div class="disclaimer">{DISCLAIMER} Voided entries are excluded; figures are
computed directly from the recorded transactions above.</div>
<footer><span>SautiLedger · Your everyday money book</span><span>Currency: {html.escape(currency)}</span></footer>
</article>
</body></html>"""
