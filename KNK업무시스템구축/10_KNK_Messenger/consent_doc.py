# -*- coding: utf-8 -*-
"""사내 전용 메신저 이용·보안준수 동의서 본문 (대표 지시 2026-06-03).

- 첫 로그인 시 + 마지막 동의로부터 약 100일마다 재동의 (app.py CONSENT_INTERVAL_DAYS).
- 고객사(게스트)는 제외.
- 내용/항목을 바꾸면 CONSENT_VERSION 을 올려 전원 재동의를 받음.

언어: ko(한국어 원문) / vi(베트남어 번역). 사용자 UI 언어가 vi 면 vi, 그 외는 ko.

v3 (2026-06-03) — 대표 확정 전문(14개 항목):
  AI 기반 업무지원 기능 운영 확인 / 처리위탁·국외이전 별도 항목 /
  보유기간 구체화(3년·5년) / 열람 시 대표 승인·사유기록·범위제한 /
  노조가입 등 민감정보 미수집 / 본인의 권리·문의처 / 동의 기록.
  ※ 전 직원 배포 전 노무사·변호사 검토 권장(강제동의 구조·통신비밀보호법·취업규칙).
"""

# v4 (2026-06-03): 프로필(얼굴) 사진 수집항목·생체인식 미처리 안내 추가 / 문의처 (주)케이엔케이 관리팀·KNKVINA 관리팀
CONSENT_VERSION = 4

# ── 테스트 모드 (대표 지시 2026-06-03) ──
#   True  : 아래 CONSENT_TEST_USERNAMES 계정만 + 매 접속/로그인마다 항상 표시 (반복 테스트용, 동의 기록 무시)
#   False : 전체 직원 대상 + 첫 로그인 + 약 100일 주기 (정식 배포)
#   → 테스트 확인 후 전체 배포 시 CONSENT_TEST_MODE = False 한 줄만 바꾸면 됨.
# 2026-06-05 대표 지시 "지금부터 전체 동의서 받게 진행" → 전 직원 정식 가동(CONSENT_TEST_MODE=False).
#   전원 대상 + 미동의자 첫 로그인/접속 시 즉시 + 마지막 동의로부터 100일마다 재동의. 거부 시 로그아웃(동의해야 사용).
#   되돌리는 법: CONSENT_TEST_MODE = True 로 바꾸면 즉시 멈춤(아래 USERNAMES 가 비어 있어 아무에게도 안 뜸).
CONSENT_TEST_MODE = False
CONSENT_TEST_USERNAMES = []   # TEST_MODE=False 면 무시됨. (테스트로 되돌릴 때만 사용 — 예: ["5"] 면 그 사번만 매번 표시)

