# 📨 DONE — 13차 supplier_form.html 시안1 z58 (공급사 풀체인 완성)

> **분류:** DONE
> **발신:** 실무팀3 (자재구매센터, 워크트리 cranky-shtern-789fa2)
> **수신:** 빅터(01)
> **시각:** 2026-05-11 17:00
> **응답 필요:** 검수 + git push

---

## 한 줄 요지
**supplier_form.html** 시안1 z58 전면 재작성 (신규 + 수정 단일 페이지 통합) — 4 섹션 + 리드타임 KPI(편집 모드) + **D 공급사 그룹 풀체인 완성**.

## 첨부
- HANDOFF: [`HANDOFF_TO_01_v13.md`](../HANDOFF_TO_01_v13.md)
- PROGRESS: [`../../PROGRESS.md`](../../PROGRESS.md)

## 산출 (1 파일)

### supplier_form.html
- **4 섹션**: 기본정보(명·코드·국가·활성) / 연락처(담당·전화·이메일) / 결제·거래조건(통화·결제) / 비고
- **사이드 4 카드**: 요약 / 📊 리드타임 통계(편집만, KPI 4) / 💡 가이드 / ⚠️ 삭제
- **라우터 호환** form name 10개 정확 정합

## 공급사 D 그룹 풀체인 완성 ✅
| 페이지 | 차수 |
|---|---|
| suppliers (목록) | z57 (7차) |
| **supplier_form** | **z58 (13차)** |

## 풀체인 완성 6개 그룹 ✅
| 그룹 | 페이지 | 차수 |
|---|---|---|
| A 자재 홈 | logistics_home | z57 |
| B 발주 | po_list / form / detail / receive | z57·z58 |
| C 부품 | parts / form / detail | z58 |
| **D 공급사** | **suppliers / supplier_form** | **z57·z58** |
| F 작업지시 | wo_list / form / print | z57·z58 |
| G 품질 | qc_report_list / form / print | z57·z58 |

## 자체 검증 결과 (1패스)
- amber-grad / knk-red: 0건 ✓
- data-dn / action / name: 21 매칭 ✓
- supplier 14 변수 + leadtime 4 + PAYMENT_TERMS 활용 ✓

## 100% 준수
- 발주서 7항 (라우트·DB 0건): 0 위반
- 룰 v4 ADDENDUM: 0 위반
- 99_DISPATCH: 0건
- 상표권 익명화: 외부 실명 0건

## 검수 1줄
```
http://localhost:8081/suppliers/new?debug=1
http://localhost:8081/suppliers/{id}/edit?debug=1
```

## 빅터(01) 처리 요청
- [ ] 신규·수정 양 모드 검수
- [ ] 리드타임 KPI (편집 모드) 표시 확인
- [ ] STATUS.md 🟢 통합 완료 z58 13차 등록
- [ ] git push
- [ ] **다음 차수 (14차) 승인**

## 누적 진행
**23 페이지 / 30+ (77%)** — 6차~13차 8 차수 누적.

## 다음 트리거
- 빅터 검수 회신 → 14차 (빅터 추천: stock_issue 단독)
- 또는 대표 직접 추가 지시
