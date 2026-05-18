# 📨 DONE — 8차 part_detail.html 시안1 z58 단독 차수 (z58 시리즈 종료)

> **분류:** DONE
> **발신:** 실무팀3 (자재구매센터, 워크트리 cranky-shtern-789fa2)
> **수신:** 빅터(01)
> **시각:** 2026-05-11 12:00
> **응답 필요:** 검수 + z58 시리즈 4 차수 일괄 통합 + git push

---

## 한 줄 요지
빅터 추천 순서 §8차 = z58 마지막. **part_detail.html** 구버전(amber-grad) → 시안1 z58 전면 재작성. **9 섹션 + 사이드 3카드 + KPI 5** + 라우터 변수 13종 활용.

## 첨부
- HANDOFF: [`HANDOFF_TO_01_v8.md`](../HANDOFF_TO_01_v8.md)
- PROGRESS: [`../../PROGRESS.md`](../../PROGRESS.md)

## 산출 (1 파일 — 분량 최다)

### 좌측 메인 9 섹션
1. 📦 FIFO 재고 레이어 (잔량 바 + 소비 처리)
2. 💰 단가 이력 30건 (변동률 색상)
3. 📅 적용일자 단가 (managed_prices)
4. 📊 7단가 chain — placeholder (z58 SQL 후)
5. 🌲 BOM 트리 — placeholder (z56 SQL 후, FIN/SEMI만)
6. 📋 최근 입출고 30건 (kind 색상 tag)
7. 🎯 프로젝트별 사용 (관리코드 연결)
8. 📎 첨부 갤러리 (image/pdf/dwg/dxf)
9. ＋ 단가 등록 폼 (10 필드, 라우터 호환)

### 우측 사이드 3 카드
- 📌 마스터 정보 (z58 컬럼 16~20개)
- 🏢 공급사별 단가 요약
- 🚀 빠른 액션 (발주/이동이력/수정)

## 자체 검증 결과 (1패스)
- amber-grad / knk-red 잔존: **0건** ✓
- data-dn 영역: **15개** ✓
- 라우터 변수 13종 활용: **37 매칭** ✓
- 단가 등록 폼 form name 10개: 라우터 호환 ✓

## z58 시리즈 누적 완료 ✅
| 차수 | 항목 | 상태 |
|---|---|---|
| 5차 | z58 SQL | 🟡 적용 위임 |
| 6차 | parts 마스터 + part_form | 🟢 |
| 7차 | VAT 발주 풀체인 (po_form/detail/receive) | 🟢 |
| **8차** | **part_detail** | **🟢** |

## 100% 준수
- 발주서 7항 (라우트 변경 0건 / DB 직접 0건): 0 위반
- 룰 v4 ADDENDUM: 0 위반
- 99_DISPATCH 게시: 0건
- 상표권 익명화: 외부 실명 0건

## 검수 1줄
```
http://localhost:8081/parts/{id}?debug=1
```

## 빅터(01) 처리 요청
- [ ] part_detail.html 검수
- [ ] z58 SQL 적용 결재 (5차)
- [ ] STATUS.md z58 5~8차 일괄 등록
- [ ] git push
- [ ] **다음 차수 — z59 시리즈 또는 다른 영역 (rates_/wo_form/qms_) 승인 대기**

## 다음 트리거
- 빅터 검수 회신 → 다음 차수 시작
- 또는 대표 직접 추가 지시
