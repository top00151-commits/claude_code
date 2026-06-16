# 자동 미러 설정 — claude_code(01_HAIST_WORKS) → knk-haist-works

목표: **모노레포 한 곳(claude_code)에만 작업·push** 하면, 배포 저장소(knk-haist-works)로
자동 복사되고 NAS가 1분 cron으로 받아 **자동 배포**된다. → 휴대폰만 있어도 평소대로 끝.

워크플로 파일: `.github/workflows/mirror-works-to-deploy.yml`

## ✅ 현재 상태 (2026-06-16 활성)

- `DEPLOY_REPO_TOKEN` 시크릿 등록 완료.
- 두 저장소 **정합(reconcile) 완료** — 라이브의 최신코드(회의록·영업기회·SSO 등)를
  모노레포로 가져와 일치시킴(import-live-into-monorepo 워크플로, 커밋 df58f6c).
- 미러 **자동(push→live) 켜짐**: `main` 의 `01_HAIST_WORKS/**` 가 바뀌면 자동으로 라이브 반영.

### ⚠️ 운영 규칙 (반드시)
- 앞으로 **WORKS 작업은 claude_code(모노레포)에서만** 한다.
- **라이브 저장소(knk-haist-works)를 직접 수정하지 말 것** — 다음 미러 때 덮어써져 다시 갈라진다.
- 직접 고쳐야 할 일이 생기면, 먼저 `import-live-into-monorepo` 로 라이브→모노레포 정합 후 작업.

## 1회 설정 (대표 — 휴대폰 브라우저로도 가능)

### A. 배포 저장소 쓰기용 토큰 발급
1. GitHub → 우측 위 프로필 → **Settings** → **Developer settings**
2. **Personal access tokens → Fine-grained tokens → Generate new token**
3. Repository access: **Only select repositories → `top00151-commits/knk-haist-works`**
4. Permissions → Repository permissions → **Contents: Read and write**
5. Generate → **토큰 문자열 복사**(한 번만 보임).

### B. claude_code 에 시크릿 등록
1. `top00151-commits/claude_code` → **Settings** → **Secrets and variables → Actions**
2. **New repository secret**
   - Name: `DEPLOY_REPO_TOKEN`
   - Secret: (A에서 복사한 토큰)
3. Add secret.

## 2. 작동 방식

- `main` 브랜치에 `KNK업무시스템구축/01_HAIST_WORKS/**` 변경이 push 되면 자동 실행.
- git이 추적하는 파일만 복사(런타임/비밀 `data/ uploads/ .env logs/ .venv/` 는 양쪽 gitignore라 제외).
- **삭제하지 않음(additive)** → 배포 저장소 파일을 잘못 지우지 않음.

## 3. 먼저 안전 점검(권장) — 푸시 없이 미리보기

1. claude_code → **Actions** 탭 → "Mirror HAIST WORKS → deploy repo" →
   **Run workflow** → mode=**report** 실행.
2. 로그에서 "추가/수정될 파일" 과 "고아 후보(배포 저장소에만 있는 파일)" 확인.
3. 이상 없으면 mode=**live** 로 한 번 실행하거나, 이후 push 부터 자동 적용.

## 4. 주의

- additive 라서, 모노레포에서 **파일을 삭제/이름변경** 한 경우는 배포 저장소에 자동 반영되지 않음
  (옛 파일이 남음). 그런 경우만 배포 저장소에서 1회 수동 정리하거나, 별도 정리 실행.
- 이 워크플로는 **main 브랜치 기준**으로 동작함. 기능 브랜치 push 로는 트리거되지 않음.
- 메일(15_KNK_Mail)·메신저(10_KNK_Messenger)도 같은 2-저장소 구조면 동일 워크플로를 복제해 적용 가능.
