# HAIST_WORKS — KNK 물류허브 (Logistics Hub)

㈜케이엔케이 KNK업무시스템구축 프로젝트의 물류 모듈 — 완성품 / 자재 / 소모품 통합 관리.

## 목적
부품등록 → 관리번호 매칭 → 발주 → 입고 → 재고 흐름을 한 곳에서 추적.

## 스택
- Backend: FastAPI + Jinja2 + SQLite
- Frontend: Vanilla HTML/CSS (Pretendard 폰트, KNK 디자인 토큰)
- Port: `8081` (데일리허브 v2의 8080과 분리)

## 폴더 구조
```
HAIST_WORKS/
├── run.py                  서버 시작
├── requirements.txt
├── app/
│   ├── main.py             FastAPI 라우트
│   ├── database.py         SQLite 스키마 + CRUD
│   └── templates/
│       ├── base.html       다크 헤더 + 사이드 네비
│       ├── home.html       대시보드
│       ├── parts.html      부품 마스터 목록
│       └── part_form.html  부품 등록·수정
├── static/
│   └── style.css           KNK 브랜드 토큰 + 프리미엄 카드
└── data/
    └── knk_logistics.db    (첫 실행 시 자동 생성)
```

## 실행
```bash
# 1) 의존성 설치 (최초 1회)
pip install -r requirements.txt

# 2) 서버 시작
python run.py

# 3) 브라우저 접속
http://localhost:8081
```

## 단계별 로드맵
- **1단계** ✅ 부품 마스터 등록 / 검색 / 수정 / 삭제
- **2단계** 관리번호 매칭 (KNK PMS 8자리 표준: `001T2604`)
- **3단계** 발주 등록 (PO 헤더 + 라인)
- **4단계** 입고 처리 (부분입고 가능)
- **5단계** 재고 흐름 추적 (입고 / 출고 / 조정)

## 디자인 기준
- KNK Primary RED `#A5282C`, Dark Red `#8B1E22`
- 폰트: Pretendard (fallback 맑은 고딕)
- 데일리허브 v2의 다크 헤더·프리미엄 카드 패턴 일관 적용

---
㈜케이엔케이 | HAIST Innovation | Human & AI create the Best
