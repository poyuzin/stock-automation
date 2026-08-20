"""보유 종목 평가 - 수익률, 비중, 일간 손익."""
from __future__ import annotations

import pandas as pd


def evaluate(cfg: dict, prices: dict[str, pd.DataFrame]) -> dict:
    holdings = cfg.get("holdings") or []
    cash = float(cfg.get("cash", 0) or 0)

    rows = []
    for h in holdings:
        t = h["ticker"]
        if t not in prices:
            continue
        close = prices[t]["Close"]
        last = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) > 1 else last
        shares = float(h["shares"])
        avg = float(h["avg_price"])

        value = last * shares
        cost = avg * shares
        rows.append(
            {
                "ticker": t,
                "shares": shares,
                "avg_price": avg,
                "price": last,
                "value": value,
                "cost": cost,
                "pnl": value - cost,
                "pnl_pct": (last / avg - 1) * 100 if avg else 0.0,
                "day_pnl": (last - prev) * shares,
                "day_pct": (last / prev - 1) * 100 if prev else 0.0,
            }
        )

    equity = sum(r["value"] for r in rows)
    total = equity + cash
    cost_total = sum(r["cost"] for r in rows)
    day_pnl = sum(r["day_pnl"] for r in rows)
    prev_total = total - day_pnl

    for r in rows:
        r["weight"] = (r["value"] / total * 100) if total else 0.0
    rows.sort(key=lambda r: r["value"], reverse=True)

    return {
        "rows": rows,
        "cash": cash,
        "cash_weight": (cash / total * 100) if total else 0.0,
        "equity": equity,
        "total": total,
        "cost": cost_total,
        "pnl": equity - cost_total,
        "pnl_pct": ((equity / cost_total - 1) * 100) if cost_total else 0.0,
        "day_pnl": day_pnl,
        "day_pct": (day_pnl / prev_total * 100) if prev_total else 0.0,
        "has_holdings": bool(rows),
    }
