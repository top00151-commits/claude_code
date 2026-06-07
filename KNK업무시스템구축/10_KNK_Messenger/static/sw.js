// KNK Messenger Service Worker — pass-through + 강제 네트워크
// v10-resub: SW 교체 시 푸시 구독 자동 복구(pushsubscriptionchange) — 알림 끊김 방지
// v16: message 채널 — 클라이언트 페이지에서 SW 에 알림 닫기 요청 (Samsung Internet 호환)
// v17: push 핸들러에서 같은 tag 기존 알림 명시적 close → 강제 교체 (2+개 누적 시 알림 안 닫히던 버그 수정)
// v18: 활성 방 + 페이지 포커스 시 push 알림 발생 자체를 막음 (모바일 OS 가 close 권한 안 줘서 — 닫는 대신 안 띄움)
// v19: explicit close 제거 (Chrome 에서 잔존 흔적 원인) + 알림 body 진단 prefix (지금은 제거됨)
// v20: URL 기반 활성 방 검출 + 페이지→SW 하트비트 — Chrome Android PWA 의 visibilityState 버그 우회
// v21: 서버측 active_room 차단으로 1차 방어 (sw 측 fallback 으로 이중 안전망 유지)
// v22: 알림 시스템 작업 종료 정리 — 진단 코드 제거 후 안정 버전
// v23: 같은 방 1팝업 + 배지 증가 — 메시지마다 유일 tag(room_X_msg_<ts>) 로 띄우고 옛것 close (실패)
// v24: 같은 tag 유지(서버 원본) + 첫 알림 body 보존 + renotify 로 사운드 매번 + setAppBadge 로 배지 증가
// v25: v24 의 body 보존 로직이 알림 자체를 막은 듯 → 단순 복원 (같은 tag + renotify + 매번 새 본문)
// v37: SW 버전 강제 상향 — 옛 SW 가 캐싱하던 클라이언트도 새 SW 활성화 시 모든 캐시 삭제 후 최신 HTML 수신 (대표 지시 2026-05-31 헤더 UI 반영 안 되던 문제)
// v38: AI 요약창 UI 개선 — 요약 본문 고정 높이(창 크기 고정) + 범위 버튼 선택 표시 유지 (대표 지시 2026-05-31)
// v39: 범위 버튼 고정 격자(라벨+3칸) — 선택해도 위치 안 바뀜 + 버튼 의미 설명/툴팁 + 높이 축소 (대표 지시 2026-05-31)
// v40: 공용 KNK 달력(date picker) — 납기·마감일·다운로드 기간 날짜선택을 커스텀 달력으로 교체(주말색·한국/베트남 공휴일 K/V 배지·오늘/선택 ring). holidays_kr_vn.json (대표 지시 2026-05-31)
// v41: AI 표식 — 원형 'AI' 배지(파랑=AI 가용/빨강=불가)를 AI 기능 5곳(요약·작성도움·번역·이력갱신·관리자 번역)에 적용. 이모지(🧠·✨·🌐)→배지 교체 (대표 지시 2026-05-31)
// v42: 번역 바 정리 — 칩 라벨 단축(국기+짧게), '자동 번역 ON' 안내를 연파랑 알약으로 슬림화, 모바일 '번역:' 라벨 숨김+OFF폭 축소(한 줄 유지) (대표 지시 2026-05-31)
// v43: 번역 칩 라벨을 영문 코드(🇻🇳 VN·🇺🇸 EN·🇨🇳 CN·🇰🇷 KR)로 — 언어 무관 통일, 더 짧고 한 줄 확실 (대표 지시 2026-05-31)
// v44: 번역 바 재배치 — 칩 순서 OFF·KR·VN·US·CN(한국 먼저), 영어=US, '뒤로'를 둘째 줄 오른쪽으로 이동(안내 알약은 왼쪽). 국기 유지 (대표 지시 2026-05-31)
// v45: 번역 바 미세조정 — OFF 칩을 다른 칩과 동일 크기, '번역:'→'번역'(콜론 제거), AI+번역 밀착(cl-trlabel), 안내 '...발송됩니다'→'...발송' (대표 지시 2026-05-31)
// v46: 번역 바 미세조정2 — AI+번역 간격 살짝(2→5px), 안내 글씨 더 작게(10px)+테두리 박스 제거(글씨만)+왼쪽 정렬해 위 AI와 좌측 라인 맞춤 (대표 지시 2026-05-31)
// v47: 모바일 번역 칩 균형 — 언어 칩(OFF·KR·VN·US·CN)을 flex 1 로 균등하게 늘려 가로폭 꽉 채움(한쪽 쏠림 해소) (대표 지시 2026-05-31)
// v48: 글씨 크기 6단계로 — '아주크게'(fs-5) 추가, 노안 배려로 본문 +10px(더크게보다 +4px)·UI +6px. 베/영/중 fs.4를 중간 단계로 재배치 (대표 지시 2026-05-31)
// v49: 글씨 크기 전체 연동 — style.css 333곳 + chat.html 162곳 + app.js 117곳의 미연동 font-size(>=11px)를 calc(+var(--fs-add-ui))로 일괄 변환(작은 아이콘/배지 제외). 사용자 목록은 본문폭(--fs-add). 이제 사용자목록·버튼·대화창 등 거의 전부가 글씨크기 선택에 반응 (대표 지시 2026-05-31)
// v50: 전체보기 방목록 종류별 강조 차등 — 프로젝트>그룹>채널>1:1 순으로 굵기+크기 차등(맑은고딕 중간굵기 한계로 크기도 함께). 행에 room-type-* 클래스 + 컨테이너 rl-all. 미읽음은 항상 굵게 유지 (대표 지시 2026-05-31)
// v51: WORKS 사용자 'W' 뱃지 — 사용자 목록에서 works_access=1 인 사람에게 AI 뱃지처럼 'W' 알약 표시(WORKS=KNK 빨강으로 AI 인디고와 구분). i18n badge.worksAllowed 4언어 (대표 지시 2026-05-31)
// v52: 게스트(고객사) 화면에서 우리직원 정보카드의 '사번'·'ID' 행 숨김(_meIsGuest 면 제외) + 사용자목록 AI/W/외부 뱃지를 오른쪽 묶음(.user-card-badges)으로 줄 맞춤(상태 글자 길이와 무관) (대표 지시 2026-05-31)
// v53: AI/W 뱃지 고정 2칸 배열 — AI=1열·W=2열, 한쪽 없으면 그 칸은 빈 칸(ub-off, visibility:hidden)으로 자리 유지해 행마다 정확히 정렬. 같은 폭(min-width 22px). 둘 다 없으면 칸 미생성 (대표 지시 2026-05-31)
// v54: AI 요약 비용절감 — 창 열 때 자동 요약 제거(저장본만 무료 조회), '요약하기' 버튼으로만 생성. 저장본은 방·범위별 공유. 보기는 멤버 전체(게스트 제외), 생성만 권한자(없으면 403 안내). (대표 지시 2026-06-01)
// v55: AI 요약 다이얼로그 하단 버튼 4개 글자 줄바꿈(요약하/기) 방지 — nowrap + 콤팩트 패딩 + flex-wrap(큰 글씨면 통째로 다음 줄) (대표 지시 2026-06-01)
// v56: AI 요약 창 크기 고정 — modal-content 높이 고정(min(86vh,640px)) + 본문 flex로 남는 공간 채워 안에서만 스크롤. 저장본 유무·meta 줄수·아이콘 눌러도 창 안 변함 (대표 지시 2026-06-01)
// v57: 상태표시 단순화(기본) — 접속하면 '🟢 접속' 하나로(컴퓨터/휴대폰 구분·(회사) 꼬리표 숨김). 관리자 설정 '상태 표시 — 기기·회사망' ON 시 기존처럼 표시. 표시만 바뀌고 내부 로직(푸시 라우팅·퇴근 자동복귀) 불변 (대표 지시 2026-06-01)
// v58: AI 모델 화면 변경 + 신형 파라미터 자동 대응 — 관리자 권한 탭에 'AI 모델' 입력+저장+🔌연결테스트 추가. 신형 OpenAI 모델(gpt-5.4-mini 등)은 max_tokens→max_completion_tokens 자동 전환(openai_create 래퍼). 모델 우선순위 환경변수>app_settings.ai_model>기본값(gpt-5.4-mini) (대표 지시 2026-06-01, WORKS 가이드)
// v59: 프로젝트방 목록 칩(회사명·관리번호·상태) 글씨 10.5px→12px + 글씨크기 설정 연동(calc+--fs-add) + 패딩 약간 키움. style.css 만. (대표 지시 2026-06-01)
// v60: 프로젝트 이력 정비 — (1) 이력 시트 정돈(메타→알약 pill·'요약' 라벨·좌측 녹색 액센트·안내 박스) (2) AI요약/이력 역할 명확화(버튼 title·메뉴 라벨) (3) WORKS 자동전송 선구현(기본 OFF 게이팅: env URL+관리자 토글) — 관리자 권한탭 '📤 WORKS 자동전송' 토글. (대표 지시 2026-06-01, 01 협의 발주)
// v61: 전달(Forward) 버그 3종 수정 — (1) 전달 창이 "두 번째"부터 안 열리던 버그(확인버튼 textContent 교체로 span#forwardCount 파괴 → innerHTML 저장/복원) (2) 전달받은 첨부 파일 403(미리보기·다운로드 불가) — serve_upload 권한을 'file_path 참조 메시지가 있는 방 멤버'까지 허용(전달본 포함, 이미 전달된 것도 즉시 복구) (3) 전달본/원본 삭제 시 공유 물리파일 동반삭제 방지(마지막 참조일 때만 os.remove). app.js + app.py. (대표 지시 2026-06-01)
// v62: 첨부 미리보기(라이트박스) 모바일 뒤로가기 지원 — 미리보기 열 때 history 한 칸 push, 휴대폰 뒤로가기(popstate)면 미리보기만 닫히고 보던 대화방 유지(이전엔 메신저가 통째로 나가짐). X·배경탭·ESC 닫기는 close() 를 한 번 감싸 history 일괄 정리(컨텍스트 메뉴와 동일 패턴). app.js 만. (대표 지시 2026-06-01)
// v63: 중국어(中文) 직원 화면 복원 — 어제 c18ef05 '중국어 고객사 전용 한정(직원 화면 제거)'을 해제. 직원 로그인(login.html)·설정 언어선택(chat.html)에 中文 버튼 복원, 작성기 🇨🇳 칩(app.js applyComposerLangUI)을 모든 방에서 표시(고객사 방 한정 제거). 고객사 입장(guest_login)·zh 456키·번역엔진은 그대로 유지. (대표 지시 2026-06-01)
// v64: (1)로그아웃 발견성 — 사이드바 ↩ 아이콘에 '로그아웃' 텍스트 병기(알약형, title.logout 키 재사용). (2)직원 초대 — 설정 다이얼로그에 '👥 초대' 별도 탭 신설: 메신저 접속 링크 QR + '메시지 복사(카톡)' + '링크만 복사'. 새 계정 생성 없음(직원은 사번 계정 보유), 기존 QR 라이브러리 재사용, 게스트는 탭 숨김. i18n 5키×4언어. chat.html/app.js/style.css/i18n.js. DB·백엔드 무변경. (대표 지시 2026-06-01)
// v65: 직원 초대 QR/링크 주소 수정 — '/' → '/login?staff=1'. 게스트 쿠키(knk_gt) 남은 기기에서 QR 찍으면 직원 로그인이 아니라 고객사(/g/토큰) 페이지로 튕기던 문제(2026-05-30 게스트기기 강제리다이렉트 설계 때문) → ?staff=1 우회로 항상 직원 사번 로그인. app.js _empInviteUrl 1줄. (대표 지시 2026-06-01)
// v66: 직원 초대 다국어 — 초대 탭에 언어 선택(한국어·Tiếng Việt·English·中文) 추가. 선택 언어로 (1)카톡 메시지 복사(4언어 맞춤·베트남 9999 안내 등) (2)QR/링크에 &lang=<선택> 부착. i18n.js 초기화가 URL ?lang= 을 최우선 반영 → 그 QR로 들어온 로그인창이 선택 언어로 열림(localStorage knkmsg.lang 저장). 언어선택은 초대용만(대시보드 UI 언어 불변). chat.html/app.js/i18n.js/style.css. DB·백엔드 무변경. (대표 지시 2026-06-01)
// v67: 방 헤더 버튼 — 컴퓨터에서 '많이 쓴 순' 개인 맞춤 정렬. 각 직원 기기에 클릭 횟수 누적(localStorage knkmsg.headUsage) → 자주 누른 상위 3개만 아이콘+한글글자로 노출, 나머지는 ⋮ 더보기 메뉴로(나가기도 메뉴로, 휴대폰과 동일). 직접클릭+더보기메뉴클릭 둘 다 카운트(헤더 위임 리스너+방설정 보강). 처음엔 기본순서(요청·사진·AI요약…). 휴대폰은 기존 그대로(아이콘줄 숨김+⋮메뉴, 한글설명 있음). chat.html(hb-lbl 라벨)/app.js(usage·정렬·카운트)/style.css(컴퓨터 상위3+⋮메뉴). DB·백엔드 무변경. (대표 지시 2026-06-01)
// v68: 헤더 방향 전환 — '많이 쓴 순 상위3 글자'(v67) 되돌리고, 아이콘은 원래대로 다 보이게(라벨/상위3/재정렬 제거). 대신 ⋮ 더보기 메뉴 각 항목에 '상세 설명' 추가(제목+한 줄 설명: 공지·요청·스레드·AI요약·이력·중요·사진·엑셀·초대·정보수정·방설정·나가기) — 컴퓨터·휴대폰 공통. 컴퓨터는 우측상단 ⋮ 더보기로 설명 확인(나가기도 메뉴에). app.js(적응형 제거)/chat.html(메뉴 설명)/style.css(라벨숨김+메뉴 hmm-text/hmm-d). DB·백엔드 무변경. (대표 지시 2026-06-01)
// v69: 컴퓨터 헤더의 ⋮ 더보기 버튼 이름을 '설명'으로 변경(아이콘 ⋮→ⓘ) — 컴퓨터는 아이콘이 다 보이므로 '더보기'가 아니라 기존 아이콘 설명. style.css 만(컴퓨터 head-more ::before/::after). 휴대폰 ⋮ 메뉴는 그대로. (대표 지시 2026-06-01)
// v70: 휴대폰 필터 칩(전체·프로젝트·1:1·그룹·채널·내 요청·멘션) 7개가 한 줄에 다 보이게 가로폭 축소 — 여백 9→5px, 간격 3→2px, 글자 11.5→10.5px, 개수배지 14→13px (≤720px 만). 컴퓨터 화면은 그대로. style.css 만. DB·백엔드 무변경. (대표 지시 2026-06-01)
// v71: 휴대폰 필터 칩을 flex:1 균등 분배로 가로 전체 꽉 채움. 칩 글자 10.5px '고정'(글씨크기 설정 --fs-add-ui 분리) → 글씨 작게=오른쪽 빈공간X, 크게=오른쪽 넘침X, 배치 항상 동일. (≤720px 만). 컴퓨터 화면은 그대로. style.css 만. DB·백엔드 무변경. (대표 지시 2026-06-01)
// v72: 설정창 — ①언어 버튼(한국어·Tiếng Việt·English·中文) 4개 한 줄 균등(flex:1, 라벨 위로) ②탭(알림·초대·보안·사용법·관리자) 한 줄 강제(white-space:nowrap·word-break:keep-all) 5개 flex:1 균등 → 한글 2열로 안 깨짐. 둘 다 글자 고정(글씨크기 --fs-add-ui 분리)으로 배치 항상 동일. style.css 만. DB·백엔드·HTML·JS 무변경. (대표 지시 2026-06-02)
// v73: 말풍선 우클릭/롱프레스 '텍스트 복사' — 선택된 텍스트가 있으면 그 선택분만 복사(키보드 Ctrl+C 와 동일), 선택 없으면 말풍선 전체. 메뉴 열리는 시점에 선택을 미리 캡처(클릭 시 선택 풀림 방지) + 그 말풍선 안의 선택만 인정. app.js 만. DB·백엔드·HTML·CSS 무변경. (대표 지시 2026-06-02)
// v74: 파일·멘션 3건. ①파일 다운로드 시 '보낸 원본 파일명'으로 저장 — 서버 ?dl=1 모드가 Content-Disposition(UTF-8)으로 DB file_name 지정(휴대폰서 a.download 무시 대비). 같은 이름은 브라우저가 자동 (1). 받기 링크 4곳+이미지 저장에 ?dl=1. ②멘션 방향키 이동 시 선택항목 scrollIntoView(보이는 범위 밖도 따라감). ③멘션은 @가 '맨 앞/공백 뒤'일 때만 발동(이메일 top0015@... 차단) — 입력 자동완성+pickCurrent+렌더 정규식 모두. app.py(serve_upload dl)+app.js. DB 무변경. (대표 지시 2026-06-02)
// v75: 멘션 2건. ①@ 만 입력 시 방 참여 인원 '전체' 표시(기존 8명 제한 list.slice(0,8) 제거) + 이름순 정렬 → 스크롤·방향키로 모두 찾기. ②'내 멘션'에서 항목 클릭 시 해당 메시지로 점프(기존엔 방 맨 아래로 감) — 방 열 때 강제 최하단 보정(_forceMessagesToBottom 250ms 등)이 점프를 덮어쓰던 문제를 _userTouchedMessages=true 로 차단 후 scrollIntoView(+못 찾으면 재시도). app.js 만. DB·CSS 무변경. (대표 지시 2026-06-02)
// v76: 대화창 스크롤이 위로 올렸다 다시 바닥으로 튕기던 문제 수정. updateViewport()의 '바닥 150px 이내면 맨 아래로 스냅'이 입력창 포커스 중 250ms 폴링(_focusPollTimer)으로 계속 실행 + 컴퓨터는 방 열면 입력창 자동포커스 → 조금 올리면 스냅 복귀('올라갔다 내려옴'). 자동 스냅 2곳(updateViewport, 컴포저 ResizeObserver)에 '!_userTouchedMessages'(휠·터치 중이면 건드리지 않음) 가드 추가. 새 메시지 자동하단·키보드 따라가기는 별도 경로라 유지. app.js 만. DB·CSS 무변경. (대표 지시 2026-06-02)
// v77: '내게 온 멘션' 클릭 시 해당 메시지에 '정확히' 안착. v75 는 한 번만 scrollIntoView 해서, 점프 직후 첨부 이미지(PDF·사진)가 lazy 로드되며 위쪽 높이가 늘어 위치가 밀렸음 → _gotoMention 의 점프를 ~1.6초간(120ms×13) 여러 번 'block:center' instant 재보정으로 교체(이미지 다 뜬 뒤에도 가운데 안착) + 강조 1회. app.js 만. DB·CSS 무변경. (대표 지시 2026-06-02)
// v78: 멘션 점프 시 대화창이 3~4번 깜빡이던 문제 수정(v77 부작용). v77 은 1.6초간 13번 즉시 재보정 → 이미지 뜰 때마다 툭툭 튐. 변경: '즉시 1번 이동' 후 이미지 로드가 멈춘 뒤 '딱 1번 부드럽게' 재보정(디바운스 120ms) + 900ms 안전망 1회, 점프 직후 ~2초 창 안에서만(나중 스크롤 시 늦게 뜨는 이미지가 끌어당기지 않게). 정확 안착 유지 + 깜빡임 최소화. app.js 만. DB·CSS 무변경. (대표 지시 2026-06-02)
// v79: 멘션 점프 깜빡임·위치실패 '근본 원인' 수정. 진짜 원인 = 컴퓨터에서 방 열 때 입력창 자동포커스(openRoom)→onInputFocus 가 50/150/300/500/800/1200ms 6개 타이머로 els.messages.scrollTop=scrollHeight(맨아래로) 강제 + 250ms 폴링 → 멘션 점프를 1.2초간 계속 바닥으로 덮어씀(v77/v78 재보정과 싸워 깜빡+실패). 해결: 점프 모드(_jumpTargetMsgId) 도입 → openRoom 이 ①입력창 자동포커스 안 함 ②_forceMessagesToBottom 하단강제 skip, updateViewport/ResizeObserver 하단스냅도 가드. _gotoMention 은 깔끔히 1회 이동+이미지 reflow 시 1회 보정, 2.5초 후 플래그 해제. app.js 만. DB·CSS 무변경. (대표 지시 2026-06-02)
// v80: 클립보드 '파일 붙여넣기(Ctrl+V)'를 바로 보내지 말고 '보낼 첨부'에 담기 → 보내기 버튼/엔터로 전송(클립 버튼과 동일). paste 핸들러를 uploadFiles(즉시전송)→_stageFiles(기존 담긴 것에 추가)로 변경, 파일일 때만 preventDefault(텍스트 붙여넣기는 그대로). app.js 만. DB·CSS 무변경. (대표 지시 2026-06-02)
// v81: 화면잠금 비번 해제 확인. 비번 해제는 지문 등록과 무관하게 동작하는 구조(verify_password=로그인과 동일 check_password_hash) 확인. 실패 시 진짜 원인이 가려지던 문제 보완: ①잠금화면 입력칸에 👁 보기 토글 추가(가려진 비번 오타 확인) ②해제 오류를 서버오류/네트워크/오타로 구분 표시(기존엔 무조건 '비번 틀림') + r.ok·credentials 견고화 ③잠글 때마다 가림(●)+👁 초기화. chat.html(👁)+style.css(.lock-pw-form .pw-wrap flex)+app.js. DB·백엔드 무변경. (대표 지시 2026-06-02)
// v82: 컴퓨터 헤더 'ⓘ 설명' 버튼 라벨 → '메뉴상세설명' (대표 지시 2026-06-02). style.css 가상요소(::after content)만 변경 — 정적 캐시 갱신용 버전업.
// v83: 단독창 대화 글씨 메인과 통일(messages zoom 0.82→1) + 대화창 접기/펼치기(데스크탑) 추가 (대표 지시 2026-06-02). chat.html+style.css+app.js — 정적 캐시 갱신용 버전업.
// v84: 대화창 접기/펼치기 버튼을 사이드바 아이콘 → 분리선 위 길쭉한 화살표 탭(#chatCollapseBtn ❮/❯)으로 이동 (대표 지시 2026-06-02). 정적 캐시 갱신용 버전업.
// v85: 접힘 동작 정정 — 정보창(방목록) 폭은 그대로 두고 오른쪽 대화방만 접어 숨김(정보창 안 넓힘). 탭은 분리선 자리 고정 (대표 정정 2026-06-02). 정적 캐시 갱신용 버전업.
// v86: 접으면 창(window)을 방 목록 폭으로 줄여 오른쪽 빈 영역 자체를 제거(window.resizeTo), 펼치면 원래 너비 복원 (대표 재정정 2026-06-02). 설치형 단독창 전용. 정적 캐시 갱신용 버전업.
// v87: 접힘 시 방 목록을 1fr(창 전체폭)로 채워 잔여 띠 제거 + 분리선 숨김 + 창 넓히면 목록이 넓어짐. JS: class 적용 전에 사이드바 폭 측정(축소 폭 오류 수정) (대표 재재정정 2026-06-02). 정적 캐시 갱신용 버전업.
// v88: 접힘 전환 중 정보창이 잠깐 커졌다 줄어드는 현상 제거 — 사이드바를 현재 폭으로 고정한 채 창 먼저 축소→class→해제(현재 화면 그대로 접힘) (대표 재재재정정 2026-06-02). 정적 캐시 갱신용 버전업.
// v89: 접힘=정보창 고정폭 유지(1fr 제거→커짐 완전 차단) + 펼칠 때 보던 스크롤 위치 복원 + 접힘 중 방 1번클릭은 선택만(자동펼침 제거, 더블클릭=새 창) (대표 재재재재정정 2026-06-02). 정적 캐시 갱신용 버전업.
// v90: ①필터 칩 모바일 규칙을 pointer:coarse 로 게이트 → 접힘(좁은 데스크탑 창)에서 칩 크기 안 변함 ②창 축소 완료(resize) 후 방 목록을 창 폭에 맞춰 채워 오른쪽 잔여 띠 제거(부풀림 없음) (대표 지시 2026-06-02). 정적 캐시 갱신용 버전업.
// v91: 접힘 '정보창 조금 커짐' 근본수정 — .chat-app 데스크탑 min-width:470px 를 접힘 시 0 으로 해제(창이 정보창 폭까지 줄어듦, fit 땜질 제거) + 새창(분리창) 카톡 크기(400×700)·메인창 위 중앙 + 솔로창 ⓘ 글자깨짐 수정 + 새버전 안내창 3배 크게(세로배치) (대표 지시 2026-06-02). 정적 캐시 갱신용 버전업.
// v92: 접힘 시 대화창이 오른쪽에 찌그러져 보이던 것 수정 — grid 의 '대화창 칸'을 0 으로 강제. 지난 v91 에서 1fr 0(대화칸 0) 규칙을 빼면서 대화창이 1fr 칸에 다시 드러난 게 원인(display:none 만으론 안 가려졌음). 정보창 칸은 var(--sidebar-width) 고정 그대로(안 커짐) (대표 지시 2026-06-02). 정적 캐시 갱신용 버전업.
// v93: 대화창 숨김 3중 안전망 — _applyCollapsedUI 에서 els.chatPane.style.display 도 인라인으로 none 설정(CSS 가 어디서 덮여도 확실). (대표 지시 2026-06-02). 정적 캐시 갱신용 버전업.
// v94: 접기 = 방 목록이 빈 자리 채움(grid 1fr 0) + 탭은 창 오른쪽 끝 고정(좌우로 안 움직임). 창 크기 조절(resizeTo)은 크롬이 보안상 차단 — 창 줄이기 포기 (대표 선택 2026-06-02). 정적 캐시 갱신용 버전업.
// v95: 접은 뒤 창을 슬림하게(가로 ≈350px) 끌 때 머리줄(대화방만들기+WORKS+아이콘4) 압축 — 좁은 폭(≤480px·마우스)에서만 여백·간격 축소해 글자 보존 + 가로 스크롤 방지 (대표 지시 2026-06-02). 정적 캐시 갱신용 버전업.
// v96: 접기 = 메신저 본체를 '딱 350px 슬림 컬럼' 고정(대표 선택). .chat-app.chat-collapsed 에 width:350px+max-width:100%(창<350 가로스크롤 방지)+grid 1fr 0. 창이 더 넓으면 오른쪽은 빈 바탕(body #f6f7f9), 창을 350 으로 끌면 딱 맞는 띠. 머리줄 압축은 접힘 시 항상 적용(폭 늘 350)으로 변경. 펼치기 탭은 본체(350) 오른쪽 끝. 창 자체는 resizeTo 차단으로 자동축소 불가(사용자가 끌어 맞춤) (대표 지시 2026-06-02). 정적 캐시 갱신용 버전업.
// v97: 접기/펼치기 화살표 탭 위치 복구 — 펼침 시 '창 맨 오른쪽 끝'(잘 안 보이고 화면 잘림)에 있던 것을 '방 목록↔대화창 분리선 위'(대표 원래 요청 '구분라인에 화살표')로 이동. 빨강 화살표+테두리로 강조(잘 보이게), 살짝 크게(22x76). 접힘 시엔 350px 패널 오른쪽 끝(펼침 분리선과 거의 같은 자리) → 항상 같은 곳에서 찾음. z-index 62 (대표 지시 2026-06-02). 정적 캐시 갱신용 버전업.
// v98: ★자동 업데이트★ — 새 버전 감지 시 (작성 중·창 열림 아니면) 캐시 비우고 자동 새로고침(app.js _checkAppVersion). 배너 '지금 적용'·헤더 🔄 모두 SW해제+전체캐시삭제+캐시버스트reload(_nukeCaches/_reloadFresh)로 통일 → 이제 옛 CSS/JS 안 남음. 무한루프 방지(같은버전 90초 가드). 이 캐시문제 영구 해결 (대표 지시 2026-06-02). 정적 캐시 갱신용 버전업.
// v99: 접힘 = 350px 고정 대신 '방 목록이 창을 꽉 채움'(고정폭 제거, grid 1fr 0)으로 — 창 폭이 얼마든 오른쪽 여백 0. 창을 크롬 최소폭까지 좁게 끌수록 방 목록도 같이 좁아져 슬림 띠. 머리줄 압축은 좁은 창(≤480px)에서만 작동하게 환원(이제 접힘폭=창폭이라 뷰포트 기준이 맞음) (대표 결정 2026-06-03: 여백 없애려 350고정 폐기·창에 맞춰 채움). 정적 캐시 갱신용 버전업.
// v100: 아바타 상태 표시 폐지 — 아바타는 사진/이름 첫글자(신원)만, 상태는 사용자목록 이름옆 글자로 확인. _statusFillHtml→null(상태색 원+이모지 덮기 제거), 1:1 방 아바타=상대방 _avatarBody(사진/첫글자), 코너 상태점(.status-dot) CSS 숨김. 부담↓·식별↑ (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v101: 개인 아바타 셀프 등록 — 인사카드 사진(관리자 avatar_url)과 별개로 직원이 본인 아바타(self_avatar)를 직접 등록/변경/삭제. 헤더 좌상단 아바타 클릭→메뉴. 표시 우선순위 개인>인사카드>이름첫글자(_selfAvatarMap). 헤더 아바타 상태채움 버그(③) 제거. 게스트 제외. DB self_avatar 컬럼 + /api/me/avatar API + self_avatar_changed 소켓 (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v102: 상태창 '🟢 출근(자동)' 카드 일단 비활성화 — 보이되 클릭 안 됨(disabled) + 흑백(grayscale+opacity) 처리. 없애진 않음. 오프라인=로그아웃 표시는 그대로 유지(정상). 상태로직·백엔드 변경 없음 (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v103: 휴대폰 길게누르기 시 OS 텍스트선택 막대(복사·번역·모두선택·웹검색·공유)가 우리 앱 메뉴와 겹쳐 뜨던 문제 해결(A안). 말풍선 기본 user-select:none+touch-callout:none(휴대폰=앱 메뉴만), .lp-selectable 은 text 유지(더 길게=부분선택 2단계), @media (pointer:fine) 로 PC는 자유선택 유지(05-27 지시 PC한정). 메뉴 '📋 복사'로 전체복사 가능 (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v104: 길게누르기 메뉴에 '✂️ 텍스트 선택 복사' 추가 — 📋 텍스트 복사=말풍선 전체, ✂️ 텍스트 선택 복사=부분만 선택해 복사(말풍선 선택모드 .lp-selectable 전환+전체선택→손잡이로 범위 조정, 기존 2단계 코드 재사용). 휴대폰 기본 선택UI는 이 항목 누를 때만 (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v105: 텍스트 선택 복사 보완 — ① 선택영역 강조색(::selection 노랑#ffd21e+검정, 파란/회색 말풍선 양쪽 가독성) ② '텍스트 선택 복사' 누르면 말풍선을 화면 가운데로 스크롤(scrollIntoView center)해 OS 선택막대가 선택글을 안 가리게 (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v106: 검색 통합 우선순위 — 검색창이 방 이름·사용자 이름도 찾게(기존엔 메시지+프로젝트만). /api/search 에 방이름(내 멤버방)·사용자이름(게스트제외) 쿼리 추가, 반환 우선순위 방→사람→프로젝트→대화내용. 프론트 렌더러에 💬방·👤사람 타입 + 클릭(방=열기/사람=정보보기/메시지=방이동) (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v107: 접힘(슬림) 상태에서 방 열기 시 새 창(solo 팝업) — 접힘 땐 대화칸 0px라 그 자리에 열면 안 보이던 문제. _openRoomOrPopout 헬퍼: 접힘+솔로아님이면 /chat?solo=1&room=N 을 window.open(기존 팝업코드 재사용), 펼침이면 그 자리. 검색 결과·방 목록 클릭 둘 다 적용 (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v108: 사이드바 상단 검색창 슬림화 — 위아래 여백만 절반(.search-box padding 10→5px, input padding 8→4px), 글자 크기 유지 (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v109: 사내 메신저 이용·보안 동의서 팝업 — 직원 첫 로그인 + 약 100일마다 전체차단 모달로 동의서(한국어+베트남어) 표시, 동의해야 사용 가능. 게스트 제외, '동의 안 함'=로그아웃, 끝까지 읽어야 버튼 활성. consent_doc.py + app.py(consent_agreements 테이블+API) + app.js + chat.html + style.css (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v121: 방 목록 맨 위 고정 "같은 칸" — 내메모장 + 메신저불편사항 두 방을 좌우 2칸(아바타 없음)으로 합쳐 최상단 고정. (신고)채널 이름을 "메신저불편사항" 으로 변경 (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v122: 상단 "같은 칸" 높이 최소화(여백 축소) + 제목 중앙정렬 → 대화방 목록 더 많이 노출. (신고)채널 이름 "메신저불편사항"→"메신저 불편 신고 여기에" (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v123: (철회됨) 새 창에서 ⋮'더보기'를 숨겼던 변경 — 그 ⋮ 는 대표님이 만드신 '메뉴 상세 설명' 기능이라 숨기면 안 됨. v124 에서 원복.
// v124: v123 원복 — 새 창(solo)에서도 ⋮ '메뉴 상세 설명' 버튼 그대로 노출 유지 (대표 지시 2026-06-03: 기능을 없애지 말고 새 창에서 내용이 잘 뜨도록 고쳐야 함). 정적 캐시 갱신용 버전업.
// v125: 새 창 '메뉴상세설명' 버튼 깨짐 수정 — solo head-btn(28px·15px) 규칙이 head-more 의 font-size:0(⋮숨김)을 덮어써 'ⓘ⋮' 로 깨졌던 것 → head-more 만 auto폭·font-size:0·'ⓘ 메뉴상세설명' 한 줄로 정상화 (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v126: 동의서 제목 줄바꿈 수정(.consent-head h2 word-break:keep-all → '확인서' 글자 중간서 안 끊김) + 동의서 팝업 잠금(consent_doc CONSENT_TEST_USERNAMES=[] → 대표님 포함 아무에게도 안 뜸, 기능 보존) (대표 지시 2026-06-03). 정적 캐시 갱신용 버전업.
// v127: 상단 고정칸 '메신저 불편 신고 여기에' 아이콘 변경 🛠(공구)→🙋(손들기) — 직원이 손들고 의견 제기하는 이미지로 (대표 지시 2026-06-04). app.js _bugLabel 1곳. 정적 캐시 갱신용 버전업.
// v128: 사용자 탭 이름 검색 시 매칭 사용자를 부서 트리 대신 '평탄한 목록'으로 맨 위에 표시(+부서명 칩) — 박지은 등 하단 부서 사람도 검색 즉시 상단에 보임 (대표 지시 2026-06-04). app.js renderUserList. css .user-dept-chip. 정적 캐시 갱신용 버전업.
// v129: 방 설정 권한 정비 — 방 이름 변경=방장만(관리자는 '강제 변경'+방장 통보 기록), 방 사진(아바타)=방장+관리자(기존 관리자 전용), 채널삭제에 '🔒 관리자 전용' 배지, 관리자 강제 변경/삭제 시 '방장에게 통보' 안내 (대표 지시 2026-06-04). app.js _renderRoomSettings · app.py rename/avatar 가드. 정적 캐시 갱신용 버전업.
// v130: 방 설정 후속 수정 — (버그) 채널에선 _my_room_role 이 관리자(ceo)를 effective 'host'로 줘서 관리자가 방장 아닌데도 방장용 '저장' UI를 받던 문제 → '방 이름 변경'만 '실제 방장'(멤버 role=host 본인=iAmRealHost)으로 판단, 관리자는 강제변경. 채널삭제 배지 '관리자 전용'→'관리자·만든 사람'(만든 사람도 삭제 가능, 오표기 정정). 통보문구도 실제 방장 기준 (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v131: 여러 방 동시 공유 [Phase 2 화면] — 입력창 📢 버튼 → 방 선택·검색 + 공유묶음 모달(broadcast 전송), 받는 쪽 '📢 여러 방에 공유된 글' 배지(share_count>=2). app.js openMultiShare + msgHtml shareCard · chat.html 버튼 · css .ms-*/.share-card (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v132: 여러 방 공유 — '현재 방(작성 중)'도 자동 포함. 모달 열 때 현재 방 자동 체크 + 맨 위 '현재 방' 라벨, 묶음 불러와도 현재 방 유지, 보낸 뒤 입력창 비움 (대표 지시 2026-06-04). app.js openMultiShare · css .ms-cur. 정적 캐시 갱신용 버전업.
// v133: 여러 방 공유 목록 조정 — 내 메모장(self) 포함(저장용으로 보낼 수 있게), '메신저 불편 신고' 채널은 제외 (대표 지시 2026-06-04). app.js openMultiShare sendable 필터 + 메모장 이름 표시. 정적 캐시 갱신용 버전업.
// v134: 여러 방 공유 아이콘 📢(확성기→공지와 헷갈림)을 👥(사람 여럿)로 변경 — 입력창 버튼·모달 헤더·받는쪽 배지·푸시 제목 전부 통일 (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v137: 공유한 방 목록 팝업에 '✏️ 작성한 방'(글 쓴 방) + '📍 지금 방'(보고 있는 방) 표시 → 다른 방에서 눌러도 출처/현위치 한눈에. app.py share_origin_room_id 컬럼·broadcast 저장(origin_room_id)·share_targets 응답 is_origin/origin_room_id, app.js openMultiShare origin 전송·showShareTargets 뱃지, css .share-tag (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v138: 멤버/초대 목록 — 베트남 직원 이름 한국어 모드 병기(_dispName) + 초대·새방 picker 본사/베트남법인 묶음 구분. app.js renderMemberRow 이름 _dispName, _groupedPickerHtml(_corpOfDept 기준)·openNewRoom·openInviteDialog·검색 빈그룹 숨김, css .pick-group-head (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v139: 카톡식 날짜 구분선 + '여기까지 읽었습니다' 읽음 경계. 날짜 바뀌는 자리에 가운데 띠(📅 2026년 6월 4일 목요일·현지화), 진입 시 첫 안읽음 앞에 경계 줄, 안읽음 있으면 그 줄로 스크롤(없으면 하단). 시간 인라인 날짜 제거→시:분만. app.js _dateDividerHtml/_unreadDividerHtml/_buildMessagesHtml·openRoom 진입 last_read 스냅샷·_scrollMessagesToUnread, css .date-divider/.unread-divider (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v140: 내 상태 — 회의중·외근 등 수동상태를 풀 방법이 없던 문제 해결. 상태 카드 맨 끝에 '💼 업무' 추가(누르면 online 저장→자동표시 규칙이 접속/컴퓨터/휴대폰으로 환산=수동상태 해제). 흑백 '출근(자동)' 카드는 유지. app.js STATUS_INFO work + openStatusDialog _pickerOrder/라벨(다국어)/_highlightKey/_SELECTABLE_STATUSES + _saveStatus work→online (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v141: ①'메신저 불편 신고' 채널 AI번역 기본 OFF(자동번역 안 켜짐, 직접 켜면 manual 로 유지) — app.js computeAutoTranslateLang 가 BUG_ROOM 이면 "" 반환. ②방 목록 상단 '내 메모장+불편신고' 합친 칸을 스크롤에서 제외하고 항상 맨 위 고정(sticky) — css .room-combo-cell position:sticky·top:0·배경 var(--surface) (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v142: 방 목록 상단 고정 칸 위 빈 띠 제거 — .room-list padding-top(8px) 때문에 스크롤 시 그 틈으로 아래 방이 비쳐 올라오던 것 → padding: 8px 0 → 0 0 8px 로 윗여백 제거, 합친 칸을 맨 위에 딱 붙임 (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v143: 방 목록 상단 고정 칸(내메모장+불편신고) 여백 최소화 — 칸 패딩 8px 8px 6px→2px 6px 3px, 반쪽 버튼 패딩 4px 10px→2px 8px(radius 9→7) 로 높이 줄여 리스트 더 보이게 (대표 지시 2026-06-04). 정적 캐시 갱신용 버전업.
// v146: 스레드(답글)에서도 사진·파일 첨부·표시·다운로드 — 스레드 입력창 📎 추가, 부모·답글에 사진 미리보기(클릭 확대)·파일 받기, 메인 업로드 통로(/api/upload) 재사용 + thread_parent_id 분기 (대표 지시 2026-06-04). app.py·app.js·style.css 변경.
// v147: 스레드 AI 요약 버튼 아이콘 🧠(뇌 이모지)→ 표준 AI 배지(.ai-avatar/.ai-mark) 교체 — chat.html 표준화(2026-05-31) 때 누락됐던 JS 동적 버튼 + 요약창 머리말 2곳 일관화 (대표 지시 2026-06-04). app.js만.
// v148: ①스레드 엑셀에 실제 사진 임베드(파일명만→썸네일 '사진'열, app.py) ②스레드 첨부도 메인처럼 — 📎·붙여넣기(Ctrl+V)·끌어다놓기 → '보낼 첨부'에 먼저 담고 보내기/Enter 전송(app.js+css) (대표 지시 2026-06-04).
// v149: 멤버 초대(+새 방 만들기) picker 를 본사/베트남법인 '책갈피(탭)'로 분리 — 한 리스트 대신 탭 전환, 탭별 인원수, 검색은 활성 탭 안에서, 선택은 탭 바꿔도 유지(합산 초대) (대표 지시 2026-06-05). _groupedPickerHtml 탭 구조 + _wireUserPickerSearch 탭 인식 + css .pick-tabs/.pick-tab/.pick-pane.
// v150: 첨부 사진을 PC에서 '별도 새 창' 전용 뷰어로 열기 — 카톡처럼 사진 보면서 메신저 동시 사용 (대표 지시 2026-06-05). 확대/축소(+/−·휠)·맞춤·드래그 이동·저장·앨범 이전/다음·Esc 닫기. 휴대폰(터치)은 기존 전체화면 미리보기 유지. 메인 타임라인·스레드 사진 클릭에 _viewImage 적용.
// v151: 메시지(사진·파일·글) 우클릭 메뉴에 '외부 앱으로 공유' 추가 — 카톡 등으로 전달. 휴대폰=OS 공유시트(navigator.share, 사진·파일째), PC=사진은 클립보드 복사 후 Ctrl+V·글은 텍스트 복사·파일은 다운로드. _shareMessageExternal + _toast/_copyImageToClipboard 등 (대표 지시 2026-06-05).
// v152: 멤버 초대 창 정리 (대표 지시 2026-06-05) — 본사/베트남법인 탭을 sticky→고정 헤더로 빼고 목록만 안쪽 스크롤(.pick-scroll)해서 탭 위로 명단 비침·여백 제거 + 초대 모달을 flex 레이아웃(외곽 스크롤 제거)으로 바꿔 취소·초대 버튼이 스크롤 없이 항상 보이게.
// v153: 방 목록 상단 고정 칸(내 메모장+불편신고)에 스크롤되는 리스트가 비쳐 올라오던 버그 수정 — .room-combo-cell:hover 배경이 transparent 라 마우스 올린 채 스크롤하면 뒤 리스트가 투과돼 보였음 → var(--surface) 불투명 유지 (대표 지시 2026-06-05).
// v154: 방 목록 상단 고정 칸에 아래 그림자 추가 — 목록이 그 칸 '아래로' 확실히 스크롤되게(칸에 포함돼 보이지 않게) (대표 지시 2026-06-05). v153 호버불투명 + 본 그림자로 비침/포함 인상 제거. (대표가 v153 적용 전 옛 캐시를 보던 것으로 추정 — 모사 렌더 확인상 현재 코드는 비침 없음)
// v155: 방 목록 스크롤바가 상단 고정 칸 옆까지 올라오던 문제 해결 (대표 지시 2026-06-05, 진짜 원인). 고정 칸이 .room-list(overflow auto) 안에 있어 스크롤바가 칸 옆에도 생겼음 → .room-list 를 스크롤 없는 flex 컨테이너로, 명단만 .room-scroll(overflow auto)로 감싸 스크롤바를 명단에만. 고정 칸은 flex 헤더(sticky 해제). app.js(명단 .room-scroll 래핑)+css.
// v156: 검색창 placeholder 깔끔하게 — '🔍 검색 (from:이름 in:방 has:파일 before:날짜)'(산만) → '🔍 이름·방·내용 검색'. 고급 필터 문법은 옆 ⓘ 도움말에 이미 다 있어 중복 제거 (대표 지시 2026-06-05). chat.html placeholder + i18n ph.search 4언어.
// v157: 중국어(zh) UI 누락 69키 일괄 보강 (대표 지시 2026-06-05 다국어 누락 전수 1단계). zh 만 475키로 핵심 메뉴(탭·필터·스레드·내보내기·AI/채널 권한·게스트)가 한국어로 보이던 문제 → i18n.js zh 블록에 69키 삽입(기존 zh 용어 일관). 4언어 각 544 완전일치 검증.
// v158: 다국어 누락 전수 2단계 — chat.html 헤더 버튼·더보기메뉴·작성기 툴팁/라벨 하드코딩 한국어를 data-i18n 키화. i18n.js 4언어 각 +61키(605). i18n 적용기에 data-i18n-aria 지원 추가. chat.html data-i18n 키 337개 전부 정의 확인.
// v159: 다국어 2단계-B — 사용자 공통 다이얼로그 키화(상단바 툴팁·이모지검색·첨부 미리보기 다이얼로그). 동적항목은 JS(Phase3)로 분리. i18n.js 4언어 각 +8키(613).
// v160: 다국어 2단계-C — 비밀번호변경·내정보 다이얼로그 키화. 중국어 정책 변경(대표 지시: zh 는 고객사 화면만, 회사에 중국직원 없음) → 내부 전용은 ko/vi/en 3개만. i18n 정책: ko=vi=en 완전일치, zh 는 고객용 부분집합.
// v161: 내 정보 다이얼로그 관리자 필드 키화(표시명·관리자권한·활성·비번초기화·위험구역·삭제·비번변경, ko/vi/en). 복잡 중첩HTML 2곳(권한 라벨·위험구역 다행안내)은 관리자만 드물게 봐서 한국어 유지.
// v162: 다국어 3단계(app.js 동적문구) batch1 — 전역 헬퍼 _kt(key,한국어폴백) 추가 + 메시지 외부공유 toast 9개 키화. 공유는 고객도 쓰므로 4개 언어(zh 포함). 브랜드명은 vi/en/zh 중립표현.
// v163: 사이드바 탭 버그 수정 — 사용자 탭에서 방목록·필터바가 안 숨겨지고 명단과 겹쳐 보이던 문제. 원인=v155 .room-list{display:flex}가 [hidden]{display:none}(동급 우선순위)을 무력화. 재발대책=전역 [hidden]{display:none!important}.
// v164: AI 번역 사용량 본사/베트남법인 분리 — 화면 표 위에 책갈피 탭(법인별 소계) + 엑셀 2시트 분리. 백엔드 is_vn 플래그 추가. 관리자 전용 한국어.
// v165: AI 사용량 베트남 직원 이름 '베트남어 (한국식발음)' 병기(화면+엑셀) — 표준 _dispName 규칙. 백엔드 usage API·export 에 display_name_vn 추가.
// v166: 대화방 첨부 표기 컴팩트 — 이미지 280x320→140x160(절반, 클릭시 미리보기로 크게), 파일 카드 패딩·아이콘·글씨·받기버튼 축소 (대표 지시 2026-06-05).
// v167: 파일 카드 더 작게 — 받기 버튼 줄바꿈 방지(nowrap+flex-shrink, 세로로 길쭉해지던 문제) + 아이콘 26→22·여백·글씨 추가 축소 + 카드 max-width 280 (대표 지시 2026-06-05 더 작게).
// v168: 파일명 최대 2줄로 제한 — 넘치면 … 말줄임(-webkit-line-clamp:2) (대표 지시 2026-06-05, 3줄까지 늘어나던 문제).
// v169: 연속 메시지 묶기(카톡식) — 같은 사람 5분 이내 연속 메시지는 아바타·이름 1회 + 중간 시간/읽음 숨기고 묶음 끝에만 시간 + 간격 좁게. 5분 초과/다른 사람이면 새 묶음. 전체렌더·실시간추가·단일갱신 모두 반영 (대표 지시 2026-06-05).
// v170: 연속 메시지 묶기 더 확실하게 — 묶음 내 말풍선 맞닿게(margin -2→-4px, gap 0) + 연결 모서리 평평(14→4px)해 한 덩어리 말풍선처럼 (대표 지시 2026-06-05).
// v171: 말풍선 상하 내부 여백 6→5px (대표 지시 2026-06-05) — 묶였을 때 공간 더 절약.
// v172: 말풍선 상하 내부 여백 5→4px (대표 지시 2026-06-05).
// v173: 연속 메시지 묶음 간격 0→1px (대표 지시 2026-06-05) — margin-top -4→-3px.
// v174: 연속 메시지 묶음 간격 1→2px (대표 지시 2026-06-05) — margin-top -3→-2px.
// v175: 1:1 목록·아바타 동명이인 오표시 버그 수정 — 상대를 이름 글자가 아닌 peer_id(ID)로 식별 (대표 지시 2026-06-05).
// v176: 1:1 대화 완전삭제 기능(소유자=대표 본인 전용) — 나가기 다이얼로그에 영구삭제 옵션 추가 (대표 지시 2026-06-05).
// v177: 위 옵션이 사이드바 방 우클릭->나가기 경로에서 안 보이던 문제 수정(경로2에도 토글 추가) (대표 지시 2026-06-05).
// v178: 모바일 첨부 파일 카드 더 작게 — 받기 버튼 옆줄 유지 + 폰트·아이콘·패딩·폭 축소 (PC 유지) (대표 지시 2026-06-05).
// v179: 말풍선 '읽음' 표시 — 전원이 다 읽으면 '읽음' 글자 숨김(시간만), 안 읽은 사람 있을 때만 숫자 (대표 지시 2026-06-05).
// v180: 안 읽은 사람 숫자 — 비활성(잠금)·삭제된 계정 제외 (대표 지시 2026-06-05). 퇴사자 때문에 '1' 이 안 사라지던 문제 방지.
// v181: 메시지 본문 URL 자동 링크 — http(s):// 클릭하면 새 탭으로 (대표 지시 2026-06-05).
// v182: 사용동의서 전 직원 정식 가동 + 이미 접속자도 앱 복귀 시 즉시 게이트 재확인 (대표 지시 2026-06-05).
// v183: 관리자 탭에 '사용동의 현황' 추가 — 동의자·미동의자 명단/일시/본사·베트남별/엑셀 (대표 지시 2026-06-05).
// v184: 사용동의 현황 — 유지보수관리자 전용 -> 관리자(ceo) 전체에게 표시 (대표 지시 2026-06-05).
// v185: 앱 제목을 '사람을 잇고, 일을 잇고, 미래를 잇다. — 이음'으로 (창제목·설치명 전체, 아이콘명 '이음') (대표 지시 2026-06-05).
const CACHE = "knk-messenger-v282-eum";