_KO_HTML = """
<p>본인은 회사가 업무 소통, 업무 이력 관리, 정보보호, 고객사 자료 보호 및 AI 기반 업무지원을 위해 사내 전용 메신저를 운영한다는 내용을 안내받았습니다.</p>
<p><strong>본인은 아래 내용을 확인하고 동의합니다.</strong></p>

<h3>1. 설치 및 이용 동의</h3>
<p>본인은 회사 업무 수행을 위해 사내 전용 메신저를 아래 기기에 설치하고 사용하는 것에 동의합니다.</p>
<ul>
  <li>회사 업무용 PC</li>
  <li>회사 지급 노트북</li>
  <li>업무 수행을 위해 본인이 사용하는 휴대폰</li>
  <li>기타 회사가 승인한 업무용 기기</li>
</ul>
<p>개인 휴대폰에 사내 메신저를 설치하는 경우에도 회사는 사내 메신저 앱 내부의 업무정보만 관리하며, 개인 휴대폰 내 개인 메신저, 문자, 통화내역, 사진, 연락처, 개인파일 등은 임의로 확인하지 않음을 안내받았습니다.</p>

<h3>2. 회사가 관리하는 업무 정보</h3>
<p>본인은 사내 메신저 안에서 작성·전송되는 아래 정보가 회사 업무기록으로 관리될 수 있음을 확인합니다.</p>
<ul>
  <li>업무방, 부서방, 프로젝트방, 공지방 등 공식 업무방 내 회사 업무 관련 대화</li>
  <li>회사 업무 관련 첨부파일, 사진, 자료</li>
  <li>공지 확인 내역</li>
  <li>업무지시, 담당자 지정, 완료 여부 등 업무 처리 기록</li>
  <li>메신저 운영에 필요한 계정 정보 및 접속 기록</li>
</ul>
<p>단, 1:1 대화방은 본 확인서의 "1:1 대화방 보호 원칙"에 따라 별도로 보호됨을 확인합니다.</p>

<h3>3. AI 기반 업무지원 기능 운영 확인</h3>
<p>본인은 회사가 업무 효율 향상, 업무 이력 관리, 번역·요약, 보고서 작성 지원, 회의내용 정리, 프로젝트 진행상황 정리, 본사와 해외법인 간 소통 개선 등을 위해 사내 메신저에 AI 기반 업무지원 기능을 적용할 수 있음을 안내받았습니다.</p>
<p>본인은 회사 업무 수행 과정에서 사내 메신저의 AI 기능을 사용할 수 있으며, 해당 기능 수행에 필요한 범위 내에서 회사 업무 관련 메시지, 업무파일, 공지 내용, 프로젝트 자료 등이 AI 시스템을 통해 처리될 수 있음을 확인합니다.</p>
<p>회사는 AI 기능을 개인 사생활 감시 목적으로 사용하지 않으며, 개인 휴대폰 내부자료, 개인 메신저, 문자, 통화내역, 사진, 연락처 등 개인자료를 AI 처리 대상으로 삼지 않음을 확인합니다.</p>
<p>회사는 AI 기능 운영을 위해 서버 호스팅, 시스템 유지보수, 번역·요약·분석 등 외부 서비스에 개인정보 처리업무의 일부를 위탁할 수 있으며, 수탁자가 개인정보와 회사 정보를 안전하게 처리하도록 관리·감독합니다.</p>
<p>외부 AI 서비스의 서버가 국외에 위치하거나 개인정보의 국외 이전이 발생하는 경우, 회사는 관련 법령에 따라 이전받는 자, 이전 국가, 이전 항목, 이전 목적, 보유·이용기간 등 필요한 사항을 안내하고 필요한 절차를 진행합니다.</p>
<p>본인은 회사가 승인하지 않은 개인용 AI 서비스 또는 외부 AI 사이트에 회사자료, 고객사 자료, 도면, 견적, 계약자료, 프로그램 소스, 장비 핵심기술, 개인정보 등이 포함된 내용을 입력하지 않겠습니다.</p>

<h3>4. 회사가 하지 않는 사항</h3>
<p>회사는 사내 메신저 운영과 관련하여 아래 사항을 임의로 수행하지 않습니다.</p>
<ul>
  <li>개인 위치 추적</li>
  <li>개인 메신저, 문자, 통화내역 확인</li>
  <li>개인 사진, 연락처, 개인파일 확인</li>
  <li>개인 휴대폰 내부자료 확인</li>
  <li>개인 사생활 감시</li>
  <li>1:1 대화방 임의 열람</li>
</ul>

<h3>5. 1:1 대화방 보호 원칙</h3>
<p>회사는 사내 메신저의 1:1 대화방을 임의로 열람하지 않습니다.</p>
<p>1:1 대화방은 직원 간 개별 소통 공간으로 보며, 회사는 일반적인 관리 목적이나 직원 감시 목적으로 해당 내용을 확인하지 않습니다.</p>
<p>다만, 아래와 같은 예외적인 사유가 발생한 경우에는 법이 정한 절차와 방법에 따라 필요한 범위 내에서 확인될 수 있음을 확인합니다.</p>
<ul>
  <li>수사기관의 적법한 요청</li>
  <li>법원 명령 또는 재판 절차상 필요한 경우</li>
  <li>회사와 임직원 또는 제3자 사이의 법적 분쟁</li>
  <li>회사 또는 고객사 정보유출 사고가 발생했거나 객관적인 의심 정황이 있는 경우</li>
  <li>중대한 보안사고, 계정 도용, 불법행위 확인이 필요한 경우</li>
</ul>
<p>이 경우에도 회사는 대표이사 또는 지정 책임자의 승인, 열람 사유 기록, 열람 범위 제한 등 내부 절차에 따라 필요한 범위 내에서만 확인합니다.</p>

<h3>6. 업무자료 확인 가능 범위</h3>
<p>본인은 회사가 아래 사유가 발생한 경우, 필요한 범위 내에서 사내 메신저의 회사 업무 관련 내용을 확인할 수 있음을 확인합니다.</p>
<ul>
  <li>회사 또는 고객사 정보유출 사고가 발생했거나 객관적인 의심 정황이 있는 경우</li>
  <li>고객사 클레임, 품질 이슈, 납기 문제 확인이 필요한 경우</li>
  <li>퇴사, 부서 이동, 담당자 변경에 따른 업무 인수인계가 필요한 경우</li>
  <li>프로젝트 진행 이력 확인이 필요한 경우</li>
  <li>보안사고, 비정상 접속, 시스템 장애 대응이 필요한 경우</li>
  <li>법령, 감사, 고객사 보안 요청 대응이 필요한 경우</li>
</ul>
<p>회사는 위와 같은 경우에도 필요한 범위를 초과하여 업무 내용을 확인하지 않으며, 관련 법령과 회사 내부 절차에 따라 처리합니다.</p>

<h3>7. 개인정보 수집·이용 동의</h3>
<p>본인은 회사가 사내 메신저 운영을 위해 아래 개인정보를 수집·이용하는 것에 동의합니다.</p>
<p><strong>1) 수집·이용 목적</strong></p>
<ul>
  <li>사내 메신저 계정 생성 및 사용자 식별</li>
  <li>회사 업무 소통 및 업무 이력 관리</li>
  <li>공지사항 전달 및 확인</li>
  <li>회사 및 고객사 정보보호</li>
  <li>AI 기반 업무지원 기능 운영</li>
  <li>보안사고 예방 및 대응</li>
  <li>시스템 운영, 장애 대응, 접속 관리</li>
  <li>퇴사, 전보, 담당자 변경 시 업무 인수인계</li>
</ul>
<p><strong>2) 수집 항목</strong></p>
<ul>
  <li>성명, 부서, 직급, 사번, 회사 이메일, 업무 연락처</li>
  <li>메신저 계정 정보</li>
  <li>접속 일시, 접속 기기, IP 등 시스템 운영에 필요한 기록</li>
  <li>사내 메신저 내 회사 업무 관련 대화, 파일, 공지 확인 내역</li>
  <li>AI 업무지원 기능 사용 시 처리되는 업무 메시지, 업무파일, 요청 내용 및 처리 결과</li>
  <li>프로필(아바타) 등록용 얼굴 사진 등 본인 식별용 사진</li>
</ul>
<p><strong>3) 보유 및 이용기간</strong></p>
<ul>
  <li>재직 기간 동안 보유·이용합니다.</li>
  <li>퇴사 후 일반 계정정보 및 접속기록은 원칙적으로 3년간 보관합니다.</li>
  <li>프로젝트, 고객사 대응, 품질 이슈, 장비 납품, 분쟁 관련 업무기록은 해당 업무 종료 후 원칙적으로 5년간 보관할 수 있습니다.</li>
  <li>법령상 보존 의무, 고객사 계약상 보존 필요, 감사, 수사, 소송, 분쟁 대응이 진행 중인 경우에는 해당 사유가 종료될 때까지 보관할 수 있습니다.</li>
  <li>보존 필요성이 종료된 정보는 회사 내부 기준에 따라 삭제 또는 분리 보관합니다.</li>
</ul>
<p><strong>4) 수집하지 않는 정보</strong></p>
<p>회사는 사내 메신저 운영을 위해 주민등록번호 등 고유식별정보나 사상, 건강, 노동조합 가입 여부 등 민감정보를 수집하지 않습니다.</p>
<p>또한 개인 메신저, 문자, 통화내역, 사진, 연락처, 개인파일, 개인 휴대폰 내부자료를 임의로 수집하지 않습니다.</p>
<p><strong>5) 프로필(얼굴) 사진 안내</strong></p>
<p>회사는 사용자 식별과 업무 편의를 위해 프로필(아바타) 사진 등록을 원칙으로 안내하며, 본인이 등록한 얼굴 사진을 수집·표시할 수 있습니다. 해당 사진은 사내 메신저 내 표시 용도로만 사용하며, 회사는 이를 얼굴인식 등 생체인식정보로 처리하지 않습니다. 등록된 사진은 사내 메신저 이용자에게 표시될 수 있습니다.</p>

<h3>8. 개인정보 처리위탁 및 국외 이전 안내</h3>
<p>회사는 사내 메신저 운영, 서버 호스팅, 시스템 유지보수, AI 번역·요약·분석 등 업무 수행을 위해 개인정보 처리업무의 일부를 외부 업체에 위탁할 수 있습니다.</p>
<p>회사는 수탁자가 개인정보와 회사 정보를 안전하게 처리하도록 관리·감독하며, 수탁자가 위탁받은 목적과 범위를 초과하여 개인정보를 이용하거나 제3자에게 제공하지 않도록 관리합니다.</p>
<p>구체적인 수탁자, 위탁업무, 처리정보, 국외 이전 여부 등은 별도 첨부자료 또는 사내 공지를 통해 안내할 수 있으며, 수탁자 또는 위탁업무 내용이 변경되는 경우 변경 내용을 안내합니다.</p>
<p>외부 서비스의 서버가 국외에 위치하거나 개인정보의 국외 이전이 발생하는 경우, 회사는 관련 법령에 따라 이전받는 자, 이전 국가, 이전 항목, 이전 목적, 보유·이용기간 등 필요한 사항을 안내하고 필요한 절차를 진행합니다.</p>

<h3>9. 개인정보 보호 안전조치</h3>
<p>회사는 개인정보와 회사 업무정보를 안전하게 보호하기 위해 아래와 같은 합리적인 조치를 시행합니다.</p>
<ul>
  <li>접근 권한 통제 및 관리자 권한 최소화</li>
  <li>계정 및 비밀번호 보호</li>
  <li>접속 기록의 보관 및 점검</li>
  <li>주요 업무자료 열람 이력 관리</li>
  <li>전송 구간 암호화 적용</li>
  <li>업무 목적 범위를 벗어난 열람 제한</li>
  <li>보안사고 발생 시 필요한 조치 시행</li>
</ul>

<h3>10. 본인의 권리 및 문의처</h3>
<p>본인은 사내 메신저에 보관된 본인의 개인정보에 대해 열람, 정정·삭제, 처리정지 및 동의 철회를 요청할 수 있음을 안내받았습니다.</p>
<p>다만, 회사의 필수 업무 운영, 법령상 보존 의무, 업무 인수인계, 분쟁 대응, 고객사 대응 등 정당한 사유가 있는 경우 요청이 일부 제한될 수 있습니다.</p>
<p>관련 요청 및 문의는 (주)케이엔케이 관리팀으로 할 수 있습니다.</p>

<h3>11. 위치정보 관련 확인</h3>
<p>회사는 사내 메신저 운영 과정에서 임직원의 실시간 개인 위치정보를 수집하거나 추적하지 않습니다.</p>
<p>향후 출퇴근 관리, 현장 출입 확인 등 위치정보 기능을 별도로 도입할 경우에는 사전에 목적, 수집 항목, 보유기간, 이용 범위를 별도로 안내하고 별도 동의를 받겠습니다.</p>

<h3>12. 정보보호 준수</h3>
<p>본인은 사내 메신저를 사용하면서 아래 사항을 준수하겠습니다.</p>
<ul>
  <li>회사 업무자료를 외부 메신저, 개인 이메일, 개인 클라우드 등으로 임의 전송하지 않겠습니다.</li>
  <li>회사가 승인하지 않은 개인용 AI 서비스 또는 외부 AI 사이트에 회사자료나 고객사 자료를 입력하지 않겠습니다.</li>
  <li>고객사 자료, 도면, 견적, 프로그램, 장비 사진, 계약자료 등을 승인 없이 외부로 공유하지 않겠습니다.</li>
  <li>고객사 승인 없이 고객사 공장 내부 사진, 장비 설치 사진, 프로그램 화면, 도면, 검사조건, 생산조건 등을 외부로 공유하지 않겠습니다.</li>
  <li>회사 승인 없이 외부인 또는 퇴사자를 업무방에 초대하지 않겠습니다.</li>
  <li>메신저 계정과 비밀번호를 타인에게 공유하지 않겠습니다.</li>
  <li>회사 업무자료를 개인 목적으로 저장, 복사, 재전송하지 않겠습니다.</li>
  <li>자료 유출, 휴대폰 분실, 계정 도용, 비정상 접속 의심이 있을 경우 즉시 회사에 보고하겠습니다.</li>
</ul>

<h3>13. 동의 거부 및 업무상 제한 안내</h3>
<p>본인은 본 확인 및 동의를 거부할 수 있음을 안내받았습니다.</p>
<p>다만, 사내 전용 메신저는 회사의 공식 업무 소통, 업무자료 관리 및 AI 기반 업무지원 시스템이므로, 필수적인 설치·이용 및 정보보호 준수 확인을 거부할 경우 공지 확인, 업무지시 확인, 프로젝트 참여, 파일 공유, 업무 인수인계 등 회사 업무 수행에 제한이 발생할 수 있음을 확인합니다.</p>

<h3>14. 동의 기록 및 정기 재확인</h3>
<p>본인이 본 확인서에 서명하거나 전자적으로 [동의합니다]를 선택하면 동의 일시, 계정정보, 접속기록 등 전자적 동의 증빙이 기록될 수 있음을 확인합니다.</p>
<p>본인은 회사가 사내 메신저 운영 및 정보보호 준수 상태를 확인하기 위해 약 100일 주기로 본 확인서를 재확인할 수 있음을 안내받았습니다.</p>
<p>정책 변경, 수집 항목 변경, 기능 추가 등 중요한 변경사항이 발생하는 경우 회사는 변경 내용을 사전에 안내하고 필요한 경우 별도 확인 또는 동의를 받을 수 있습니다.</p>

<p><strong>위 내용을 충분히 안내받고 확인하였으며, 이에 동의합니다.</strong></p>
"""

