#!/usr/bin/env python3
"""
이슈 폼으로 제출된 스터디자료 롤백(삭제) 요청을 처리한다.

입력
  - 환경변수 ISSUE_BODY: 이슈 본문 (Issue Form 형식)

동작
  1) 본문에서 회차/스터디원/제목 파싱
  2) .automation/sessions.yml에서 (session, presenter, title) 일치 항목 검색
     - 0개 또는 2개 이상이면 실패하고 이슈에 코멘트로 안내
  3) PDF / 썸네일 PNG 삭제, sessions.yml에서 항목 제거
  4) 해당 회차의 발표가 0개가 되면 회차 자체를 yml에서 제거하고 빈 디렉터리도 정리
"""
from __future__ import annotations

import os
import re
import sys
import unicodedata
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent.parent.parent
DATA_FILE = ROOT / ".automation" / "sessions.yml"
THUMB_REL_PREFIX = ".automation/thumbnails/"


def parse_issue_body(body: str) -> dict[str, str]:
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


def main() -> int:
    body = os.environ.get("ISSUE_BODY", "")
    if not body.strip():
        fail("이슈 본문이 비어있습니다")

    sections = parse_issue_body(body)
    session_str = sections.get("회차", "").strip()
    presenter = sections.get("스터디원", "").strip()
    title = sections.get("제목", "").strip()

    if not session_str.isdigit():
        fail(f"회차는 숫자여야 합니다: {session_str!r}")
    session_no = int(session_str)
    if not presenter:
        fail("스터디원이 비어있습니다")
    if not title:
        fail("제목이 비어있습니다")

    with DATA_FILE.open() as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data.get("sessions"), list):
        data["sessions"] = []

    target_session = next((s for s in data["sessions"] if s["session"] == session_no), None)
    if target_session is None:
        fail(f"S{session_no}가 sessions.yml에 존재하지 않습니다")

    presentations = target_session.get("presentations", [])
    matches = [
        (i, p) for i, p in enumerate(presentations)
        if p.get("presenter") == presenter and p.get("title") == title
    ]

    if len(matches) == 0:
        existing = "\n".join(
            f"  - {p.get('presenter')} / {p.get('title')!r}" for p in presentations
        ) or "  (없음)"
        fail(
            f"S{session_no}에서 ({presenter}, {title!r}) 항목을 찾을 수 없습니다.\n"
            f"현재 등록된 항목:\n{existing}"
        )
    if len(matches) > 1:
        fail(f"S{session_no}에 ({presenter}, {title!r}) 항목이 {len(matches)}개 있습니다 (중복)")

    idx, target = matches[0]
    pdf_rel = target.get("pdf") or ""
    thumb_rel = target.get("thumbnail") or ""

    pdf_deleted = ""
    if pdf_rel:
        pdf_path = ROOT / unicodedata.normalize("NFC", pdf_rel)
        if pdf_path.exists():
            pdf_path.unlink()
            print(f"삭제: {pdf_rel}")
            pdf_deleted = pdf_rel
        else:
            print(f"warn: PDF 파일이 이미 없습니다: {pdf_rel}", file=sys.stderr)
            pdf_deleted = pdf_rel

    thumb_deleted = ""
    if thumb_rel and thumb_rel.startswith(THUMB_REL_PREFIX):
        thumb_path = ROOT / unicodedata.normalize("NFC", thumb_rel)
        if thumb_path.exists():
            thumb_path.unlink()
            print(f"삭제: {thumb_rel}")
            thumb_deleted = thumb_rel
        else:
            print(f"warn: 썸네일이 이미 없습니다: {thumb_rel}", file=sys.stderr)
            thumb_deleted = thumb_rel

    presentations.pop(idx)

    session_dir_removed = ""
    if not presentations:
        data["sessions"] = [s for s in data["sessions"] if s["session"] != session_no]
        session_dir_name = unicodedata.normalize("NFC", f"{session_no:02d}_{session_no}회차")
        session_dir = ROOT / session_dir_name
        if session_dir.exists() and session_dir.is_dir():
            try:
                session_dir.rmdir()
                print(f"빈 회차 디렉터리 제거: {session_dir_name}")
                session_dir_removed = session_dir_name
            except OSError:
                print(
                    f"warn: {session_dir_name}에 다른 파일이 남아있어 디렉터리는 유지합니다",
                    file=sys.stderr,
                )
        print(f"S{session_no} 회차 자체를 sessions.yml에서 제거")
    else:
        print(f"S{session_no}에서 ({presenter}, {title!r}) 제거")

    with DATA_FILE.open("w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, width=1000)

    set_output("session", str(session_no))
    set_output("presenter", presenter)
    set_output("title", title)
    set_output("pdf_path", pdf_deleted)
    set_output("thumb_path", thumb_deleted)
    set_output("session_dir_removed", session_dir_removed)
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
