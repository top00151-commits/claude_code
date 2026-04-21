# 카카오워크 Webhook 발급 + HAIST WORKS 연결 가이드

> **목적**: HAIST WORKS의 변경 알림·요청 티켓을 카카오워크 채널에 자동 푸시
> **대상**: KNK 관리자 (대표님 또는 IT 담당)
> **소요 시간**: 약 20분
> **현재 상태**: stub 상태 (콘솔 로그만 출력) → 본 가이드 완료 시 실 알림 활성

---

## 0. 한눈에 보는 흐름

```
HAIST WORKS 변경/티켓 발생
       ↓
카카오워크 Webhook URL 호출 (POST + JSON)
       ↓
지정된 카카오워크 채팅방에 알림 표시
       ↓
구성원이 즉시 인지 → web 링크 클릭으로 상세 확인
```

---

## 1. 카카오워크 워크스페이스 준비 (이미 사용 중이면 SKIP)

1. https://www.kakaowork.com 접속
2. KNK 워크스페이스 로그인 (관리자 계정)
3. **[관리자] → [워크스페이스 설정]** 메뉴 진입

> 📌 KNK가 카카오워크를 아직 안 쓰면 이 단계가 가장 큼. 별도 도입 결정 필요 (월 5,500원/인 기준).

---

## 2. Webhook 봇 생성 (각 부서·시스템별)

### 2.1 봇 생성

1. 관리자 페이지 → **[봇 관리]** → **[봇 추가]**
2. 봇 설정
   - 이름: `HAIST WORKS — 변경 알림` (예시)
   - 설명: `프로젝트 변경 사항을 자동으로 알려주는 봇`
   - 프로필 이미지: KNK 로고 업로드 권장
3. **[Webhook URL 발급]** 버튼 클릭
4. 발급된 URL 복사 (예: `https://api.kakaowork.com/v1/inbound/messages?token=xxxxxxxx`)

### 2.2 채팅방 추가

1. 카카오워크 앱에서 채팅방 생성 (또는 기존 채팅방 사용)
   - 예: `[변경 알림] 검사기 사업부`
   - 예: `[변경 알림] 자동화 사업부`
   - 예: `[요청 티켓] 구매팀`
   - 예: `[요청 티켓] 가공팀`
2. 채팅방에 방금 만든 봇 초대
3. 채팅방 ID 확인 (URL 또는 봇 관리에서 확인)

### 2.3 권장 채팅방 구성

| 채팅방 | 용도 | 멤버 |
|---|---|---|
| `[변경 알림] 전사` | 모든 변경 (Concept·중요) | 임원 + 팀장 |
| `[변경 알림] 검사기 사업부` | 기구·전장·SW 변경 (T) | 검사기 관련 부서원 |
| `[변경 알림] 자동화 사업부` | 기구·전장·SW 변경 (M) | 자동화 관련 부서원 |
| `[요청 티켓] 구매팀` | 자재요청 라우팅 | 구매팀원 |
| `[요청 티켓] 가공팀` | 긴급가공 라우팅 | 가공팀원 |
| `[요청 티켓] 품질팀` | 검수요청 라우팅 | 품질팀원 |
| `[요청 티켓] 설계팀` | MODIFY 라우팅 | 설계팀원 |

→ **부서별로 분리**해야 알림 피로 방지 (Continental 성공 패턴)

---

## 3. HAIST WORKS 연결 (config 작성)

### 3.1 환경 변수 파일 생성

`01_HAIST_WORKS/.env` 파일 생성 (없으면)

```env
# 카카오워크 Webhook URL 매핑
# 형식: KAKAO_WEBHOOK_<channel_key>=<URL>

# 변경 알림용
KAKAO_WEBHOOK_change_company=https://api.kakaowork.com/v1/inbound/messages?token=AAAA...
KAKAO_WEBHOOK_change_T=https://api.kakaowork.com/v1/inbound/messages?token=BBBB...
KAKAO_WEBHOOK_change_M=https://api.kakaowork.com/v1/inbound/messages?token=CCCC...

# 부서별 (영향 부서 ID로 매핑)
KAKAO_WEBHOOK_team_2=https://api.kakaowork.com/v1/inbound/messages?token=DDDD...   # 검사기팀
KAKAO_WEBHOOK_team_3=https://api.kakaowork.com/v1/inbound/messages?token=EEEE...   # 품질팀
KAKAO_WEBHOOK_team_4=https://api.kakaowork.com/v1/inbound/messages?token=FFFF...   # 설계팀
KAKAO_WEBHOOK_team_5=https://api.kakaowork.com/v1/inbound/messages?token=GGGG...   # SW팀
KAKAO_WEBHOOK_team_6=https://api.kakaowork.com/v1/inbound/messages?token=HHHH...   # 전장팀
KAKAO_WEBHOOK_team_7=https://api.kakaowork.com/v1/inbound/messages?token=IIII...   # 제조1팀
KAKAO_WEBHOOK_team_8=https://api.kakaowork.com/v1/inbound/messages?token=JJJJ...   # 제조2팀
KAKAO_WEBHOOK_team_9=https://api.kakaowork.com/v1/inbound/messages?token=KKKK...   # 가공팀
KAKAO_WEBHOOK_team_10=https://api.kakaowork.com/v1/inbound/messages?token=LLLL...  # 구매팀
KAKAO_WEBHOOK_team_11=https://api.kakaowork.com/v1/inbound/messages?token=MMMM...  # 관리팀
KAKAO_WEBHOOK_team_12=https://api.kakaowork.com/v1/inbound/messages?token=NNNN...  # 영업팀
KAKAO_WEBHOOK_team_13=https://api.kakaowork.com/v1/inbound/messages?token=OOOO...  # 개발혁신팀
```

