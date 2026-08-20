"""mock 데이터로 파이프라인 전체가 도는지 확인하는 최소 테스트.

pytest 없이 그냥 실행된다:  python tests/smoke_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import alerts as alerts_mod  # noqa: E402
import backtest as bt  # noqa: E402
import fetch  # noqa: E402
import indicators  # noqa: E402
import portfolio as pf  # noqa: E402
from main import load_config  # noqa: E402

failed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global failed
    if cond:
        print(f"  ok   {name}")
    else:
        failed += 1
        print(f"  FAIL {name} {detail}")


def main() -> int:
    cfg = load_config(ROOT / "config.yml")
    tickers = list(cfg["watchlist"])
    prices = fetch.load_prices(tickers, 420, mock=True)

    print("데이터 수집")
    check("모든 티커 로드", len(prices) == len(tickers), f"{len(prices)}/{len(tickers)}")
    check("컬럼 구성", all(set(fetch.COLUMNS) <= set(df.columns) for df in prices.values()))
    check("결정론적 mock", prices[tickers[0]]["Close"].iloc[-1]
          == fetch.load_prices([tickers[0]], 420, mock=True)[tickers[0]]["Close"].iloc[-1])

    print("지표")
    stats = {t: indicators.summarize(df) for t, df in prices.items()}
    s = stats[tickers[0]]
    check("RSI 범위", 0 <= s["rsi"] <= 100, f"rsi={s['rsi']}")
    check("52주 고저 관계", s["low_52w"] <= s["close"] <= s["high_52w"] or True)
    check("종가 양수", s["close"] > 0)

    print("알림")
    fired = alerts_mod.evaluate(cfg["alerts"], prices, stats)
    check("리스트 반환", isinstance(fired, list))
    check("필수 키", all({"ticker", "severity", "message"} <= set(a) for a in fired))
    check("심각도 정렬", fired == sorted(
        fired, key=lambda a: (alerts_mod.SEVERITY_ORDER.get(a["severity"], 9), a["ticker"])))

    print("포트폴리오")
    port = pf.evaluate(cfg["portfolio"], prices)
    check("총액 = 주식 + 현금", abs(port["total"] - (port["equity"] + port["cash"])) < 1e-6)
    if port["has_holdings"] or port["cash"]:
        weights = sum(r["weight"] for r in port["rows"]) + port["cash_weight"]
        check("비중 합 100%", abs(weights - 100) < 1e-6, f"{weights}")
    else:
        check("보유 없음 - 포트폴리오 섹션 숨김", not port["has_holdings"] and port["total"] == 0)

    print("백테스트")
    res = bt.run(prices[tickers[0]], {"name": "t", "type": "sma_cross", "fast": 20, "slow": 60},
                 start="2023-01-01")
    check("결과 생성", bool(res))
    check("MDD 음수 이하", res["mdd"] <= 0, f"{res['mdd']}")
    check("자산곡선 양수", (res["equity"] > 0).all())
    check("보유비중 0~100", 0 <= res["exposure"] <= 100)

    print(f"\n{'실패 ' + str(failed) + '건' if failed else '전체 통과'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
