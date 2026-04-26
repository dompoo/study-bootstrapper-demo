# 사용 가이드

이 레포는 **스터디자료(PDF) 업로드용 템플릿**입니다.   
"Use this template" 버튼으로 새 레포를 만들면 GitHub Actions가 알아서 PDF 다운로드 → 썸네일 추출 → README 갱신까지 처리합니다.

> 💡 **회차(session) 개념**: 한 회차는 한 번의 스터디 모임이며, 여러 발표가 묶입니다. 1주에 여러 회차를 진행해도 됩니다.

---

## 1. 새 레포 만들기

1. 이 페이지 우상단의 **`Use this template`** → **`Create a new repository`** 클릭
2. 레포 이름과 공개 범위(Public/Private)를 지정하고 생성
3. 생성된 레포를 로컬에 clone

> Public 레포라면 README의 PDF/썸네일 링크가 외부에서도 보입니다. Private 레포라면 같은 레포 권한이 있는 사람만 접근 가능합니다.

## 2. 스터디 정보 채우기

`.automation/templates/readme_header.md` 파일을 열어서 다음 항목을 자기 스터디에 맞게 수정해주세요.

- 스터디 이름 (`# 📚 스터디 이름`)
- 스터디 소개
- 스터디원 목록 (GitHub 프로필 이미지 / 닉네임 / 링크)
- 문의 메일 등 연락처

수정 후 main 브랜치에 push하면 끝입니다. 이 헤더는 README의 상단에 그대로 들어갑니다.

> 가능하면 첫 발표 이슈를 등록하기 전에 `readme_header.md`부터 수정하시는 걸 추천드립니다. 첫 이슈 처리 시 README가 자동 생성되는데, 이때 헤더 내용도 함께 반영되기 때문입니다.

## 3. 스터디자료 업로드

1. **Issues** 탭 → **New issue** → **`스터디자료 업로드`** 선택
2. 폼을 채우고 PDF 파일을 드래그&드롭 후 Submit
3. GitHub Actions가 자동으로:
   - PDF를 `NN_N회차/` 디렉터리에 저장
   - 첫 페이지 썸네일을 `.automation/thumbnails/` 에 생성
   - `.automation/sessions.yml` 갱신
   - README 재생성 후 커밋&푸시
   - 이슈 제목을 `[업로드] N회차 - 스터디원 / 제목` 형식으로 자동 갱신
   - 이슈에 완료 코멘트를 달고 close

> 이슈 제목은 폼에 미리 채워진 `[업로드] ` 그대로 두셔도 됩니다. 처리가 끝나면 자동으로 정돈된 제목으로 바뀝니다.

### 폼 입력 항목

| 항목 | 필수 | 설명 |
| :--- | :---: | :--- |
| 회차 | ✅ | 숫자만 (예: `17`) |
| 스터디 일자 | 🔸 | `YYYY-MM-DD`. 새 회차일 때만 필수, 기존 회차에 추가하면 비워두셔도 됩니다 |
| 스터디원 | ✅ | 닉네임 또는 이름 |
| 제목 | ✅ | 발표 제목 |
| PDF 파일 | ✅ | 영역에 드래그&드롭 |

## 4. 잘못 올린 자료 롤백하기

스터디자료를 잘못 올렸다면:

1. **New issue** → **`스터디자료 롤백`** 선택
2. 회차 / 스터디원 / 제목을 정확히 일치하게 입력
3. Submit하면 자동으로 PDF / 썸네일 / sessions.yml 항목이 제거되고 README가 재생성됩니다

(회차 / 스터디원 / 제목이 정확히 일치하는 항목이 1개일 때만 처리됩니다. 0개 또는 2개 이상이면 실패하고 코멘트로 안내됩니다.)

## 5. README 수동 재빌드

`.automation/sessions.yml`을 직접 손볼 일이 생긴다면, **Actions** 탭 → **Build README** → **Run workflow** 로 수동 재생성을 트리거할 수 있습니다.

---

## 동작 원리

- `.github/workflows/process-upload.yml` — 제목이 `[업로드]`로 시작하는 이슈가 열리면 발동
- `.github/workflows/process-rollback.yml` — 제목이 `[롤백]`로 시작하는 이슈가 열리면 발동
- `.github/workflows/build-readme.yml` — 수동 트리거 (workflow_dispatch)
- `.automation/scripts/process_upload_issue.py` — 이슈 본문 파싱 → PDF 다운로드 → sessions.yml 추가
- `.automation/scripts/process_rollback_issue.py` — 이슈 본문 파싱 → 항목/파일 삭제
- `.automation/scripts/generate_thumbnails.py` — PDF 첫 페이지를 PNG로 추출 (poppler-utils 사용)
- `.automation/scripts/generate_readme.py` — `sessions.yml` + `readme_header.md` → `README.md` 재생성

PDF / 썸네일 / README의 GitHub URL은 워크플로 실행 시점의 `GITHUB_REPOSITORY` 환경변수에서 자동으로 만들어지므로 별도 설정이 필요 없습니다.

## 권한

이슈 처리 워크플로는 OWNER / MEMBER / COLLABORATOR / CONTRIBUTOR 권한이 있는 사용자가 연 이슈만 처리합니다. 외부 사용자가 스터디자료를 임의로 추가하거나 지울 수 없습니다.

## 트러블슈팅

- **"PDF 첨부 링크를 본문에서 찾을 수 없습니다"** — 이슈 폼의 PDF 영역에 파일이 첨부되지 않았거나 GitHub의 user-attachments 링크 형식이 아닐 때 발생합니다. 이슈를 닫고 다시 작성해보세요.
- **"받은 파일이 PDF가 아닙니다"** — 첨부 파일이 손상되었거나 PDF가 아닐 때 발생합니다.
- **"이미 같은 항목이 등록되어 있습니다"** — 같은 회차에 같은 스터디원/제목이 이미 등록돼 있습니다. 롤백 후 다시 올려주세요.
- 워크플로가 실패하면 이슈에 자동으로 코멘트가 달리고 워크플로 로그 링크가 포함됩니다.