// 클라이언트가 알려주는 현재 활성 방 (방 진입 시 page 가 postMessage 로 알려줌)
// SW 가 재시작되면 초기화됨 → 다음 방 진입·visibility 변화 시 다시 받음
let _activeRoomId = null;
// 페이지 하트비트 — { ts: 마지막 시각ms, roomId: 그때 활성 방 } — SW 재시작 후 회복 신호
let _lastHeartbeat = { ts: 0, roomId: null };
// 하위 경로 배포(/msg) 지원 — 등록 시 ?base= 쿼리로 전달받은 접두어
const BASE = (new URL(self.location).searchParams.get("base") || "");

// base64url → Uint8Array (applicationServerKey 변환용)
function _urlBase64ToUint8Array(base64) {
  const padding = "=".repeat((4 - base64.length % 4) % 4);
  const base64Std = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64Std);
  const arr = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i);
  return arr;
}

// 푸시 구독 재등록 — SW 교체·만료 시 구독이 깨지면 자동 복구.
async function _resubscribePush() {
  try {
    const resp = await fetch(BASE + "/api/push/vapid_public");
    if (!resp.ok) return;
    const cfg = await resp.json();
    if (!cfg || !cfg.public_key || !cfg.enabled) return;
    const sub = await self.registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: _urlBase64ToUint8Array(cfg.public_key),
    });
    await fetch(BASE + "/api/push/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subscription: sub.toJSON() }),
    });
  } catch (e) { /* ignore */ }
}

