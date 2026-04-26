# 📚 스터디자료 자동 정리 템플릿

스터디 스터디자료(PDF)를 **이슈만 올리면** 자동으로 정리되는 GitHub 레포 템플릿입니다.

- 📝 이슈 폼에 PDF 첨부 → GitHub Actions가 PDF를 받아 디렉터리에 저장
- 🖼️ PDF 첫 페이지를 썸네일로 자동 추출
- 📋 README의 목차 / 회차별 섹션 자동 갱신
- ↩️ 잘못 올린 자료는 롤백 이슈로 한 번에 제거

> 💡 **회차(session) 개념**: 한 회차는 한 번의 스터디 모임이며 여러 발표가 묶일 수 있습니다. 1주에 여러 회차를 진행해도 됩니다.

---

## 🚀 빠른 시작

1. 이 페이지 우상단의 **`Use this template`** → **`Create a new repository`** 로 새 레포 생성
2. `.automation/templates/readme_header.md` 를 **자기 스터디 정보**로 수정 (스터디 이름 / 소개 / 멤버 / 연락처)
3. **Issues** 탭 → **New issue** → **`스터디자료 업로드`** 폼을 채우고 PDF 첨부 → Submit

자세한 사용법은 [SETUP.md](./SETUP.md) 를 참고해주세요.

---

> 💡 첫 발표 이슈가 처리되면 이 README는 자동으로 발표 목록 페이지로 교체됩니다.   
> 영구 가이드는 [SETUP.md](./SETUP.md) 에 있습니다.
