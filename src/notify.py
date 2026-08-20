"""이메일 발송 (SMTP).

필요한 환경변수 - GitHub Secrets 로 주입한다:
  SMTP_HOST  (기본 smtp.gmail.com)
  SMTP_PORT  (기본 465, SSL)
  SMTP_USER  보내는 계정
  SMTP_PASS  앱 비밀번호 (Gmail 은 2단계 인증 후 발급하는 16자리)
  MAIL_TO    받는 주소, 쉼표로 여러 개 가능
"""
from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path


def send(
    subject: str,
    html: str,
    text_fallback: str = "",
    attachments: list[Path] | None = None,
) -> bool:
    host = os.getenv("SMTP_HOST") or "smtp.gmail.com"
    port = int(os.getenv("SMTP_PORT") or "465")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    to = os.getenv("MAIL_TO") or user

    if not (user and password and to):
        print("[notify] SMTP 설정이 없어 메일을 건너뜁니다 (SMTP_USER / SMTP_PASS / MAIL_TO)")
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr(("Stock Bot", user))
    msg["To"] = ", ".join(a.strip() for a in to.split(","))
    msg.set_content(text_fallback or "HTML 메일입니다. HTML 보기를 지원하는 클라이언트에서 열어주세요.")
    msg.add_alternative(html, subtype="html")

    # 대시보드 HTML 첨부 - 웹에 공개하지 않아도 받는 사람이 열어볼 수 있게
    for path in attachments or []:
        p = Path(path)
        if not p.exists():
            print(f"[notify] 첨부 건너뜀 (파일 없음): {p}")
            continue
        msg.add_attachment(
            p.read_bytes(),
            maintype="text",
            subtype="html",
            filename=p.name,
        )
        print(f"[notify] 첨부: {p.name} ({p.stat().st_size:,} bytes)")

    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=30) as s:
                s.login(user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.starttls()
                s.login(user, password)
                s.send_message(msg)
    except Exception as exc:
        print(f"[notify] 메일 발송 실패: {exc}")
        return False

    print(f"[notify] 메일 발송 완료 → {msg['To']}")
    return True


def plain_summary(fired: list[dict], portfolio: dict) -> str:
    lines = []
    if portfolio.get("has_holdings"):
        lines.append(
            f"포트폴리오 ${portfolio['total']:,.0f} "
            f"({portfolio['day_pct']:+.2f}% 오늘, 누적 {portfolio['pnl_pct']:+.2f}%)"
        )
    lines.append(f"알림 {len(fired)}건")
    lines += [f"- [{a['severity']}] {a['message']}" for a in fired]
    return "\n".join(lines)
