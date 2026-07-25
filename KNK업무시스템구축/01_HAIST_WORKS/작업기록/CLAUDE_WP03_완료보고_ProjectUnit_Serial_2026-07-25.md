# WP-03 완료 보고 — 프로젝트 호기·일련번호 (Project Unit·Serial)

> ERP V1 전환 프로그램 · WP-03 · 참조 시나리오 **RS-01**
> 브랜치 `wp03-project-unit` @ `86949ac1` — **main 미반영 · LIVE 무변화**
> ⛔ 운영 데이터 생성 0건(씨앗은 사용자가 화면에서 누를 때만 실행) · 기존 표 무변경(순수 추가)

## 0. 대표 결정 반영 (WP-03 착수 전)
| 결정 | 대표 선택 | 반영 |
|---|---|---|
| Unit 원본(씨앗) | **호기 라인(order_items)** | 정식 호기 라벨 `^\d+호기$`만 씨앗(z779 규약과 동일) |
| 시범 프로젝트 | **005T2601** | 호기 라인 28개 → 진짜 호기 23 + 부속/부품 5 |

## 1. RS-01 통과조건 대응표
| RS-01 요구 | 구현 | 실증 |
|---|---|---|
| 관리번호에서 호기 N대·일련번호 **조회** | `/project/{id}/units` 페이지 + `get_units()` | 테스트 "RS-01 조회" PASS · 페이지 200 |
| 장비수량 기준 **호기 생성** | 씨앗(order_items→project_units) + 수동 추가 | 시범 23대 생성·대조 23=23 |
| **일련번호 연결** | `link_serial()` — 기존 활성 일련은 이력으로 비활성화(끊김 방지) | 테스트 "일련번호 연결됨" PASS |
| 각 Unit은 **하나의 Project**에 속함 | `project_id NOT NULL` + FK → projects | FK ON 강제 |
| 각 Serial은 **법인 내 유일** | `UNIQUE(entity, serial_no) WHERE active=1` | 테스트 ③ PASS(KOR 중복 차단) |
| 차단 ① 프로젝트 내 **제작번호 중복** | `UNIQUE(project_id, unit_no)` + 앱 사전검사 | 테스트 ① PASS |
| 차단 ② **일련번호 중복** | 위 법인 유일 + 앱 사전검사 | 테스트 ③ PASS |
| 차단 ③ **Project 없는 호기** | `project_id` FK + 앱 사전검사 | 테스트 ② PASS |
| 호기 삭제 = **초안 + 이력 없음**만 | `delete_unit()` 상태·전참조 스캔 가드 | 테스트 ④/④' PASS |

## 2. 데이터 모델 (신규 2표 · 기존 무변경)
```
프로젝트(관리번호) ─▶ 수주(orders) ─▶ 호기(project_units·신규) ─▶ 일련번호(equipment_serials·신규)
  projects            orders            seed_order_item_id            active 1건 + 이력
                                        ← 씨앗: order_items(^\d+호기$)
```
- **project_units**: `project_unit_id`(영구 축·앞으로 BOM·출고·투입·변경·출하가 여기 연결) · `project_id`(FK) · `order_id`(FK·SET NULL) · `seed_order_item_id`(FK·SET NULL·추적) · `unit_no` · `entity` · `status`(CHECK draft/active/shipped/cancelled)
- **equipment_serials**: `project_unit_id`(FK CASCADE) · `serial_no` · `entity` · `active` · 이력 보존
- ⭐ FK가 `foreign_keys=ON`에서 강제 → **WP-01 프로젝트 삭제 가드(foreign_key_list 스캔)에 자동 포함**(호기 있는 프로젝트 삭제 차단).
- **수량 컬럼 없음**: 호기 '대수'는 행 수로 표현 → z1048 정수 규정 오염 원천 차단.

