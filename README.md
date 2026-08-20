# 미국주식 자동 리포트

GitHub Actions가 평일 장 마감 후 자동으로 돌면서

- 관심 종목 시세·지표를 수집하고
- 설정한 조건에 걸린 종목을 **알림**으로 뽑고
- **웹 대시보드**(GitHub Pages)를 갱신하고
- **이메일**로 요약을 보내고
- 매매 전략을 **백테스트**한다.

서버도 결제도 필요 없다. 전부 GitHub 무료 범위 안에서 돈다.

---

## 0. 친구에게 나눠주기 / 남의 레포에서 시작하기

이 레포는 **템플릿**이다. 오른쪽 위 초록색 **"Use this template" → Create a new repository**를 누르면
자기 계정에 복사본이 생긴다. 이때 **Private으로 만들어도 된다.**

각자 자기 복사본에서:

- 자기 `config.yml` (관심 종목, 알림 규칙)
- 자기 Secrets (메일 계정, 보유 종목)
- 자기 대시보드 주소

를 갖는다. **원본 레포 주인과 데이터가 섞이지 않는다.** 공유되는 건 코드뿐이다.

> Fork가 아니라 Use this template을 쓰는 이유: fork는 원본의 커밋 히스토리를 그대로 들고 오고
> public 원본에서 private fork를 만들 수 없다. 템플릿 복사는 깨끗한 첫 커밋으로 시작하고
> 공개 범위도 자유롭게 고를 수 있다.

레포 주인이 템플릿을 켜는 법: **Settings → General → Template repository 체크**.

---

## 1. 처음 세팅 (15분)

### 1) 레포 만들기

이 폴더를 그대로 새 레포에 올린다. (템플릿에서 복사했다면 이 단계는 건너뛰고 clone만 하면 된다.)

```bash
cd stock-automation
git init
git add .
git commit -m "init: 주식 자동 리포트"
git branch -M main
git remote add origin https://github.com/<내계정>/stock-automation.git
git push -u origin main
```

> **Public / Private 어느 쪽이 맞나**
>
> | | Public | Private |
> |---|---|---|
> | 코드를 남이 볼 수 있나 | 볼 수 있다 (고치는 건 초대한 사람만) | 초대한 사람만 |
> | Actions 무료 사용량 | 무제한 | 월 2,000분 |
> | Pages 대시보드 주소 | 된다 | **무료·Pro 모두 안 된다** (Enterprise 전용) |
> | 내 보유 종목 | `PORTFOLIO_JSON` Secret 에 넣으면 안 보인다 | 어디에 넣든 안 보인다 |
>
> 남에게 나눠줄 생각이면 Public + Secret 조합이 가장 편하다.
> 대시보드를 웹에 안 올리고 싶으면 Private으로 두고 메일 첨부(아래 4번)로 받으면 된다.

### 2) 로컬에서 한 번 돌려보기

```bash
pip install -r requirements.txt
python src/main.py report --mock --no-email    # 가짜 데이터, 메일 없음
open docs/index.html
```

`--mock`은 네트워크 없이 도는 테스트 모드다. 실제 시세로 보려면 `--mock`을 뺀다.

```bash
python src/main.py report --no-email           # 진짜 시세, 메일만 생략
```

### 3) GitHub Pages 켜기

레포 → **Settings → Pages → Source: GitHub Actions** 선택.

첫 워크플로가 성공하면 `https://<내계정>.github.io/stock-automation/` 이 대시보드가 된다.

### 4) 이메일 설정 (Gmail 기준)

Gmail은 일반 비밀번호로는 SMTP 로그인이 안 된다. **앱 비밀번호**를 발급받아야 한다.

1. Google 계정 → 보안 → **2단계 인증**을 먼저 켠다
2. 검색창에 "앱 비밀번호" → 새 앱 비밀번호 생성 → 16자리 문자열 복사

레포 → **Settings → Secrets and variables → Actions → New repository secret** 에서:

| 이름 | 값 |
|---|---|
| `SMTP_USER` | 보내는 Gmail 주소 |
| `SMTP_PASS` | 위에서 받은 앱 비밀번호 16자리 |
| `MAIL_TO` | 받을 주소 (쉼표로 여러 개 가능) |

Gmail이 아니면 `SMTP_HOST` / `SMTP_PORT`도 같이 넣는다 (네이버: `smtp.naver.com` / `465`).

