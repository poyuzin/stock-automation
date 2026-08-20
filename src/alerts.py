"""config.yml 의 알림 규칙을 평가한다."""
from __future__ import annotations

import pandas as pd

from indicators import rsi, sma

SEVERITY_ORDER = {"critical": 0, "serious": 1, "warning": 2, "good": 3}


def _threshold_hit(value: float, rule: dict) -> bool:
    if value is None or pd.isna(value):
        return False
    if "above" in rule and value > rule["above"]:
        return True
    if "below" in rule and value < rule["below"]:
        return True
    return False


def _sma_cross(df: pd.DataFrame, fast: int, slow: int, direction: str) -> bool:
    close = df["Close"]
    f, s = sma(close, fast), sma(close, slow)
    if f.notna().sum() < 2 or s.notna().sum() < 2:
        return False
    prev_diff = f.iloc[-2] - s.iloc[-2]
    curr_diff = f.iloc[-1] - s.iloc[-1]
    if pd.isna(prev_diff) or pd.isna(curr_diff):
        return False
    if direction == "up":
        return prev_diff <= 0 < curr_diff
    return prev_diff >= 0 > curr_diff


def evaluate(
    rules: list[dict],
    prices: dict[str, pd.DataFrame],
    stats: dict[str, dict],
) -> list[dict]:
    """조건을 만족한 알림 목록을 심각도 순으로 반환."""
    fired: list[dict] = []

    for rule in rules:
        targets = [rule["ticker"]] if rule.get("ticker") else list(prices.keys())
        for t in targets:
            if t not in prices:
                continue
            df, st = prices[t], stats[t]
            rtype = rule["type"]
            value = None
            hit = False

            if rtype == "pct_change":
                w = int(rule.get("window", 1))
                value = st.get(f"chg_{w}d")
                if value is None:
                    from indicators import pct_change_n

                    value = pct_change_n(df["Close"], w)
                hit = _threshold_hit(value, rule)

            elif rtype == "rsi":
                value = float(rsi(df["Close"], int(rule.get("period", 14))).iloc[-1])
                hit = _threshold_hit(value, rule)

            elif rtype == "price":
                value = st["close"]
                hit = _threshold_hit(value, rule)

            elif rtype == "pct_from_52w_high":
                value = st["pct_from_52w_high"]
                hit = _threshold_hit(value, rule)

            elif rtype == "volume_spike":
                value = st["vol_ratio"]
                hit = pd.notna(value) and value >= float(rule.get("ratio", 2.0))

            elif rtype == "sma_cross":
                hit = _sma_cross(
                    df,
                    int(rule.get("fast", 20)),
                    int(rule.get("slow", 60)),
                    rule.get("direction", "up"),
                )
                value = st["close"]

            else:
                print(f"[alerts] 알 수 없는 규칙 타입: {rtype}")
                continue

            if hit:
                template = rule.get("message", "{ticker}: {value}")
                try:
                    text = template.format(ticker=t, value=value)
                except (KeyError, ValueError):
                    text = f"{t}: {value}"
                fired.append(
                    {
                        "id": rule.get("id", rtype),
                        "ticker": t,
                        "severity": rule.get("severity", "warning"),
                        "message": text,
                        "value": value,
                    }
                )

    fired.sort(key=lambda a: (SEVERITY_ORDER.get(a["severity"], 9), a["ticker"]))
    return fired
