"""주가 데이터 수집.

기본 소스는 yfinance(무료, 미국 주식). 네트워크가 막힌 환경이나
테스트용으로는 --mock 을 쓰면 결정론적 가짜 시계열을 만들어 준다.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = np.nan
    df = df[COLUMNS].dropna(subset=["Close"])
    return df.sort_index()


def _mock_series(ticker: str, days: int) -> pd.DataFrame:
    """티커 이름으로 시드를 고정한 기하 브라운 운동. 매번 같은 값이 나온다."""
    seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)

    n = days
    start_price = 40 + (seed % 400)
    drift = 0.0004 + (seed % 7) * 0.00008
    vol = 0.012 + (seed % 5) * 0.004

    shocks = rng.normal(drift, vol, n)
    # 중간에 조정 구간을 하나 넣어 알림 규칙이 실제로 걸리는지 보이게 한다
    dip_start = int(n * 0.74)
    shocks[dip_start: dip_start + 15] -= 0.012
    close = start_price * np.exp(np.cumsum(shocks))

    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=n)
    intraday = np.abs(rng.normal(0, 0.006, n))
    df = pd.DataFrame(
        {
            "Open": close * (1 - intraday / 2),
            "High": close * (1 + intraday),
            "Low": close * (1 - intraday),
            "Close": close,
            "Volume": rng.integers(2_000_000, 60_000_000, n).astype(float),
        },
        index=idx,
    )
    df.loc[df.index[-1], "Volume"] *= 1 + (seed % 3)
    return _normalize(df)


def _yf_download(tickers: list[str], period_days: int) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    raw = yf.download(
        tickers=" ".join(tickers),
        period=f"{period_days}d",
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        progress=False,
        threads=True,
    )
    out: dict[str, pd.DataFrame] = {}
    for t in tickers:
        try:
            df = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
            df = _normalize(df)
            if len(df) >= 30:
                out[t] = df
        except (KeyError, ValueError):
            continue
    return out


def load_prices(
    tickers: list[str],
    lookback_days: int = 420,
    mock: bool = False,
    use_cache: bool = True,
) -> dict[str, pd.DataFrame]:
    """티커별 일봉 DataFrame(dict) 반환. 실패한 티커는 조용히 빠진다."""
    tickers = sorted(set(tickers))
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if mock:
        return {t: _mock_series(t, lookback_days) for t in tickers}

    try:
        data = _yf_download(tickers, lookback_days)
    except Exception as exc:  # 네트워크/API 장애 시 캐시로 폴백
        print(f"[fetch] 다운로드 실패: {exc}")
        data = {}

    missing = [t for t in tickers if t not in data]
    if missing and use_cache:
        for t in missing:
            p = CACHE_DIR / f"{t}.csv"
            if p.exists():
                print(f"[fetch] {t}: 캐시 사용")
                data[t] = _normalize(pd.read_csv(p, index_col=0, parse_dates=True))

    for t, df in data.items():
        df.to_csv(CACHE_DIR / f"{t}.csv")

    still_missing = [t for t in tickers if t not in data]
    if still_missing:
        print(f"[fetch] 데이터 없음: {', '.join(still_missing)}")
    return data