// SW 가 교체되거나 브라우저가 구독을 무효화하면 자동 재구독 (알림 끊김 방지)
self.addEventListener("pushsubscriptionchange", (e) => {
  e.waitUntil(_resubscribePush());
});

self.addEventListener("install", (e) => {
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    (async () => {
      await caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))));
      await self.clients.claim();
      // SW 교체 후 푸시 구독이 없으면 자동 재구독 (v8→v9 교체 시 알림 끊긴 문제 복구)
      //  단, 권한이 이미 '허용(granted)'된 경우에만 조용히 재구독. '미결정(prompt)' 이면 구독 시도가
      //  알림 권한 팝업을 띄우므로 생략 — 로그인 화면에서 SW 등록 시 갑자기 팝업 뜨던 부작용 차단. (대표 지시 2026-05-30)
      try {
        const sub = await self.registration.pushManager.getSubscription();
        if (!sub) {
          let _st = "prompt";
          try { _st = await self.registration.pushManager.permissionState({ userVisibleOnly: true }); } catch (e) {}
          if (_st === "granted") await _resubscribePush();
        }
      } catch (e) { /* ignore */ }
    })()
  );
});

// HTML navigation + JS/CSS → 강제 네트워크 (옛 코드 잔존 차단)
// 이미지·아이콘은 기본 동작 (캐시 OK, ?v=쿼리로 무효화).
self.addEventListener("fetch", (e) => {
  const req = e.request;
  const accept = req.headers.get("accept") || "";
  const url = (() => { try { return new URL(req.url); } catch (_) { return null; } })();
  const path = url ? url.pathname : "";
  const isHtml = req.mode === "navigate" || accept.includes("text/html");
  const isJs   = path.endsWith(".js")  || accept.includes("javascript");
  const isCss  = path.endsWith(".css") || accept.includes("text/css");
  if (req.method === "GET" && (isHtml || isJs || isCss)) {
    e.respondWith(
      fetch(req, { cache: "no-store" }).catch(() => fetch(req))
    );
    return;
  }
  // 그 외는 기본 네트워크 동작
});

