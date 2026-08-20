"""Jinja2 템플릿 렌더링."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
TEMPLATES = ROOT / "templates"
DOCS = ROOT / "docs"

SEV_COLOR = {
    "good": "#0ca30c",
    "warning": "#fab219",
    "serious": "#ec835a",
    "critical": "#d03b3b",
}


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(template: str, **ctx) -> str:
    ctx.setdefault("sev_color", SEV_COLOR)
    return _env().get_template(template).render(**ctx)


def write(name: str, html: str) -> Path:
    DOCS.mkdir(parents=True, exist_ok=True)
    path = DOCS / name
    path.write_text(html, encoding="utf-8")
    print(f"[render] {path.relative_to(ROOT)} ({len(html):,} bytes)")
    return path
