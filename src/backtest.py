"""단순 롱/현금 백테스트.

의도적으로 단순하게 유지했다. 신호는 전일 종가로 판단하고 다음 날 종가에
체결한다고 가정(look-ahead bias 방지). 수수료·슬리피지는 bp 단위로 차감.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from indicators import max_drawdown, rsi, sma

TRADING_DAYS = 252


# ---------------------------------------------------------------- 시그널


def signal_sma_cross(df: pd.DataFrame, fast: int = 20, slow: int = 60) -> pd.Series:
    close = df["Close"]
    f, s = sma(close, fast), sma(close, slow)
    return (f > s).astype(float).where(f.notna() & s.notna())


def signal_rsi_reversion(
    df: pd.DataFrame, period: int = 14, buy_below: float = 30, sell_above: float = 70
) -> pd.Series:
    r = rsi(df["Close"], period)
    pos = pd.Series(np.nan, index=df.index)
    holding = 0.0
    for i, v in enumerate(r):
        if pd.isna(v):
            continue
        if holding == 0 and v < buy_below:
            holding = 1.0
        elif holding == 1 and v > sell_above:
            holding = 0.0
        pos.iloc[i] = holding
    return pos


SIGNALS = {"sma_cross": signal_sma_cross, "rsi_reversion": signal_rsi_reversion}


# ---------------------------------------------------------------- 실행


def run(
    df: pd.DataFrame,
    strategy: dict,
    initial_cash: float = 10_000,
    fee_bps: float = 5.0,
    start: str | None = None,
) -> dict:
    df = df.copy()
    if start:
        df = df[df.index >= pd.Timestamp(start)]
    if len(df) < 60:
        return {}

    params = {k: v for k, v in strategy.items() if k not in ("name", "type")}
    fn = SIGNALS[strategy["type"]]
    raw_pos = fn(df, **params).fillna(0.0)

    # 신호는 당일 종가 기준 → 다음 날부터 포지션 반영
    pos = raw_pos.shift(1).fillna(0.0)

    ret = df["Close"].pct_change().fillna(0.0)
    trades = pos.diff().abs().fillna(pos.abs())
    cost = trades * (fee_bps / 10_000)

    strat_ret = pos * ret - cost
    equity = initial_cash * (1 + strat_ret).cumprod()
    bh_equity = initial_cash * (1 + ret).cumprod()

    n_years = max(len(df) / TRADING_DAYS, 1e-9)
    n_trades = int((trades > 0).sum())

    # 체결 단위로 승률 계산
    wins, losses, trade_returns = 0, 0, []
    entry_price = None
    for date, p in pos.items():
        price = float(df.loc[date, "Close"])
        if p == 1 and entry_price is None:
            entry_price = price
        elif p == 0 and entry_price is not None:
            r = price / entry_price - 1
            trade_returns.append(r)
            wins += r > 0
            losses += r <= 0
            entry_price = None

    def cagr(eq: pd.Series) -> float:
        return float((eq.iloc[-1] / initial_cash) ** (1 / n_years) - 1) * 100

    ann_vol = float(strat_ret.std() * np.sqrt(TRADING_DAYS)) or np.nan
    sharpe = float(strat_ret.mean() * TRADING_DAYS / ann_vol) if ann_vol else float("nan")

    return {
        "strategy": strategy.get("name", strategy["type"]),
        "start": df.index[0].date().isoformat(),
        "end": df.index[-1].date().isoformat(),
        "days": len(df),
        "final": float(equity.iloc[-1]),
        "total_return": float(equity.iloc[-1] / initial_cash - 1) * 100,
        "cagr": cagr(equity),
        "mdd": max_drawdown(equity),
        "sharpe": sharpe,
        "vol": ann_vol * 100,
        "trades": n_trades,
        "win_rate": (wins / (wins + losses) * 100) if (wins + losses) else float("nan"),
        "avg_trade": (float(np.mean(trade_returns)) * 100) if trade_returns else float("nan"),
        "exposure": float((pos > 0).mean()) * 100,
        "bh_total_return": float(bh_equity.iloc[-1] / initial_cash - 1) * 100,
        "bh_cagr": cagr(bh_equity),
        "bh_mdd": max_drawdown(bh_equity),
        "equity": equity,
        "bh_equity": bh_equity,
    }


def run_matrix(
    prices: dict[str, pd.DataFrame], cfg: dict
) -> list[dict]:
    """설정된 종목 × 전략 조합을 모두 돌린다."""
    results = []
    for t in cfg.get("tickers", []):
        if t not in prices:
            continue
        for strat in cfg.get("strategies", []):
            r = run(
                prices[t],
                strat,
                initial_cash=float(cfg.get("initial_cash", 10_000)),
                fee_bps=float(cfg.get("fee_bps", 5)),
                start=cfg.get("start"),
            )
            if r:
                r["ticker"] = t
                results.append(r)
    return results