### 3.2 .gitignore에 추가 (보안 — Webhook URL 노출 금지)

```gitignore
# 카카오워크 Webhook 비밀
.env
*.env.local
```

### 3.3 코드 업데이트 (database.py의 `kakao_webhook_send`)

현재:
```python
def kakao_webhook_send(channel_id: str, text: str, blocks: list = None) -> bool:
    print(f"[KAKAO STUB] channel={channel_id} text={text[:80]}...")
    return True
```

실제 동작:
```python
import os, requests
from dotenv import load_dotenv
load_dotenv()

def kakao_webhook_send(channel_id: str, text: str, blocks: list = None) -> bool:
    url = os.getenv(f"KAKAO_WEBHOOK_{channel_id}")
    if not url:
        print(f"[KAKAO SKIP] channel={channel_id} (URL 미설정)")
        return False
    try:
        body = {"text": text}
        if blocks:
            body["blocks"] = blocks
        r = requests.post(url, json=body, timeout=5)
        return r.status_code in (200, 201)
    except Exception as e:
        print(f"[KAKAO ERROR] {e}")
        return False
```

### 3.4 패키지 설치

```bash
pip install python-dotenv requests
```

requirements.txt 추가
```
python-dotenv
requests
```

---

## 4. 연결 테스트

### 4.1 빠른 테스트 (콘솔)

```bash
cd "C:/Users/top00/JR/Claude 코드/KNK업무시스템구축/01_HAIST_WORKS"
python -c "
from app.database import kakao_webhook_send
result = kakao_webhook_send('change_T', '🔴 [테스트] 빅터가 보내는 첫 알림')
print('성공' if result else '실패')
"
```

→ 카카오워크 채팅방에 메시지가 표시되면 **연결 완료**.

### 4.2 실제 변경 등록 테스트

1. HAIST WORKS 로그인 (admin/admin1234)
2. `/changes/new` → 변경 등록
3. 영향 부서 카카오워크 채널에 자동 알림 확인

---

## 5. 알림 메시지 디자인 (블록 카드)

기본은 텍스트만 보내지만, 카카오워크 **블록 카드**로 더 보기 좋게:

```python
def make_change_block(change_no, title, change_type, urgency, link):
    color = "#A5282C" if urgency == "긴급" else "#F57F17"
    icon = "🔴" if urgency == "긴급" else "🟡"
    return [
        {
            "type": "header",
            "text": f"{icon} [{change_type}] {title}",
            "style": "blue"
        },
        {
            "type": "description",
            "term": "변경번호",
            "content": {"type": "text", "text": change_no}
        },
        {
            "type": "button",
            "text": "확인하러 가기",
            "style": "primary",
            "action_type": "open_system_browser",
            "value": link
        }
    ]
```

→ 추후 보강. 일단 텍스트만으로 충분.

---

## 6. 대안 — n8n self-hosted (Research 권고)

카카오워크 직접 연결 외에 **n8n self-hosted** 방식도 가능:

- 장점: 카카오워크 외에 메일·SMS·Slack·Webhook 등 동시 발송 / 워크플로우 시각 편집
- 단점: n8n 서버 별도 운영 필요 (Docker)
- 추천 시점: 알림 채널이 5개 이상 늘어나면

→ **Phase 2 검토** (현재는 직접 연결로 충분)

---

## 7. 보안 체크리스트

- [ ] Webhook URL을 절대 GitHub에 commit하지 말 것 (.env 사용)
- [ ] URL은 임직원 외부 공유 금지
- [ ] 봇 권한 최소화 (메시지 발송만, 읽기 X)
- [ ] 분기마다 Webhook URL 재발급 (보안 정책)

---

## 8. 자주 묻는 질문

### Q: Webhook URL을 분실했어요
A: 카카오워크 관리자 → 봇 관리 → 해당 봇 → "Webhook URL 재발급" 클릭

### Q: 알림이 안 와요
A: 1) `.env` 파일 형식 확인 (KAKAO_WEBHOOK_xxx) 2) 봇이 채팅방에 초대됐는지 3) `python-dotenv` 설치 4) 서버 재시작

### Q: 너무 많이 알림이 와요
A: HAIST WORKS의 "알림 피로 방지" 기능 활성화 (별도 가이드)

### Q: 카카오톡(개인 메신저)에도 보낼 수 있나요?
A: 카카오 알림톡 (별도 비용) 또는 "나에게 보내기" API 사용. 가이드 별도 작성 가능

---

## 9. 다음 단계

Webhook 발급·연결 완료 후
1. **30개 직원 대상 알림 테스트** — 실제 변경 등록해서 알림 도착 확인
2. **알림 피로 모니터링** — 1주 후 직원 피드백 수집
3. **블록 카드 디자인 적용** — 텍스트 → 시각적 카드로 업그레이드

---

**문서 위치**: `KNK업무시스템구축/01_HAIST_WORKS/_GUIDE_카카오워크_Webhook_발급.md`
**작성**: 빅터 (2026-04-20)
**연락**: 빅터 (Claude) — 막히는 부분 알려주시면 단계별 안내
