"""
v5H226z96 (2026-05-11) — 산업 부품 한영 동의어 사전 + 발음 유사 매칭.

검색 시 한글 → 영어 / 영어 → 한글 양방향 확장.
예: "솔밸브" → ["solenoid valve", "solenoid", "valve", "sy", "sv"]
    "Cylinder" → ["실린더", "cm2", "cdm2", "cj2", "cdq"]
"""

# 1:N 매핑 (한쪽 키 입력 → 여러 동의어 + 영문 부품 시리즈 prefix)
SYNONYM_GROUPS = [
    # 공압 / 유압
    ['솔밸브', '솔레노이드밸브', '솔레노이드 밸브', 'solenoid valve', 'solenoid', 'sol valve', 'sy', 'sv', 'vfr'],
    ['공압밸브', '공압 밸브', 'pneumatic valve'],
    ['유압밸브', '유압 밸브', 'hydraulic valve'],
    ['체크밸브', '체크 밸브', '역지밸브', 'check valve'],
    ['릴리프밸브', '릴리프 밸브', 'relief valve'],
    ['니들밸브', '니들 밸브', 'needle valve'],
    ['볼밸브', '볼 밸브', 'ball valve'],

    ['실린더', 'cylinder', 'cyl', 'cm2', 'cdm2', 'cj2', 'cdq', 'mb', 'cdq2', 'rhc'],
    ['공압실린더', '공압 실린더', 'pneumatic cylinder'],
    ['로드리스실린더', 'rodless cylinder', 'cy', 'mxs'],
    ['회전액추에이터', '회전 액추에이터', 'rotary actuator', 'crb', 'crb2'],
    ['액추에이터', 'actuator'],

    ['레귤레이터', '레규레이터', 'regulator', 'reg', 'ar'],
    ['필터', 'filter', 'af', 'amg', 'awd'],
    ['루브리케이터', 'lubricator', 'al'],
    ['FRL', 'frl', 'frl유닛', '에어유닛', 'air unit', 'ac'],
    ['에어드라이어', '에어 드라이어', 'air dryer', 'idfa'],

    ['피팅', '원터치피팅', '원터치 피팅', 'fitting', 'one-touch fitting', 'kq2', 'kq', 'kjh', 'kjl'],
    ['엘보우', '엘보', 'elbow', 'kq2l'],
    ['티', 'tee', 'kq2t'],
    ['유니언', '유니온', 'union', 'kq2u'],
    ['플러그', 'plug', 'kq2p'],
    ['스트레이트', '스트레이트 피팅', 'straight fitting', 'kq2h'],
    ['커플러', '커플링', 'coupler', 'coupling', 'kk', 'kkh'],

    ['에어호스', '에어 호스', 'air hose', 'tu', 'tub', 'tigb'],
    ['호스', 'hose', 'tu'],
    ['튜브', '튜빙', 'tube', 'tubing', 'tu'],
    ['파이프', 'pipe'],

    ['사이렌서', '소음기', 'silencer', 'an'],
    ['압력게이지', '압력 게이지', 'pressure gauge', 'gauge', 'g46', 'gz'],
    ['압력스위치', '압력 스위치', '디지털 압력스위치', 'pressure switch', 'ise40', 'ise', 'zse'],
    ['진공패드', '진공 패드', 'vacuum pad', 'zp'],
    ['진공발생기', '진공 발생기', 'vacuum generator', 'zh'],
    ['진공', 'vacuum'],

    ['실린더센서', '실린더 센서', '오토스위치', '오토 스위치', 'auto switch', 'd-a', 'd-m', 'd-y', 'd-z', 'd-m9b', 'd-m9p'],

    # 전기·전자
    ['센서', 'sensor'],
    ['근접센서', '근접 센서', 'proximity sensor'],
    ['포토센서', '포토 센서', '광센서', 'photo sensor', 'photoelectric'],
    ['파이버센서', '파이버 센서', '광파이버', 'fiber sensor', 'fiber'],
    ['엔코더', '인코더', 'encoder', 'enc'],
    ['리미트스위치', '리미트 스위치', 'limit switch', 'ls'],
    ['스위치', 'switch'],
    ['버튼', '푸시버튼', 'button', 'push button', 'pb'],
    ['셀렉터스위치', '셀렉터', 'selector switch'],
    ['릴레이', 'relay', 'ry', 'omron'],
    ['타이머', 'timer'],
    ['카운터', 'counter'],
    ['컨트롤러', '제어기', 'controller', 'plc'],
    ['플레이씨', 'plc'],
    ['터치패널', '터치 패널', 'touch panel', 'hmi'],
    ['디스플레이', 'display', 'lcd'],
    ['컨버터', 'converter'],
    ['인버터', 'inverter'],
    ['트랜스', '트랜스포머', '변압기', 'transformer'],
    ['파워서플라이', '파워 서플라이', '전원공급기', 'power supply', 'smps'],
    ['저항', '레지스터', 'resistor', 'r'],
    ['커패시터', '콘덴서', 'capacitor', 'cap'],
    ['다이오드', 'diode'],
    ['트랜지스터', 'transistor', 'tr'],
    ['엘이디', 'led', 'lamp'],
    ['램프', '램퍼', 'lamp'],
    ['커넥터', '코넥터', 'connector', 'conn', 'd-sub', 'dsub'],
    ['소켓', 'socket'],
    ['터미널', '단자', 'terminal'],
    ['단자대', '터미널블록', '터미널 블록', 'terminal block'],
    ['케이블', 'cable'],
    ['하네스', '와이어하네스', 'harness'],
    ['와이어', '전선', 'wire'],
    ['튜브마커', '튜브 마커', '마커', 'marker'],
    ['브레이커', '차단기', 'breaker', 'mccb', 'elb'],
    ['마그네트', '컨택터', 'magnetic contactor', 'mc'],

    # 기계요소
    ['모터', '모타', 'motor'],
    ['서보모터', '서보 모터', 'servo motor', 'servo'],
    ['스테퍼모터', '스테퍼 모터', '스텝모터', 'stepper motor', 'stepping motor', 'stepper'],
    ['기어드모터', '기어 모터', 'geared motor'],
    ['모터드라이버', '모터 드라이버', 'motor driver'],
    ['베어링', 'bearing', 'brg', 'nsk', 'thk'],
    ['리니어가이드', '리니어 가이드', 'lm가이드', 'linear guide', 'lm guide', 'lm'],
    ['볼스크류', '볼 스크류', 'ball screw', 'bs'],
    ['커플링', 'coupling'],
    ['풀리', 'pulley'],
    ['벨트', 'belt'],
    ['타이밍벨트', '타이밍 벨트', 'timing belt'],
    ['체인', 'chain'],
    ['기어', '기아', 'gear'],
    ['스프링', 'spring'],
    ['댐퍼', 'damper'],
    ['쇼크업소버', '쇼크 업소버', 'shock absorber'],
    ['샤프트', '축', 'shaft'],
    ['로드', '로드엔드', 'rod', 'rod end'],
    ['핀', 'pin'],
    ['키', '키이', 'key'],
    ['볼트', 'bolt'],
    ['너트', 'nut'],
    ['와셔', 'washer'],
    ['스크류', '나사', 'screw'],
    ['리벳', 'rivet'],

    # 구조물·가공
    ['브래킷', '브라켓', 'bracket', 'brkt'],
    ['플레이트', '플레잇', '판', 'plate'],
    ['프레임', 'frame'],
    ['바', 'bar', 'earth bar'],
    ['클램프', 'clamp'],
    ['지그', 'jig'],
    ['척', 'chuck'],
    ['바이스', 'vise'],
    ['플랜지', 'flange'],
    ['커버', 'cover'],
    ['하우징', 'housing'],
    ['캐비닛', '캐비넷', 'cabinet'],
    ['박스', 'box'],
    ['컨트롤박스', '컨트롤 박스', 'control box', 'cb'],
    ['터미널박스', '터미널 박스', 'terminal box', 'tb'],
    ['알루미늄프로파일', '알루미늄 프로파일', '알루프로파일', 'aluminum profile', 'profile'],
    ['프로파일', 'profile'],

    # 재료
    ['고무', '러버', 'rubber'],
    ['실리콘', 'silicone'],
    ['우레탄', '폴리우레탄', 'polyurethane', 'pu'],
    ['나일론', '나이론', 'nylon'],
    ['테플론', 'teflon', 'ptfe'],
    ['아크릴', 'acryl', 'acrylic'],

    # 측정·계측
    ['게이지', 'gauge', 'gage'],
    ['미터', 'meter'],
    ['카메라', 'camera', 'cam'],
    ['렌즈', 'lens'],
    ['바코드', 'barcode'],
    ['스캐너', 'scanner'],

    # KNK 회사 자주 쓰는
    ['공압', 'pneumatic'],
    ['유압', 'hydraulic'],
    ['전장', '전기', 'electric', 'electrical'],
    ['트레이', '트래이', 'tray'],
    ['셔틀', 'shuttle'],
    ['로더', 'loader'],
    ['언로더', 'unloader'],
    ['컨베이어', '컨베어', 'conveyor', 'cv'],
    ['실린더헤드', '실린더 헤드', 'cylinder head'],
    ['리프트', '리프터', 'lift', 'lifter'],
    ['프레스', 'press'],
    ['스테이션', 'station'],
    ['어태치', 'attach'],
]


def expand_query(q: str):
    """검색어를 동의어 사전으로 확장.

    Args:
        q: 사용자 검색 입력 (한글/영문/혼합)
    Returns:
        list[str] — 검색에 사용할 키워드 목록 (원본 포함, 중복 제거)
    """
    if not q or len(q.strip()) < 1:
        return [q] if q else []
    q_raw = q.strip()
    q_lower = q_raw.lower()
    q_compact = q_lower.replace(' ', '')

    expanded = {q_raw, q_lower}

    for group in SYNONYM_GROUPS:
        # 그룹 안 어떤 단어든 입력과 매칭되면 그룹 전체 추가
        for word in group:
            w_lower = word.lower()
            w_compact = w_lower.replace(' ', '')
            # 정확 일치 / 부분 포함 / 공백 무시 매칭
            if (w_lower == q_lower
                or w_compact == q_compact
                or w_lower in q_lower
                or q_lower in w_lower
                or w_compact in q_compact
                or q_compact in w_compact):
                for syn in group:
                    expanded.add(syn)
                    expanded.add(syn.lower())
                break

    # 너무 짧은 토큰 제거
    return [k for k in expanded if k and len(k) >= 1]