같은 화면의 **Variables** 탭에 `DASHBOARD_URL`을 Pages 주소로 넣어두면
메일 하단에 "대시보드 열기" 버튼이 생긴다.

메일에는 대시보드 HTML이 **첨부파일로 같이 온다.** 웹에 안 올린 포트폴리오까지 들어간
전체 버전이라, Pages를 안 쓰거나 Private 레포여도 첨부만 열면 같은 화면을 볼 수 있다.
필요 없으면 `config.yml`에서 `email.attach_dashboard: false`.

#### 보유 종목 숨기기 (Public 레포일 때)

`config.yml`에 수량·평단가를 적으면 그대로 공개된다. 대신 Secret에 넣는다.

| 이름 | 값 |
|---|---|
| `PORTFOLIO_JSON` | `{"cash": 2000, "holdings": [{"ticker":"AAPL","shares":12,"avg_price":178.40}]}` |

이 Secret이 있으면 `config.yml`의 `portfolio` 설정을 덮어쓴다. 값은 레포 주인만 볼 수 있고
Actions 로그에도 마스킹되어 찍힌다.

그리고 `config.yml`의 `report.public_dashboard: true`를 그대로 두면
**웹 대시보드에서는 포트폴리오 섹션이 빠지고** 워치리스트·알림만 올라간다.
평가금액은 메일과 첨부파일로만 본다.

### 5) 수동으로 한 번 실행

Actions 탭 → **Daily Report** → **Run workflow**.
초록 체크가 뜨고 메일이 오면 끝. 이후로는 평일 아침 6:30(KST)에 알아서 돈다.

---

## 2. 매일 뭘 하면 되나

**아무것도 안 해도 된다.** 고칠 게 생기면 `config.yml`만 건드린다.

```yaml
watchlist:      # 관심 종목 추가/삭제
  - AAPL
  - PLTR        # ← 이렇게 한 줄 추가하고 push 하면 끝

portfolio:
  cash: 2000.0
  holdings:
    - { ticker: AAPL, shares: 12, avg_price: 178.40 }
```

### 알림 규칙

| `type` | 뜻 | 쓰는 옵션 |
|---|---|---|
| `pct_change` | N거래일 등락률 | `window`, `above`/`below` |
| `rsi` | RSI 과매수/과매도 | `period`, `above`/`below` |
| `sma_cross` | 이동평균 골든/데드크로스 | `fast`, `slow`, `direction: up\|down` |
| `price` | 지정가 도달 | `ticker`, `above`/`below` |
| `pct_from_52w_high` | 52주 고가 대비 위치 | `above`/`below` |
| `volume_spike` | 거래량 급증 | `ratio` |

`ticker`를 쓰면 그 종목만, 안 쓰면 워치리스트 전체에 적용된다.
`severity`는 `good` / `warning` / `serious` / `critical` 넷 중 하나.

```yaml
  - id: my_rule
    type: pct_change
    window: 1
    below: -5.0
    severity: critical
    message: "{ticker} 하루 {value:+.2f}% — 확인 필요"
```

---

## 3. 백테스트

```bash
python src/main.py backtest          # docs/backtest.html 생성
```

또는 Actions 탭 → **Backtest** → Run workflow → 완료 후 아티팩트 다운로드.

`config.yml`의 `backtest` 항목에서 종목·기간·전략을 바꾼다.

```yaml
backtest:
  tickers: [AAPL, MSFT, NVDA, SPY]
  start: "2019-01-01"
  fee_bps: 5                        # 편도 0.05% 수수료+슬리피지
  strategies:
    - { name: "SMA 20/60", type: sma_cross, fast: 20, slow: 60 }
    - { name: "RSI 30/70", type: rsi_reversion, period: 14, buy_below: 30, sell_above: 70 }
```

**결과를 읽을 때 주의할 것**

- 신호는 당일 종가로 판단하고 **다음 날 종가에 체결**한다고 가정한다 (미래 데이터를 쓰지 않도록)
- 배당과 세금은 빠져 있다
- 전략을 여러 개 돌려서 제일 좋은 걸 고르면, 그건 과거에 맞춰 고른 것일 뿐이다
  (과최적화). 단순보유 대비 컬럼과 MDD를 같이 봐야 의미가 있다

