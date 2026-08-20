"""진입점.

  python src/main.py report            # 데이터 수집 → 대시보드 + 이메일
  python src/main.py report --mock     # 가짜 데이터로 로컬 테스트 (네트워크 불필요)
  python src/main.py report --no-email # 메일 없이 대시보드만
  python src/main.py backtest          # 백테스트 페이지 생성
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

import alerts as alerts_mod  # noqa: E402
import backtest as bt  # noqa: E402
import charts  # noqa: E402
import fetch  # noqa: E402
import indicators  # noqa: E402
import notify  # noqa: E402
import portfolio as pf  # noqa: E402
import render  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
KST = timezone(timedelta(hours=9))


def load_config(path: Path) -> dict:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))

    # 공개 레포에서 보유 종목을 숨기고 싶을 때: PORTFOLIO_JSON Secret 이
    # 있으면 config.yml 의 portfolio 를 덮어쓴다.
    raw = os.getenv("PORTFOLIO_JSON", "").strip()
    if raw:
        try:
            cfg["portfolio"] = {**cfg.get("portfolio", {}), **json.loads(raw)}
            print("[config] PORTFOLIO_JSON 적용")
        except json.JSONDecodeError as exc:
            print(f"[config] PORTFOLIO_JSON 파싱 실패, config.yml 값을 씁니다: {exc}")
    return cfg


def _now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")


# ------------------------------------------------------------------ report


def cmd_report(cfg: dict, args) -> int:
    rc = cfg.get("report", {})
    watch = list(cfg.get("watchlist", []))
    holdings = [h["ticker"] for h in (cfg.get("portfolio", {}).get("holdings") or [])]
    tickers = sorted(set(watch) | set(holdings))

    prices = fetch.load_prices(tickers, int(rc.get("lookback_days", 420)), mock=args.mock)
    if not prices:
        print("[report] 가격 데이터를 하나도 받지 못했습니다.")
        return 1

    stats = {t: indicators.summarize(df) for t, df in prices.items()}
    fired = alerts_mod.evaluate(cfg.get("alerts", []), prices, stats)
    port = pf.evaluate(cfg.get("portfolio", {}), prices)

    spark_days = int(rc.get("sparkline_days", 60))
    rows = []
    for t in watch:
        if t not in stats:
            continue
        s = dict(stats[t], ticker=t)
        closes = prices[t]["Close"].tail(spark_days).tolist()
        s["spark"] = charts.sparkline(closes)
        s["meter"] = charts.range_meter(s["low_52w"], s["high_52w"], s["close"])
        rows.append(s)
    rows.sort(key=lambda r: r["chg_1d"], reverse=True)

    weight_items = [(r["ticker"], r["weight"]) for r in port["rows"]]
    if port["cash_weight"] > 0:
        weight_items.append(("현금", port["cash_weight"]))

    last_close = max(df.index[-1] for df in prices.values()).date().isoformat()
    ctx = dict(
        title=rc.get("title", "US Stock Daily"),
        generated_kst=_now_kst(),
        last_close_date=last_close,
        stats=rows,
        fired=fired,
        portfolio=port,
        weight_bar=charts.weight_bar(weight_items),
        sparkline_days=spark_days,
        dashboard_url=os.getenv("DASHBOARD_URL", ""),
        public_dashboard=bool(rc.get("public_dashboard", False)),
    )

    # 웹 대시보드는 public_dashboard 설정에 따라 포트폴리오 섹션을 감춘다.
    # 이메일은 본인만 받으므로 항상 전체를 담는다.
    dash_path = render.write("index.html", render.render("dashboard.html.j2", **ctx))

    # 기록용 JSON — 나중에 추이 분석/블로그 소재로 쓰기 좋다
    hist_dir = ROOT / "data" / "history"
    hist_dir.mkdir(parents=True, exist_ok=True)
    (hist_dir / f"{last_close}.json").write_text(
        json.dumps(
            {
                "date": last_close,
                "portfolio": {k: v for k, v in port.items() if k != "rows"},
                "positions": port["rows"],
                "alerts": fired,
                "quotes": {t: stats[t] for t in stats},
            },
            ensure_ascii=False,
            indent=2,
            default=float,
        ),
        encoding="utf-8",
    )

    ec = cfg.get("email", {})
    if args.no_email or not ec.get("enabled", True):
        print("[report] 메일 발송 생략")
    elif ec.get("only_when_alerts") and not fired:
        print("[report] 알림이 없어 메일 생략")
    else:
        subject = ec.get("subject", "[{date}] {title} — {alert_count}건 알림").format(
            date=last_close, title=ctx["title"], alert_count=len(fired)
        )

        attachments = []
        if ec.get("attach_dashboard", True):
            if ctx["public_dashboard"]:
                # 웹에 올라간 버전은 포트폴리오가 빠져 있으므로, 메일용으로
                # 전체 버전을 따로 만들어 첨부한다 (커밋하지 않는 임시 파일)
                full = render.render("dashboard.html.j2", **{**ctx, "public_dashboard": False})
                tmp = ROOT / "data" / f"dashboard-{last_close}.html"
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_text(full, encoding="utf-8")
                attachments.append(tmp)
            else:
                attachments.append(dash_path)

        notify.send(
            subject,
            render.render("email.html.j2", **ctx),
            notify.plain_summary(fired, port),
            attachments=attachments,
        )

    print(f"[report] 완료 · 종목 {len(rows)} · 알림 {len(fired)}")
    return 0


# ---------------------------------------------------------------- backtest


def cmd_backtest(cfg: dict, args) -> int:
    bc = cfg.get("backtest", {})
    tickers = bc.get("tickers", [])
    prices = fetch.load_prices(tickers, 4000, mock=args.mock)
    if not prices:
        print("[backtest] 가격 데이터 없음")
        return 1

    results = bt.run_matrix(prices, bc)
    if not results:
        print("[backtest] 결과 없음 - 기간이나 종목 설정을 확인하세요")
        return 1

    results.sort(key=lambda r: r["total_return"], reverse=True)

    charts_ctx = []
    for r in results[: args.charts]:
        eq, bh = r["equity"], r["bh_equity"]
        n = max(len(eq) // 400, 1)  # SVG 경량화를 위해 다운샘플
        charts_ctx.append(
            dict(
                r,
                svg=charts.equity_chart(
                    [d.date().isoformat() for d in eq.index[::n]],
                    [("전략", eq.iloc[::n].tolist()), ("단순보유", bh.iloc[::n].tolist())],
                ),
            )
        )

    html = render.render(
        "backtest.html.j2",
        generated_kst=_now_kst(),
        fee_bps=bc.get("fee_bps", 5),
        results=results,
        charts=charts_ctx,
    )
    render.write("backtest.html", html)
    print(f"[backtest] 완료 · 조합 {len(results)}개")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="stock-automation")
    p.add_argument("command", choices=["report", "backtest"])
    p.add_argument("--config", default=str(ROOT / "config.yml"))
    p.add_argument("--mock", action="store_true", help="가짜 데이터로 실행 (네트워크 불필요)")
    p.add_argument("--no-email", action="store_true")
    p.add_argument("--charts", type=int, default=6, help="백테스트 상세 차트 개수")
    args = p.parse_args()

    cfg = load_config(Path(args.config))
    return cmd_report(cfg, args) if args.command == "report" else cmd_backtest(cfg, args)


if __name__ == "__main__":
    raise SystemExit(main())