// Push notifications 핸들러 — 휴대폰 PWA 가 백그라운드/종료 상태에서도 OS 알림 + 앱 배지
self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data ? e.data.json() : {}; } catch (err) { data = { title: "KNK 이음", body: e.data?.text() || "" }; }
  // 읽음 신호(type=clear) — 다른 기기에서 그 방을 읽었을 때 서버가 보냄.
  // 알림을 새로 띄우지 않고, 해당 방(tag) 알림을 닫고 앱 배지만 갱신. (대표 지시 2026-05-20)
  if (data && data.type === "clear") {
    e.waitUntil((async () => {
      try {
        const tag = data.tag;   // ex: "room_5"
        const notes = await self.registration.getNotifications();
        // v24: 유일 tag 방식 폐기 — 같은 tag 정확 매칭으로 close
        notes.forEach(n => {
          if (!tag || n.tag === tag) { try { n.close(); } catch (e) {} }
        });
      } catch (e) { /* ignore */ }
      try {
        if ("setAppBadge" in self.navigator) {
          const n = (typeof data.badge === "number") ? data.badge : 0;
          if (n > 0) await self.navigator.setAppBadge(n);
          else if ("clearAppBadge" in self.navigator) await self.navigator.clearAppBadge();
        }
      } catch (e) { /* ignore */ }
    })());
    return;
  }
  const rawTitle = data.title || "KNK 이음";
  // tag = 방 단위 (예: room_5) — 같은 방 메시지는 1장 카드에 누적 (대표 지시 2026-05-26 팝업 통합)
  // 사운드는 OS 차원 throttle 가능 → 진동 패턴 강화로 보완
  e.waitUntil((async () => {
    // v18 → v20: 활성 방 시 알림 생략 (대표 지시 2026-05-26)
    //   모바일 OS 가 한번 띄운 알림에 대한 close 권한이 약함 → 닫는 대신 처음부터 안 띄우는 전략.
    //   3가지 신호 OR 결합 (하나만 부합해도 활성으로 간주):
    //     (1) postMessage 로 받은 _activeRoomId  ← SW 살아있을 때
    //     (2) 페이지 하트비트 (최근 8초 안)   ← SW 재시작 후 회복용
    //     (3) 클라이언트 URL 의 ?room=N      ← SW 재시작·visibilityState 버그와 무관 (최강 신호)
    //   visibilityState/focused 는 Chrome Android PWA 푸시 컨텍스트에서 신뢰 불가 → 의존 안 함.
    try {
      const tagRoomMatch = data.tag && data.tag.match(/^room_(\d+)$/);
      const tagRoomId = tagRoomMatch ? tagRoomMatch[1] : null;
      if (tagRoomId) {
        let isSameRoom = false;
        // (1) 메모리 변수
        if (_activeRoomId != null && String(_activeRoomId) === tagRoomId) {
          isSameRoom = true;
        }
        // (2) 하트비트 (최근 8초 — 2초 간격 × 4번 누락 허용)
        if (!isSameRoom && _lastHeartbeat.roomId != null
            && String(_lastHeartbeat.roomId) === tagRoomId
            && (Date.now() - _lastHeartbeat.ts) < 8000) {
          isSameRoom = true;
        }
        // (3) 클라이언트 URL — 가장 신뢰성 높음 (페이지가 ?room=X 에 있으면 그 방을 보고 있음)
        let clientCount = 0;
        if (!isSameRoom) {
          const clientList = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
          clientCount = clientList.length;
          for (const c of clientList) {
            const url = c.url || "";
            const m = url.match(/[?&]room=(\d+)/);
            if (m && m[1] === tagRoomId) {
              isSameRoom = true;
              break;
            }
          }
        }
        if (isSameRoom) {
          // 사용자가 이 방을 보고 있음 → OS 알림 생략. 배지만 갱신.
          if ("setAppBadge" in self.navigator) {
            try {
              const n = (typeof data.badge === "number" && data.badge > 0) ? data.badge : undefined;
              if (n !== undefined) await self.navigator.setAppBadge(n);
              else if ("clearAppBadge" in self.navigator) await self.navigator.clearAppBadge();
            } catch (_) {}
          }
          return;   // ★ 알림 안 띄우고 종료
        }
      }
    } catch (_) {}

    // v25: 단순 복원 — 같은 tag + renotify + 서버 데이터 그대로
    //   v22 검증된 방식. body 보존 시도(v24)가 알림 자체를 막은 원인 추정 → 폐기.
    const tag = data.tag || "";   // ex: "room_5"

    // PWA 홈화면 아이콘 배지 갱신 (서버가 보낸 정확한 안 읽음 수)
    if ("setAppBadge" in self.navigator) {
      try {
        const n = (typeof data.badge === "number" && data.badge > 0) ? data.badge : undefined;
        if (n !== undefined) await self.navigator.setAppBadge(n);
        else await self.navigator.setAppBadge();
      } catch (e) { /* ignore */ }
    }

    const opts = {
      body: data.body || "",
      icon: BASE + "/static/icons/icon-192.png",
      badge: BASE + "/static/icons/icon-192.png",
      data: { url: data.url || (BASE + "/chat") },
      tag: tag,
      requireInteraction: false,
      vibrate: [300, 80, 300, 80, 300, 80, 500],
      renotify: true,   // ★ 같은 tag 라도 사운드/진동 매번
    };
    await self.registration.showNotification(rawTitle, opts);
  })());
});

