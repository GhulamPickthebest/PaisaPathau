"""Flat table rows and HTML view for live rates (client-friendly)."""

from __future__ import annotations

import html
from typing import Any


def build_rates_table_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Build flat table rows: Provider, Rate, Payment Method, Fee, News."""
    matrix = payload.get("aud_npr_transfer_methods") or {}
    matrix_rows = [
        row for row in matrix.get("rows", []) if row.get("status") == "ok"
    ]
    if matrix_rows:
        return [_row_from_transfer_method(row) for row in matrix_rows]

    rows: list[dict[str, Any]] = []
    for record in payload.get("all_rates", []):
        if record.get("status") != "ok":
            continue
        rows.append(_row_from_rate_record(record))
    return rows


def build_unavailable_table_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Providers/methods that could not be quoted."""
    matrix = payload.get("aud_npr_transfer_methods") or {}
    matrix_rows = [
        row
        for row in matrix.get("rows", [])
        if row.get("status") in ("unavailable", "error")
    ]
    if matrix_rows:
        return [
            {
                "provider": row.get("provider", ""),
                "rate": None,
                "payment_method": row.get("transfer_method", ""),
                "fee": row.get("fee"),
                "news": row.get("notes") or row.get("status", "unavailable"),
                "status": row.get("status", "unavailable"),
            }
            for row in matrix_rows
        ]

    return [
        {
            "provider": record.get("provider", ""),
            "rate": None,
            "payment_method": record.get("delivery_method") or "—",
            "fee": None,
            "news": record.get("error_message") or "Unavailable",
            "status": "error",
        }
        for record in payload.get("all_rates", [])
        if record.get("status") == "error"
    ]


def render_rates_html(payload: dict[str, Any]) -> str:
    """Render a simple HTML table for browser viewing."""
    rows = build_rates_table_rows(payload)
    unavailable = build_unavailable_table_rows(payload)
    send_amount = payload.get("send_amount", "")
    last_updated = payload.get("last_updated", "")
    cached = payload.get("cached", False)
    cache_seconds = payload.get("cache_seconds", "")
    fetch_duration = payload.get("fetch_duration_seconds", "")

    meta_parts = [
        f"AUD → NPR · send amount: {html.escape(str(send_amount))}",
        f"Updated: {html.escape(str(last_updated))}",
    ]
    if cached:
        meta_parts.append("Served from cache")
    if fetch_duration:
        meta_parts.append(f"Fetch took {fetch_duration}s")

    body_rows = "".join(_html_row(row) for row in rows) or (
        "<tr><td colspan='5'>No live rates available</td></tr>"
    )
    unavailable_section = ""
    if unavailable:
        unavail_rows = "".join(_html_row(row, dim=True) for row in unavailable)
        unavailable_section = f"""
        <h2>Unavailable</h2>
        <table>
          <thead>
            <tr>
              <th>Provider</th>
              <th>Rate</th>
              <th>Payment Method</th>
              <th>Fee</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>{unavail_rows}</tbody>
        </table>
        """

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PaisaPathau Live Rates</title>
  <style>
    body {{
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      margin: 2rem;
      color: #1a1a1a;
      background: #f7f7f8;
    }}
    h1 {{ margin-bottom: 0.25rem; }}
    .meta {{ color: #555; margin-bottom: 1.5rem; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      box-shadow: 0 1px 3px rgba(0,0,0,.08);
      margin-bottom: 2rem;
    }}
    th, td {{
      border: 1px solid #e5e5e5;
      padding: 0.75rem 1rem;
      text-align: left;
    }}
    th {{
      background: #0f766e;
      color: #fff;
      font-weight: 600;
    }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    .dim td {{ color: #777; }}
    .links {{ margin-top: 1rem; }}
    .links a {{ margin-right: 1rem; }}
  </style>
</head>
<body>
  <h1>AUD → NPR Live Rates</h1>
  <p class="meta">{" · ".join(meta_parts)}</p>
  <table>
    <thead>
      <tr>
        <th>Provider</th>
        <th>Rate</th>
        <th>Payment Method</th>
        <th>Fee</th>
        <th>Notes</th>
      </tr>
    </thead>
    <tbody>{body_rows}</tbody>
  </table>
  {unavailable_section}
  <p class="links">
    <a href="/data/rates_table.json">Table JSON</a>
    <a href="/data/latest_rates.json">Full JSON</a>
    <a href="/health">Health</a>
  </p>
</body>
</html>"""


def _row_from_transfer_method(row: dict[str, Any]) -> dict[str, Any]:
    news_parts: list[str] = []
    if row.get("notes"):
        news_parts.append(str(row["notes"]))
    existing = row.get("existing_user_rate")
    new_rate = row.get("new_user_rate")
    if existing and new_rate and existing != new_rate:
        news_parts.append(f"Existing user rate: {existing}")
    return {
        "provider": row.get("provider", ""),
        "rate": new_rate,
        "payment_method": row.get("transfer_method", ""),
        "fee": row.get("fee"),
        "news": " · ".join(news_parts),
        "status": "ok",
    }


def _row_from_rate_record(record: dict[str, Any]) -> dict[str, Any]:
    news_parts: list[str] = []
    if record.get("rate_label"):
        news_parts.append(str(record["rate_label"]))
    if record.get("transfer_speed"):
        news_parts.append(str(record["transfer_speed"]))
    return {
        "provider": record.get("provider", ""),
        "rate": record.get("exchange_rate"),
        "payment_method": record.get("delivery_method") or "—",
        "fee": record.get("fee"),
        "news": " · ".join(news_parts),
        "status": "ok",
    }


def _format_rate(value: Any) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "—"


def _format_fee(value: Any, currency: str = "AUD") -> str:
    if value is None:
        return "—"
    try:
        amount = float(value)
        if amount == 0:
            return f"$0 {currency}"
        return f"${amount:g} {currency}"
    except (TypeError, ValueError):
        return "—"


def _html_row(row: dict[str, Any], dim: bool = False) -> str:
    tr_class = ' class="dim"' if dim else ""
    return (
        f"<tr{tr_class}>"
        f"<td>{html.escape(str(row.get('provider', '')))}</td>"
        f"<td>{html.escape(_format_rate(row.get('rate')))}</td>"
        f"<td>{html.escape(str(row.get('payment_method', '') or '—'))}</td>"
        f"<td>{html.escape(_format_fee(row.get('fee')))}</td>"
        f"<td>{html.escape(str(row.get('news', '') or '—'))}</td>"
        f"</tr>"
    )
