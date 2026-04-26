#!/usr/bin/env python3
"""
이슈 폼으로 제출된 스터디자료 업로드 요청을 처리한다.

입력
  - 환경변수 ISSUE_BODY: 이슈 본문 (Issue Form 형식)
  - 환경변수 GITHUB_TOKEN: user-attachments 다운로드용

동작
  1) 본문에서 회차/스터디 일자/스터디원/제목/PDF 링크 파싱
  2) PDF 다운로드 (NFC 정규화된 파일명으로 저장)
  3) .automation/sessions.yml에 항목 추가 (해당 회차가 없으면 새 회차 생성)
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata
from pathlib import Path

import requests
import yaml


ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = ROOT / ".automation" / "sessions.yml"

NO_RESPONSE_PLACEHOLDERS = {"", "_No response_"}


def parse_issue_body(body: str) -> dict[str, str]:
    """`### 헤딩` 블록을 키-값 dict로."""
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    for line in body.replace("\r\n", "\n").split("\n"):
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            if current_key is not None:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_key is not None:
        sections[current_key] = "\n".join(current_lines).strip()
    return sections


def extract_pdf_url(text: str) -> str | None:
    m = re.search(r"\[([^\]]+\.pdf)\]\((https?://[^\)]+)\)", text, re.IGNORECASE)
    return m.group(2) if m else None


def slugify_filename(title: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", title).strip()
    cleaned = unicodedata.normalize("NFC", cleaned)
    return cleaned or "untitled"


def set_output(name: str, value: str) -> None:
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    with open(out, "a") as f:
        f.write(f"{name}<<__EOF__\n{value}\n__EOF__\n")


def fail(msg: str) -> None:
    set_output("error", msg)
    print(f"::error::{msg}", file=sys.stderr)
    sys.exit(1)


def download_pdf(url: str) -> bytes:
    headers = {"Accept": "application/octet-stream"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, timeout=120, allow_redirects=True)
    if resp.status_code != 200:
        fail(f"PDF 다운로드 실패: HTTP {resp.status_code}")
    if not resp.content.startswith(b"%PDF"):
        fail("받은 파일이 PDF가 아닙니다")
    return resp.content


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        fail("이슈 본문이 비어있습니다")

    sections = parse_issue_body(body)

    session_str = sections.get("회차", "").strip()
    date_raw = sections.get("스터디 일자", "").strip()
    presenter = sections.get("스터디원", "").strip()
    title = sections.get("제목", "").strip()
    pdf_field = sections.get("PDF 파일", "")

    if not session_str.isdigit():
        fail(f"회차는 숫자여야 합니다: {session_str!r}")
    session_no = int(session_str)
    if session_no < 1 or session_no > 999:
        fail(f"회차 범위 초과: {session_no}")
    if not presenter:
        fail("스터디원이 비어있습니다")
    if not title:
        fail("제목이 비어있습니다")

    date = "" if date_raw in NO_RESPONSE_PLACEHOLDERS else date_raw
    if date and not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        fail(f"스터디 일자 형식이 잘못되었습니다 (YYYY-MM-DD 필요): {date!r}")

    pdf_url = extract_pdf_url(pdf_field)
    if not pdf_url:
        fail("PDF 첨부 링크를 본문에서 찾을 수 없습니다")

    with DATA_FILE.open() as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data.get("sessions"), list):
        data["sessions"] = []

    target_session = next((s for s in data["sessions"] if s["session"] == session_no), None)

    if target_session is None and not date:
        fail(f"S{session_no}는 새로 생성되는 회차이므로 스터디 일자가 필요합니다")
    if target_session is not None:
        for p in target_session.get("presentations", []):
            if p.get("presenter") == presenter and p.get("title") == title:
                fail(f"이미 같은 항목이 등록되어 있습니다: S{session_no} {presenter} {title!r}")

    print(f"PDF 다운로드: {pdf_url}")
    pdf_bytes = download_pdf(pdf_url)

    session_dir_name = unicodedata.normalize("NFC", f"{session_no:02d}_{session_no}회차")
    session_dir = ROOT / session_dir_name
    session_dir.mkdir(parents=True, exist_ok=True)

    file_basename = slugify_filename(title) + ".pdf"
    pdf_path = session_dir / file_basename
    if pdf_path.exists():
        fail(f"이미 같은 경로에 파일이 있습니다: {pdf_path.relative_to(ROOT)}")
    pdf_path.write_bytes(pdf_bytes)
    print(f"저장: {pdf_path.relative_to(ROOT)} ({len(pdf_bytes):,} bytes)")

    pdf_rel = f"{session_dir_name}/{file_basename}"

    new_entry = {
        "title": title,
        "presenter": presenter,
        "pdf": pdf_rel,
        "thumbnail": None,
    }

    if target_session is None:
        data["sessions"].append({
            "session": session_no,
            "date": date,
            "presentations": [new_entry],
        })
        data["sessions"].sort(key=lambda s: s["session"])
        print(f"새 회차 생성: S{session_no} ({date})")
    else:
        target_session.setdefault("presentations", []).append(new_entry)
        print(f"기존 회차에 추가: S{session_no}")

    with DATA_FILE.open("w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, width=1000)

    set_output("session", str(session_no))
    set_output("presenter", presenter)
    set_output("title", title)
    set_output("pdf_path", pdf_rel)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