// 클라이언트 페이지 → SW 메시지 채널 (대표 지시 2026-05-26)
// 일부 브라우저(Samsung Internet)는 페이지의 notification.close() 가 OS 트레이까지 안 닿음.
// SW 안에서 close() 호출하면 더 신뢰성 있게 동작 — 그래서 페이지가 SW 에 부탁하는 구조.
self.addEventListener("message", (e) => {
  const data = e.data || {};
  // v18: 활성 방 추적 — 페이지가 방 진입·visibility 변화 시 알려줌
  if (data.type === "set_active_room") {
    _activeRoomId = data.roomId || null;
    return;
  }
  if (data.type === "clear_active_room") {
    _activeRoomId = null;
    return;
  }
  // v20: 하트비트 — 페이지가 2초마다 자기가 살아있고 어느 방인지 알려줌. SW 재시작 시 회복.
  if (data.type === "heartbeat") {
    _lastHeartbeat = {
      ts: Date.now(),
      roomId: data.roomId || null,
    };
    return;
  }
  if (data.type === "clear_room") {
    e.waitUntil((async () => {
      const tag = data.tag || ("room_" + data.roomId);   // ex: "room_5"
      try {
        // v24: tag 정확 매칭 (유일 tag 방식 폐기)
        const all = await self.registration.getNotifications();
        all.forEach(n => {
          if (n.tag === tag) { try { n.close(); } catch (_) {} }
        });
      } catch (_) {}
      // 배지 갱신 (서버가 알려준 정확한 카운트)
      if (typeof data.badge === "number" && "setAppBadge" in self.navigator) {
        try {
          if (data.badge > 0) await self.navigator.setAppBadge(data.badge);
          else if ("clearAppBadge" in self.navigator) await self.navigator.clearAppBadge();
        } catch (_) {}
      }
    })());
  } else if (data.type === "clear_all") {
    e.waitUntil((async () => {
      try {
        const all = await self.registration.getNotifications();
        all.forEach(n => { try { n.close(); } catch (_) {} });
      } catch (_) {}
      if ("clearAppBadge" in self.navigator) {
        try { await self.navigator.clearAppBadge(); } catch (_) {}
      }
    })());
  }
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  let url = e.notification.data?.url || (BASE + "/chat");
  // 서버가 BASE_PATH 없이 "/chat?room=4" 같은 경로만 보내는 경우 자동으로 BASE 접두 추가.
  // 이중 적용 방지 — 이미 BASE 로 시작하면 그대로.
  if (BASE && !url.startsWith(BASE) && url.startsWith("/")) {
    url = BASE + url;
  }
  // 알림 클릭 시 PWA 앱 배지 해제 (사용자가 열어서 봤으니까)
  if ("clearAppBadge" in self.navigator) {
    try { self.navigator.clearAppBadge(); } catch (e) {}
  }
  e.waitUntil(
    clients.matchAll({ type: "window" }).then(list => {
      for (const c of list) {
        if (c.url.includes(url) && "focus" in c) return c.focus();
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
