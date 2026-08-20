"""기술적 지표 계산 - 외부 TA 라이브러리 없이 pandas 만 사용."""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(close: pd.Series, window: int) -> pd.Series:
    return close.rolling(window, min_periods=window).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder smoothing
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(100.0).where(avg_loss.notna())


def pct_change_n(close: pd.Series, n: int) -> float:
    if len(close) <= n:
        return float("nan")
    return float((close.iloc[-1] / close.iloc[-1 - n] - 1) * 100)


def annualized_vol(close: pd.Series, window: int = 20) -> float:
    r = close.pct_change().tail(window)
    if r.notna().sum() < 5:
        return float("nan")
    return float(r.std() * np.sqrt(252) * 100)


def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float(((equity / peak) - 1).min() * 100)


def summarize(df: pd.DataFrame, rsi_period: int = 14) -> dict:
    """대시보드 한 줄에 필요한 값들을 한 번에 계산."""
    close = df["Close"]
    last = float(close.iloc[-1])
    win52 = close.tail(252)
    hi52, lo52 = float(win52.max()), float(win52.min())

    vol_avg20 = float(df["Volume"].tail(20).mean())
    vol_last = float(df["Volume"].iloc[-1])

    s_fast, s_slow = sma(close, 20), sma(close, 60)
    s200 = sma(close, 200)

    return {
        "close": last,
        "chg_1d": pct_change_n(close, 1),
        "chg_5d": pct_change_n(close, 5),
        "chg_20d": pct_change_n(close, 20),
        "chg_ytd": _ytd_change(close),
        "rsi": _safe_last(rsi(close, rsi_period)),
        "sma20": _safe_last(s_fast),
        "sma60": _safe_last(s_slow),
        "sma200": _safe_last(s200),
        "above_sma200": (last > s200.iloc[-1]) if pd.notna(s200.iloc[-1]) else None,
        "high_52w": hi52,
        "low_52w": lo52,
        "pct_from_52w_high": (last / hi52 - 1) * 100 if hi52 else float("nan"),
        "pct_from_52w_low": (last / lo52 - 1) * 100 if lo52 else float("nan"),
        "vol_ratio": vol_last / vol_avg20 if vol_avg20 else float("nan"),
        "volatility_20d": annualized_vol(close),
    }


def _safe_last(s: pd.Series) -> float:
    v = s.iloc[-1] if len(s) else np.nan
    return float(v) if pd.notna(v) else float("nan")


def _ytd_change(close: pd.Series) -> float:
    year = close.index[-1].year
    ytd = close[close.index >= pd.Timestamp(year=year, month=1, day=1)]
    if len(ytd) < 2:
        return float("nan")
    return float((ytd.iloc[-1] / ytd.iloc[0] - 1) * 100)