## 3. 씨앗 규칙 + 시범 005T2601 호기 수 대조
- 씨앗 대상 = `order_items.unit_label`이 `^\d+호기$`인 라인만(= 시스템 정식 호기, z779 재번호 대상).
- **부속/부품 라인 제외**(비표준 라벨). 시범 005T2601: 28라인 = 진짜 호기 **23**(전부 수량=1) + 부속/부품 **5**(수량>1인 4개 전부 여기).
- **호기 수 대조**: 씨앗 대상 23 = 생성 호기 23 = 조회 호기 23 → **✅ 일치**. 재씨앗 멱등(0 생성).

## 4. 변경 목록 (`86949ac1` · 6파일 · +717줄)
| 파일 | 내용 |
|---|---|
| `app/migrations/m_z1053_project_unit.py` (신규) | project_units·equipment_serials 테이블(idempotent·FK·UNIQUE) |
| `app/project_unit.py` (신규) | 씨앗·조회·생성·일련번호 연결(이력)·삭제 가드·법인 판정·전참조 스캔 |
| `app/main.py` (수정) | 마이그레이션 startup 등록 + 라우트 5종(페이지·씨앗·추가·일련번호·삭제) |
| `app/templates/project_units.html` (신규) | 호기·일련번호 화면(표준 셸·디자인 토큰·사람친화 한국어) |
| `app/templates/project_detail.html` (수정) | 수주 내역 헤더에 '🔧 호기·일련번호 관리' 링크 |
| `tests/test_wp03_project_unit.py` (신규) | RS-01 정식 검증 19건 |

## 5. 테스트 결과
| 검사 | 결과 |
|---|---|
| WP-03 정식 테스트 `tests/test_wp03_project_unit.py` | **19 / 19 PASS**(함수 12 + 라우트 7) |
| 시범 005T2601 씨앗·가드(사본 DB 실증) | 호기 23대·대조 일치·가드 4종·멱등 전부 PASS |
| WP-01 회귀 `tests/test_wp01_p0_guards.py` | **98 / 98 PASS**(추가 변경이 기존 잠금 안 깸) |
| 표준 검사 `deploy/check_standards.py` | **전부 통과**(수량칸 소수 위반 0 — 페이지에 수량 입력칸 없음) |
| `py_compile`(main·모듈·마이그레이션) | ✅ |
| 템플릿 Jinja 렌더 | ✅(라우트 200) |

## 6. 안전 경계 (지킨 것)
- **순수 추가(additive)**: `order_items`·작업일정표·수주내역 **무변경**(교량 조건). 테스트 "additive · order_items 불변" PASS.
- **WP-01 잠금 유지**: 출고·입고·재고 경로 안 건드림(회귀 98/98).
- **씨앗은 사용자 행동**: 자동 생성 없음 — 화면 버튼을 눌러야 실행(안전·통제).
- **PG 호환·규정**: 수량=행 수(z1048) · 날짜=시간대 표준 패턴 · FK/UNIQUE/CHECK 명시.

## 7. 미해결·정직 고지
1. **수량>1 부속 라인 제외**: 시범의 부속/부품 5라인은 호기가 아니므로 Unit 미생성(ADR "공용자재는 Unit 없이"). 이 판정을 화면에서 뒤집을 필요가 생기면 규칙 재검토.
2. **법인 기본 KOR**: 프로젝트에 법인칸이 비어 시범(검사기 국내)은 KOR. **베트남 호기 씨앗 시 `teams.entity` 기준 판정으로 정교화 필요**(후속).
3. **전체 285개 프로젝트 확산은 PASS 후**: 이번은 시범 005T2601만 실증. 확산은 게이트 통과 후.
4. **현황판 §4 등재·버전(z1053)·BAT는 병합 시**: 브랜치 단계라 배포 표준 절차는 main 병합 시 수행.
5. **일련번호 이력 UI**: V1은 활성 1건 + 개수만 표시. 전체 이력 열람 화면은 후속(WP-08 상태이력과 함께).

## 8. 다음 단계
게이트 판정(PASS/FAIL/BLOCKED) → 대표 승인 → main 병합(버전·BAT·§4)·배포 → LIVE 시범 확인 → 전체 프로젝트 확산 → WP-04(EBOM·PBOM, 호기 Baseline).