새 전략을 넣으려면 `src/backtest.py`에 시그널 함수 하나를 추가하고 `SIGNALS` 딕셔너리에 등록하면 된다.

```python
def signal_my_strategy(df, param=10):
    # 1.0 = 보유, 0.0 = 현금 인 Series 를 돌려주면 된다
    return (df["Close"] > df["Close"].rolling(param).mean()).astype(float)

SIGNALS["my_strategy"] = signal_my_strategy
```

---

## 4. 자동매매로 가려면

이 레포는 **주문을 내지 않는다.** 의도적이다. 실계좌 자동매매로 넘어가기 전에 순서가 있다.

1. **백테스트** — 여기까지가 이 레포
2. **페이퍼 트레이딩** — [Alpaca](https://alpaca.markets) 무료 페이퍼 계좌로 가짜 돈 주문을 최소 몇 달
3. **소액 실계좌** — 잃어도 되는 금액으로만
4. 그 다음에야 규모 이야기

주문 API 키를 GitHub Secrets에 넣고 Actions에서 매매를 돌리는 건 기술적으로는 가능하지만,
스케줄 실행이 몇 분 밀리거나 건너뛰는 경우가 있어서 체결 타이밍이 중요한 전략에는 맞지 않는다.
자동매매 단계로 가면 실행 환경을 Actions에서 상시 구동되는 서버로 옮기는 게 맞다.

---

## 5. 구조

```
├── config.yml              ← 대부분 이 파일만 고치면 된다
├── src/
│   ├── main.py             진입점 (report / backtest)
│   ├── fetch.py            데이터 수집 (yfinance + mock + 캐시 폴백)
│   ├── indicators.py       SMA · RSI · 52주 위치 · 변동성
│   ├── alerts.py           알림 규칙 평가
│   ├── portfolio.py        보유 종목 수익률·비중
│   ├── backtest.py         전략 시뮬레이션
│   ├── charts.py           인라인 SVG 차트 (외부 JS 없음)
│   ├── render.py           HTML 렌더링
│   └── notify.py           SMTP 메일 발송
├── templates/              대시보드 · 이메일 · 백테스트 템플릿
├── docs/                   ← GitHub Pages 가 서빙하는 폴더 (자동 생성)
├── data/history/           날짜별 스냅샷 JSON (자동 커밋, 나중에 추이 분석용)
├── tests/smoke_test.py     mock 으로 파이프라인 전체 확인
└── .github/workflows/
    ├── daily.yml           평일 21:30 UTC 자동 실행
    ├── backtest.yml        수동 실행
    └── ci.yml              push/PR 마다 스모크 테스트
```

---

## 6. 자주 걸리는 것

**워크플로가 안 도는데요**
30일 넘게 커밋이 없으면 GitHub가 schedule을 자동으로 멈춘다. 아무 커밋이나 하나 하면 다시 살아난다.
매일 리포트가 커밋을 남기니 실제로는 잘 안 걸린다.

**메일이 안 와요**
Actions 로그에 `[notify] SMTP 설정이 없어...`가 찍혔으면 Secret 이름 오타다.
`앱 비밀번호`가 아니라 계정 비밀번호를 넣은 경우도 흔하다.

**데이터가 비어 있어요**
yfinance가 Yahoo Finance를 긁는 방식이라 가끔 막힌다. `fetch.py`가 직전 캐시로 폴백하도록 되어 있지만,
계속 실패하면 티커 철자를 확인하고(예: `BRK.B` → `BRK-B`) 그래도 안 되면 잠시 후 재실행한다.

**시간이 안 맞아요**
cron은 UTC 기준이고 미국은 서머타임이 있다. `30 21 * * 1-5`는 여름엔 마감 +30분,
겨울엔 마감 -30분(장중)이 된다. 겨울에 정확히 맞추려면 `30 22 * * 1-5`로 바꾼다.

**Actions 보안**
지금은 `actions/checkout@v4`처럼 태그로 고정돼 있다. 실무 레포라면 커밋 SHA로 고정하는 게 안전하다
(`actions/checkout@8f4b7f8...`). 태그는 옮겨 달 수 있고 SHA는 못 옮긴다.

---

이 레포가 만드는 건 **기록과 요약**이지 투자 판단이 아니다.
수치는 Yahoo Finance 무료 데이터라 종종 지연되거나 틀린다. 실제 매매 전에는 증권사 앱으로 확인할 것.
