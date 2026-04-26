#!/usr/bin/env python3
"""
.automation/sessions.yml + .automation/templates/readme_header.md 로 README.md 전체를 재생성한다.

규칙
- 헤더 파일 아래에 "## 📣 목차" 테이블을 자동 생성
- 회차별 섹션(<a id="session-N"></a>)을 발표자 수에 맞게 2-column table 로 렌더
- PDF / 썸네일 링크는 sessions.yml 값을 그대로 사용
- 로컬 경로는 NFC로 URL 인코딩하여 GitHub raw/blob URL 로 변환
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import unicodedata
import urllib.parse
from pathlib import Path

import yaml


# Script lives at .automation/scripts/; repo root is two levels up.
ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = ROOT / ".automation" / "sessions.yml"
HEADER_FILE = ROOT / ".automation" / "templates" / "readme_header.md"
OUT_FILE = ROOT / "README.md"


def detect_repo_slug() -> str:
    """Return owner/repo. Prefer GITHUB_REPOSITORY (set by Actions), fall back to `git remote`."""
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env.strip()
    try:
        url = subprocess.check_output(
            ["git", "-C", str(ROOT), "config", "--get", "remote.origin.url"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""
    m = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", url)
    return m.group(1) if m else ""


def detect_branch() -> str:
    return os.environ.get("GITHUB_REF_NAME") or os.environ.get("README_BRANCH") or "main"


REPO_SLUG = detect_repo_slug()
BRANCH = detect_branch()
REPO_BASE = f"https://github.com/{REPO_SLUG}/blob/{BRANCH}/" if REPO_SLUG else ""
RAW_BASE = f"https://github.com/{REPO_SLUG}/raw/{BRANCH}/" if REPO_SLUG else ""


def encode_repo_path(rel_path: str, for_raw: bool = False) -> str:
    """Encode a repo-relative path into a GitHub URL.

    All segments are NFC-normalized so URLs match the repo's stored filenames.
    """
    if not rel_path:
        return ""
    # External URLs passed through
    if rel_path.startswith("http"):
        return rel_path
    parts = rel_path.split("/")
    encoded_parts = [
        urllib.parse.quote(unicodedata.normalize("NFC", p), safe="()")
        for p in parts
    ]
    base = RAW_BASE if for_raw else REPO_BASE
    return base + "/".join(encoded_parts)


def thumb_url(rel_path: str | None) -> str:
    if not rel_path:
        return ""
    if rel_path.startswith("http"):
        return rel_path
    return encode_repo_path(rel_path, for_raw=True)


def anchor_for_toc(session: int) -> str:
    return f"#session-{session}"


def format_date(date_str: str) -> tuple[str, str]:
    y, m, d = date_str.split("-")
    long = f"{int(y)}년 {int(m)}월 {int(d)}일"
    short = f"{y}.{int(m)}.{d.zfill(2)}"
    return long, short


def render_toc(sessions: list[dict]) -> str:
    lines = [
        "## 📣 목차",
        "",
        "| 회차 | 발표 주제 및 스터디원 |",
        "| :--- | :--- |",
    ]
    for s in sessions:
        long, short = format_date(s["date"])
        items = "<br>".join(
            f"• {p['title']} (👤 {p['presenter']})" for p in s["presentations"]
        )
        lines.append(f"| [**{s['session']}회차** ({short})]({anchor_for_toc(s['session'])}) | {items} |")
    lines.extend(["", "", "<br>", "<br>", ""])
    return "\n".join(lines)


def render_session_section(s: dict) -> str:
    long_date, _ = format_date(s["date"])
    ps = s["presentations"]
    n = len(ps)

    # Title table
    title_cells = " | ".join(p["title"] for p in ps)
    divider = " | ".join([":-:"] * n)
    presenter_cells = " | ".join(p["presenter"] for p in ps)

    out = [
        f'<a id="session-{s["session"]}"></a>',
        "",
        f'## **{s["session"]}회차** ( {long_date} )',
        "",
        f"> | {title_cells} |",
        f"> | {divider} |",
        f"> | {presenter_cells} |",
        "",
        "### 💎 스터디자료",
        "",
        "<table>",
    ]

    # Render a 2-column grid of (image, links)
    rows = []
    i = 0
    while i < n:
        left, right = ps[i], ps[i + 1] if i + 1 < n else None
        rows.append((left, right))
        i += 2

    for left, right in rows:
        # image row
        out.append("  <tr>")
        out.append(f'    <td width="50%" align="center">')
        img = thumb_url(left.get("thumbnail"))
        if img:
            out.append(f'      <img src="{img}" width="100%">')
        out.append("    </td>")
        if right:
            out.append(f'    <td width="50%" align="center">')
            img_r = thumb_url(right.get("thumbnail"))
            if img_r:
                out.append(f'      <img src="{img_r}" width="100%">')
            out.append("    </td>")
        else:
            out.append("    <td>&nbsp;</td>")
        out.append("  </tr>")

        # link row
        out.append("  <tr>")
        for cell in (left, right):
            if cell is None:
                out.append("    <td>&nbsp;</td>")
                continue
            pdf_url = encode_repo_path(cell.get("pdf")) if cell.get("pdf") else ""
            out.append('    <td align="center">')
            out.append(f'      <a href="{pdf_url}">[📚 {cell["title"]}]</a>')
            out.append("    </td>")
        out.append("  </tr>")

    out.extend(["</table>", "", "---", ""])
    return "\n".join(out)


def main() -> int:
    data = yaml.safe_load(DATA_FILE.read_text()) or {}
    sessions = sorted(data.get("sessions") or [], key=lambda s: s["session"])

    header = HEADER_FILE.read_text().rstrip() + "\n\n"
    if sessions:
        toc = render_toc(sessions)
        body = "\n".join("<br/>\n" + render_session_section(s) for s in sessions)
        content = header + toc + body
    else:
        content = header + "_아직 등록된 발표가 없습니다. 첫 이슈를 등록해보세요._\n"

    OUT_FILE.write_text(content)
    print(f"wrote {OUT_FILE} ({len(sessions)} sessions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
