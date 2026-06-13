# Cloudflare Email Worker 연결 안내 v1 (2026-06-13)

> 목적: `test@knk-mailtest.com` 으로 온 **실제 메일을 HAIST WORKS 메일함으로 직접** 받기.
> 현재: test@ → 지메일 전달(받기 증명용) → **이걸 Worker로 전환**.
> 대표님 화면(WORKS): 관리자 → **메일 받기 설정**(`/admin/mail-inbound`) 에 토큰·값·코드·순서가 모두 있음.

---

## 구조

```
[외부 발신] → test@knk-mailtest.com
   → Cloudflare Email Worker (아래 코드)
   → POST https://works.knknara.co.kr/api/mail/inbound  (헤더 X-KNK-Mail-Token)
   → HAIST WORKS 메일함 저장 + AI 분류·요약
   (+ 안전망: 지메일로도 전달 — 시범 기간 유실 0)
```

## 연결 순서 (대표님)

1. **WORKS 관리자 → 메일 받기 설정** 에서 **토큰 생성** (복사)
2. **Cloudflare → Workers & Pages → Create → Worker** → 아래 코드 붙여넣기 → 배포
3. 그 Worker → **Settings → Variables** 에 3개 등록:
   - `WORKS_INBOUND_URL` = `https://works.knknara.co.kr/api/mail/inbound`
   - `KNK_MAIL_INBOUND_TOKEN` = (1에서 만든 토큰)
   - `FORWARD_TO` = `knk.jungrack.kim@gmail.com` (안전망, 선택)
4. **Cloudflare → Email Routing → 라우팅 규칙** → `test@knk-mailtest.com` 동작을
   **'이메일로 전송' → 'Worker로 전송'** 으로 변경(그 Worker 선택)
5. 실제 메일을 `test@knk-mailtest.com` 으로 보내 → **HAIST WORKS 메일함** 도착 확인

## Worker 코드

```js
// KNK Mail — Cloudflare Email Worker
export default {
  async email(message, env, ctx) {
    let raw = "";
    try { raw = await new Response(message.raw).text(); } catch (e) {}
    const payload = {
      to: message.to,
      from: message.from,
      subject: (message.headers && message.headers.get("subject")) || "",
      raw: raw,
      size: raw.length,
    };
    try {
      await fetch(env.WORKS_INBOUND_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-KNK-Mail-Token": env.KNK_MAIL_INBOUND_TOKEN,
        },
        body: JSON.stringify(payload),
      });
    } catch (e) {}
    if (env.FORWARD_TO) {
      try { await message.forward(env.FORWARD_TO); } catch (e) {}
    }
  }
};
```

## WORKS 측 처리 (구현 완료, z380)

- `/api/mail/inbound` : 토큰 검증(관리자 설정 `mail_inbound_token` 우선, 없으면 env) → `raw` MIME 를 파이썬 `email` 모듈로 파싱(멀티파트·인코딩 헤더·첨부명) → 저장 + AI.
- 토큰은 **WORKS 관리자 화면에서 생성**(전산 불필요). app_settings 에 보관.
- 보안: 토큰 불일치 401, 미설정 403(비활성), 외부 위조 차단.

## 주의

- knknara.co.kr(회사 도메인)·MX 는 **건드리지 않음**. 전부 knk-mailtest.com 에서만.
- 첨부 파일 본문 저장은 다음 단계(현재는 첨부 '이름·개수'만 본문에 표시).
- 토큰 재생성 시 Cloudflare Worker 변수도 새 값으로 교체 필요.

*작성: 빅터 — 2026-06-13.*