_VI_HTML = """
<p>Tôi đã được thông báo rằng công ty vận hành Messenger nội bộ nhằm phục vụ trao đổi công việc, quản lý lịch sử công việc, bảo vệ thông tin, bảo vệ tài liệu của khách hàng (đối tác) và hỗ trợ công việc dựa trên AI.</p>
<p><strong>Tôi xác nhận và đồng ý với các nội dung dưới đây.</strong></p>

<h3>1. Đồng ý cài đặt và sử dụng</h3>
<p>Tôi đồng ý cài đặt và sử dụng Messenger nội bộ trên các thiết bị dưới đây để thực hiện công việc của công ty.</p>
<ul>
  <li>Máy tính (PC) dùng cho công việc của công ty</li>
  <li>Máy tính xách tay do công ty cấp</li>
  <li>Điện thoại di động mà bản thân sử dụng để thực hiện công việc</li>
  <li>Các thiết bị công việc khác được công ty phê duyệt</li>
</ul>
<p>Tôi đã được thông báo rằng ngay cả khi cài đặt Messenger nội bộ trên điện thoại cá nhân, công ty chỉ quản lý thông tin công việc bên trong ứng dụng Messenger nội bộ, và không tùy tiện kiểm tra tin nhắn cá nhân, tin nhắn SMS, lịch sử cuộc gọi, hình ảnh, danh bạ, tệp cá nhân... trong điện thoại cá nhân.</p>

<h3>2. Thông tin công việc do công ty quản lý</h3>
<p>Tôi xác nhận rằng các thông tin dưới đây được tạo · gửi trong Messenger nội bộ có thể được quản lý như hồ sơ công việc của công ty.</p>
<ul>
  <li>Cuộc trò chuyện liên quan đến công việc trong các phòng công việc chính thức như phòng công việc, phòng bộ phận, phòng dự án, phòng thông báo</li>
  <li>Tệp đính kèm, hình ảnh, tài liệu liên quan đến công việc của công ty</li>
  <li>Lịch sử xác nhận thông báo</li>
  <li>Hồ sơ xử lý công việc như chỉ thị công việc, chỉ định người phụ trách, tình trạng hoàn thành</li>
  <li>Thông tin tài khoản và lịch sử truy cập cần thiết cho việc vận hành Messenger</li>
</ul>
<p>Tuy nhiên, phòng trò chuyện 1:1 được bảo vệ riêng theo "Nguyên tắc bảo vệ phòng trò chuyện 1:1" của bản xác nhận này.</p>

<h3>3. Xác nhận về việc vận hành chức năng hỗ trợ công việc dựa trên AI</h3>
<p>Tôi đã được thông báo rằng công ty có thể áp dụng chức năng hỗ trợ công việc dựa trên AI vào Messenger nội bộ nhằm nâng cao hiệu quả công việc, quản lý lịch sử công việc, dịch · tóm tắt, hỗ trợ soạn báo cáo, tổng hợp nội dung cuộc họp, tổng hợp tình hình tiến độ dự án, cải thiện giao tiếp giữa trụ sở chính và pháp nhân nước ngoài...</p>
<p>Tôi xác nhận rằng trong quá trình thực hiện công việc, tôi có thể sử dụng chức năng AI của Messenger nội bộ, và trong phạm vi cần thiết để thực hiện chức năng đó, các tin nhắn liên quan đến công việc, tệp công việc, nội dung thông báo, tài liệu dự án... của công ty có thể được xử lý thông qua hệ thống AI.</p>
<p>Công ty không sử dụng chức năng AI cho mục đích giám sát đời sống riêng tư cá nhân, và xác nhận không lấy dữ liệu cá nhân như dữ liệu bên trong điện thoại cá nhân, tin nhắn cá nhân, SMS, lịch sử cuộc gọi, hình ảnh, danh bạ... làm đối tượng xử lý của AI.</p>
<p>Để vận hành chức năng AI, công ty có thể ủy thác một phần công việc xử lý thông tin cá nhân cho các dịch vụ bên ngoài như lưu trữ máy chủ (hosting), bảo trì hệ thống, dịch · tóm tắt · phân tích..., và quản lý · giám sát để bên nhận ủy thác xử lý thông tin cá nhân và thông tin của công ty một cách an toàn.</p>
<p>Trong trường hợp máy chủ của dịch vụ AI bên ngoài đặt ở nước ngoài hoặc phát sinh việc chuyển thông tin cá nhân ra nước ngoài, công ty sẽ thông báo các nội dung cần thiết như bên nhận chuyển, quốc gia chuyển đến, hạng mục chuyển, mục đích chuyển, thời gian lưu giữ · sử dụng... theo quy định pháp luật liên quan và thực hiện các thủ tục cần thiết.</p>
<p>Tôi sẽ không nhập các nội dung có chứa tài liệu công ty, tài liệu khách hàng, bản vẽ, báo giá, tài liệu hợp đồng, mã nguồn chương trình, công nghệ lõi của thiết bị, thông tin cá nhân... vào các dịch vụ AI cá nhân hoặc trang AI bên ngoài mà công ty không phê duyệt.</p>

<h3>4. Những điều công ty không thực hiện</h3>
<p>Liên quan đến việc vận hành Messenger nội bộ, công ty không tùy tiện thực hiện các việc dưới đây.</p>
<ul>
  <li>Theo dõi vị trí cá nhân</li>
  <li>Kiểm tra tin nhắn cá nhân, tin nhắn SMS, lịch sử cuộc gọi</li>
  <li>Kiểm tra hình ảnh, danh bạ, tệp cá nhân</li>
  <li>Kiểm tra dữ liệu bên trong điện thoại cá nhân</li>
  <li>Giám sát đời sống riêng tư cá nhân</li>
  <li>Tùy tiện xem phòng trò chuyện 1:1</li>
</ul>

<h3>5. Nguyên tắc bảo vệ phòng trò chuyện 1:1</h3>
<p>Công ty không tùy tiện xem phòng trò chuyện 1:1 của Messenger nội bộ.</p>
<p>Phòng trò chuyện 1:1 được xem là không gian trao đổi riêng giữa các nhân viên, và công ty không kiểm tra nội dung đó vì mục đích quản lý thông thường hay mục đích giám sát nhân viên.</p>
<p>Tuy nhiên, tôi xác nhận rằng trong trường hợp phát sinh các lý do ngoại lệ dưới đây, nội dung có thể được kiểm tra trong phạm vi cần thiết theo trình tự và phương pháp do pháp luật quy định.</p>
<ul>
  <li>Yêu cầu hợp pháp của cơ quan điều tra</li>
  <li>Lệnh của tòa án hoặc khi cần thiết trong trình tự xét xử</li>
  <li>Tranh chấp pháp lý giữa công ty với người lao động hoặc bên thứ ba</li>
  <li>Khi xảy ra sự cố rò rỉ thông tin của công ty hoặc khách hàng, hoặc có tình huống nghi ngờ một cách khách quan</li>
  <li>Khi cần xác minh sự cố bảo mật nghiêm trọng, đánh cắp tài khoản, hành vi vi phạm pháp luật</li>
</ul>
<p>Ngay cả trong các trường hợp này, công ty chỉ kiểm tra trong phạm vi cần thiết theo trình tự nội bộ như có sự phê duyệt của Tổng giám đốc hoặc người phụ trách được chỉ định, ghi lại lý do xem, giới hạn phạm vi xem.</p>

<h3>6. Phạm vi có thể kiểm tra tài liệu công việc</h3>
<p>Tôi xác nhận rằng khi phát sinh các lý do dưới đây, công ty có thể kiểm tra nội dung liên quan đến công việc của công ty trong Messenger nội bộ trong phạm vi cần thiết.</p>
<ul>
  <li>Khi xảy ra sự cố rò rỉ thông tin của công ty hoặc khách hàng, hoặc có tình huống nghi ngờ một cách khách quan</li>
  <li>Khi cần xác minh khiếu nại của khách hàng, vấn đề chất lượng, vấn đề tiến độ giao hàng</li>
  <li>Khi cần bàn giao công việc do nghỉ việc, chuyển bộ phận, thay đổi người phụ trách</li>
  <li>Khi cần kiểm tra lịch sử tiến hành dự án</li>
  <li>Khi cần ứng phó sự cố bảo mật, truy cập bất thường, sự cố hệ thống</li>
  <li>Khi cần đáp ứng yêu cầu của pháp luật, kiểm toán, yêu cầu bảo mật của khách hàng</li>
</ul>
<p>Ngay cả trong các trường hợp trên, công ty không kiểm tra nội dung công việc vượt quá phạm vi cần thiết, và xử lý theo pháp luật liên quan cùng quy trình nội bộ của công ty.</p>

<h3>7. Đồng ý thu thập · sử dụng thông tin cá nhân</h3>
<p>Tôi đồng ý để công ty thu thập · sử dụng các thông tin cá nhân dưới đây nhằm vận hành Messenger nội bộ.</p>
<p><strong>1) Mục đích thu thập · sử dụng</strong></p>
<ul>
  <li>Tạo tài khoản Messenger nội bộ và nhận diện người dùng</li>
  <li>Trao đổi công việc của công ty và quản lý lịch sử công việc</li>
  <li>Truyền đạt và xác nhận thông báo</li>
  <li>Bảo vệ thông tin của công ty và khách hàng</li>
  <li>Vận hành chức năng hỗ trợ công việc dựa trên AI</li>
  <li>Phòng ngừa và ứng phó sự cố bảo mật</li>
  <li>Vận hành hệ thống, ứng phó sự cố, quản lý truy cập</li>
  <li>Bàn giao công việc khi nghỉ việc, thuyên chuyển, thay đổi người phụ trách</li>
</ul>
<p><strong>2) Hạng mục thu thập</strong></p>
<ul>
  <li>Họ tên, bộ phận, chức vụ, mã số nhân viên, email công ty, số liên lạc công việc</li>
  <li>Thông tin tài khoản Messenger</li>
  <li>Thời gian truy cập, thiết bị truy cập, IP và các hồ sơ cần thiết cho việc vận hành hệ thống</li>
  <li>Cuộc trò chuyện, tệp, lịch sử xác nhận thông báo liên quan đến công việc trong Messenger nội bộ</li>
  <li>Tin nhắn công việc, tệp công việc, nội dung yêu cầu và kết quả xử lý được xử lý khi sử dụng chức năng hỗ trợ công việc AI</li>
  <li>Ảnh khuôn mặt dùng để đăng ký ảnh đại diện (avatar) và các ảnh khác dùng để nhận diện bản thân</li>
</ul>
<p><strong>3) Thời gian lưu giữ và sử dụng</strong></p>
<ul>
  <li>Lưu giữ · sử dụng trong thời gian làm việc.</li>
  <li>Sau khi nghỉ việc, thông tin tài khoản chung và lịch sử truy cập về nguyên tắc được lưu giữ trong 3 năm.</li>
  <li>Hồ sơ công việc liên quan đến dự án, đáp ứng khách hàng, vấn đề chất lượng, giao thiết bị, tranh chấp về nguyên tắc có thể được lưu giữ trong 5 năm kể từ khi kết thúc công việc đó.</li>
  <li>Trong trường hợp đang có nghĩa vụ lưu giữ theo pháp luật, nhu cầu lưu giữ theo hợp đồng với khách hàng, hoặc đang tiến hành kiểm toán, điều tra, kiện tụng, xử lý tranh chấp, có thể lưu giữ cho đến khi lý do đó kết thúc.</li>
  <li>Thông tin đã hết nhu cầu lưu giữ sẽ được xóa hoặc lưu giữ tách biệt theo tiêu chuẩn nội bộ của công ty.</li>
</ul>
<p><strong>4) Thông tin không thu thập</strong></p>
<p>Để vận hành Messenger nội bộ, công ty không thu thập thông tin định danh riêng (như số đăng ký cư dân, CMND/CCCD) hay thông tin nhạy cảm như tư tưởng, sức khỏe, việc gia nhập công đoàn.</p>
<p>Ngoài ra, công ty không tùy tiện thu thập tin nhắn cá nhân, SMS, lịch sử cuộc gọi, hình ảnh, danh bạ, tệp cá nhân, dữ liệu bên trong điện thoại cá nhân.</p>
<p><strong>5) Hướng dẫn về ảnh hồ sơ (khuôn mặt)</strong></p>
<p>Để nhận diện người dùng và thuận tiện cho công việc, công ty về nguyên tắc hướng dẫn đăng ký ảnh hồ sơ (avatar), và có thể thu thập · hiển thị ảnh khuôn mặt do bản thân đăng ký. Ảnh đó chỉ được sử dụng cho mục đích hiển thị trong Messenger nội bộ, và công ty không xử lý ảnh đó thành thông tin sinh trắc học như nhận diện khuôn mặt. Ảnh đã đăng ký có thể được hiển thị cho người dùng Messenger nội bộ.</p>

<h3>8. Hướng dẫn về ủy thác xử lý và chuyển thông tin cá nhân ra nước ngoài</h3>
<p>Công ty có thể ủy thác một phần công việc xử lý thông tin cá nhân cho đơn vị bên ngoài để thực hiện các công việc như vận hành Messenger nội bộ, lưu trữ máy chủ, bảo trì hệ thống, dịch · tóm tắt · phân tích bằng AI.</p>
<p>Công ty quản lý · giám sát để bên nhận ủy thác xử lý thông tin cá nhân và thông tin công ty một cách an toàn, và quản lý để bên nhận ủy thác không sử dụng thông tin cá nhân vượt quá mục đích và phạm vi được ủy thác hoặc cung cấp cho bên thứ ba.</p>
<p>Bên nhận ủy thác cụ thể, công việc ủy thác, thông tin được xử lý, có chuyển ra nước ngoài hay không... có thể được thông báo qua tài liệu đính kèm riêng hoặc thông báo nội bộ, và khi bên nhận ủy thác hoặc nội dung công việc ủy thác thay đổi, công ty sẽ thông báo nội dung thay đổi.</p>
<p>Trong trường hợp máy chủ của dịch vụ bên ngoài đặt ở nước ngoài hoặc phát sinh việc chuyển thông tin cá nhân ra nước ngoài, công ty sẽ thông báo các nội dung cần thiết như bên nhận chuyển, quốc gia chuyển đến, hạng mục chuyển, mục đích chuyển, thời gian lưu giữ · sử dụng... theo quy định pháp luật liên quan và thực hiện các thủ tục cần thiết.</p>

<h3>9. Biện pháp an toàn bảo vệ thông tin cá nhân</h3>
<p>Để bảo vệ an toàn thông tin cá nhân và thông tin công việc của công ty, công ty thực hiện các biện pháp hợp lý dưới đây.</p>
<ul>
  <li>Kiểm soát quyền truy cập và tối thiểu hóa quyền quản trị viên</li>
  <li>Bảo vệ tài khoản và mật khẩu</li>
  <li>Lưu giữ và kiểm tra lịch sử truy cập</li>
  <li>Quản lý lịch sử xem các tài liệu công việc quan trọng</li>
  <li>Áp dụng mã hóa đường truyền</li>
  <li>Hạn chế việc xem vượt quá phạm vi mục đích công việc</li>
  <li>Thực hiện các biện pháp cần thiết khi xảy ra sự cố bảo mật</li>
</ul>

<h3>10. Quyền của bản thân và nơi liên hệ</h3>
<p>Tôi đã được thông báo rằng tôi có thể yêu cầu xem, đính chính · xóa, tạm dừng xử lý và rút lại sự đồng ý đối với thông tin cá nhân của tôi được lưu giữ trong Messenger nội bộ.</p>
<p>Tuy nhiên, trong trường hợp có lý do chính đáng như vận hành công việc thiết yếu của công ty, nghĩa vụ lưu giữ theo pháp luật, bàn giao công việc, xử lý tranh chấp, đáp ứng khách hàng, yêu cầu có thể bị hạn chế một phần.</p>
<p>Các yêu cầu và thắc mắc liên quan có thể gửi đến Bộ phận Quản lý KNKVINA.</p>

<h3>11. Xác nhận liên quan đến thông tin vị trí</h3>
<p>Trong quá trình vận hành Messenger nội bộ, công ty không thu thập hoặc theo dõi thông tin vị trí cá nhân theo thời gian thực của người lao động.</p>
<p>Trong trường hợp sau này triển khai riêng chức năng thông tin vị trí như quản lý giờ ra vào làm, xác nhận ra vào hiện trường..., công ty sẽ thông báo trước về mục đích, hạng mục thu thập, thời gian lưu giữ, phạm vi sử dụng và nhận sự đồng ý riêng.</p>

<h3>12. Tuân thủ bảo vệ thông tin</h3>
<p>Trong khi sử dụng Messenger nội bộ, tôi sẽ tuân thủ các điều dưới đây.</p>
<ul>
  <li>Tôi sẽ không tùy tiện gửi tài liệu công việc của công ty ra ngoài qua messenger bên ngoài, email cá nhân, đám mây (cloud) cá nhân...</li>
  <li>Tôi sẽ không nhập tài liệu công ty hay tài liệu khách hàng vào dịch vụ AI cá nhân hoặc trang AI bên ngoài mà công ty không phê duyệt.</li>
  <li>Tôi sẽ không chia sẻ ra ngoài tài liệu của khách hàng, bản vẽ, báo giá, chương trình, hình ảnh thiết bị, tài liệu hợp đồng... khi chưa được phê duyệt.</li>
  <li>Tôi sẽ không chia sẻ ra ngoài hình ảnh bên trong nhà máy khách hàng, hình ảnh lắp đặt thiết bị, màn hình chương trình, bản vẽ, điều kiện kiểm tra, điều kiện sản xuất... khi chưa được khách hàng phê duyệt.</li>
  <li>Tôi sẽ không mời người ngoài hoặc người đã nghỉ việc vào phòng công việc khi chưa được công ty phê duyệt.</li>
  <li>Tôi sẽ không chia sẻ tài khoản và mật khẩu Messenger cho người khác.</li>
  <li>Tôi sẽ không lưu trữ, sao chép, gửi lại tài liệu công việc của công ty vì mục đích cá nhân.</li>
  <li>Khi nghi ngờ rò rỉ tài liệu, mất điện thoại, đánh cắp tài khoản, truy cập bất thường, tôi sẽ báo cáo ngay cho công ty.</li>
</ul>

<h3>13. Thông báo về quyền từ chối đồng ý và hạn chế trong công việc</h3>
<p>Tôi đã được thông báo rằng tôi có thể từ chối việc xác nhận và đồng ý này.</p>
<p>Tuy nhiên, vì Messenger nội bộ là hệ thống trao đổi công việc chính thức, quản lý tài liệu công việc và hỗ trợ công việc dựa trên AI của công ty, tôi xác nhận rằng nếu từ chối việc xác nhận cài đặt · sử dụng thiết yếu và tuân thủ bảo vệ thông tin, có thể phát sinh hạn chế trong việc thực hiện công việc của công ty như xác nhận thông báo, xác nhận chỉ thị công việc, tham gia dự án, chia sẻ tệp, bàn giao công việc.</p>

<h3>14. Ghi nhận sự đồng ý và tái xác nhận định kỳ</h3>
<p>Tôi xác nhận rằng khi tôi ký vào bản xác nhận này hoặc chọn [Tôi đồng ý] bằng phương thức điện tử, bằng chứng đồng ý điện tử như thời điểm đồng ý, thông tin tài khoản, lịch sử truy cập... có thể được ghi lại.</p>
<p>Tôi đã được thông báo rằng công ty có thể tái xác nhận bản xác nhận này theo chu kỳ khoảng 100 ngày để kiểm tra tình trạng vận hành Messenger nội bộ và việc tuân thủ bảo vệ thông tin.</p>
<p>Trong trường hợp phát sinh các thay đổi quan trọng như thay đổi chính sách, thay đổi hạng mục thu thập, bổ sung chức năng, công ty sẽ thông báo trước về nội dung thay đổi và có thể nhận xác nhận hoặc đồng ý riêng nếu cần thiết.</p>

<p><strong>Tôi đã được hướng dẫn và xác nhận đầy đủ các nội dung trên, và đồng ý với các nội dung đó.</strong></p>
"""

CONSENT_DOC = {
    "ko": {
        "title": "사내 전용 메신저 설치·이용 및 보안준수 확인서",
        "html": _KO_HTML,
        "agree": "동의합니다",
        "decline": "동의하지 않음 (로그아웃)",
        "scroll_hint": "끝까지 읽으시면 [동의합니다] 버튼이 활성화됩니다.",
        "declined_msg": "동의해야 메신저를 사용할 수 있습니다. 로그아웃합니다.",
    },
    "vi": {
        "title": "Bản xác nhận cài đặt · sử dụng Messenger nội bộ và tuân thủ bảo mật",
        "html": _VI_HTML,
        "agree": "Tôi đồng ý",
        "decline": "Không đồng ý (Đăng xuất)",
        "scroll_hint": "Vui lòng đọc đến cuối, nút [Tôi đồng ý] sẽ được kích hoạt.",
        "declined_msg": "Bạn phải đồng ý mới có thể sử dụng messenger. Hệ thống sẽ đăng xuất.",
    },
}
