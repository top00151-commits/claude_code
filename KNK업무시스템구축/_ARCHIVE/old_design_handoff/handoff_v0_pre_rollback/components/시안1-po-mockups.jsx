/* HAIST WORKS · 시안1 — 구매·자재 6페이지 (ERP-grade)
 * 다중 필터바 + sticky 컬럼 + 합계행 / 분석 차트 / 정보 밀도 ↑
 */
const { TopBar, Sidebar, PageHead, Sparkline, Bar, Trend, Mgmt, BizChip, StatusChip,
        SalesHome, OrdersPage, ProjectDetail, CalendarPage, DailyWork, TokensV2, ComponentsV2, Closing } = window;

/* ─── shared bits ─────────────────────────────────────────────── */
const POChip = ({ s }) => {
  const map = {draft:["po-draft","초안"],requested:["po-requested","품의중"],approved:["po-approved","승인"],
               sent:["po-sent","발주"],partial:["po-partial","부분입고"],received:["po-received","입고완료"],
               closed:["po-closed","종결"],overdue:["po-overdue","납기지연"]};
  const [c,l]=map[s]||["po-draft",s];
  return <span className={"chip-po "+c}>{l}</span>;
};
const StkBar = ({cur, safe, max}) => {
  const ratio = cur/max*100, safeR = safe/max*100;
  const cls = cur < safe*0.5 ? "is-critical" : cur < safe ? "is-low" : "";
  return (
    <div className="stk-bar">
      <div className={"stk-fill "+cls} style={{width:Math.min(100,ratio)+"%"}}/>
      <div className="stk-safe" style={{left:safeR+"%"}}/>
      <div className="stk-text">{cur} / {safe}</div>
    </div>
  );
};
const FilterBar = ({chips=[], search="자재 코드 · 품명 · 발주번호", result=""}) => (
  <div className="filterbar">
    <span className="fb-label">필터</span>
    {chips.map((c,i)=>c==="|"
      ? <span key={i} className="fb-divider"/>
      : <span key={i} className={"fb-chip"+(c.on?" is-active":"")}>{c.t}{c.v && <span className="num" style={{opacity:0.7,marginLeft:2}}>{c.v}</span>}{c.on && <span className="fb-x">×</span>}</span>
    )}
    <span className="fb-divider"/>
    <span className="fb-chip" style={{borderStyle:"dashed"}}>＋ 필터</span>
    <div style={{position:"relative",marginLeft:8}}>
      <span style={{position:"absolute",left:8,top:6,fontSize:12,color:"var(--ink-4)"}}>⌕</span>
      <input className="fb-search" placeholder={search}/>
    </div>
    {result && <span className="fb-result">{result}</span>}
  </div>
);

/* ============================================================
   ① 구매 홈 — KPI 6장 + 발주 단계별 분포 + 입고 임박 + 부족 알림
   ============================================================ */
const PurchaseHome = () => {
  const sparkPO = [12,18,15,22,28,24,30,32,28,35,42,38];
  const sparkSpend = [180,210,195,240,260,255,290,310,300,340,380,360];
  return (
    <div className="chrome">
      <TopBar/>
      <Sidebar active="po-home"/>
      <div className="main">
        <PageHead crumb="구매·자재" title="구매 홈"
          meta={<>2025년 1월 · 구매팀 박 차장 · <span className="num">10:24</span> 갱신</>}
          actions={<>
            <div className="seg"><button>일</button><button>주</button><button className="is-active">월</button><button>분기</button></div>
            <button className="btn btn-sm">⤓ Excel</button>
            <button className="btn btn-primary btn-sm">＋ 신규 발주</button>
          </>}/>
        <div className="main-bento" style={{gridTemplateColumns:"repeat(12, 1fr)",gridTemplateRows:"auto auto 1fr",gap:12}}>
          {/* 6 KPI */}
          {[
            {l:"이달 발주액",v:"3.62",u:"억",t:["up","+8.2%"],c:"#0f172a",sp:sparkSpend},
            {l:"진행 발주",v:"18",u:"건",t:["flat","승인 4·발주 12·부분입고 2"],c:"#1e5fbf",sp:sparkPO},
            {l:"이번 주 입고",v:"7",u:"건",t:["up","총 4,240만원"],c:"#0d7c4f"},
            {l:"납기 지연",v:"2",u:"건",t:["down","서일정밀 · 대성소재"],c:"#b91c1c",warn:1},
            {l:"안전재고 미달",v:"3",u:"품목",t:["flat","SCM440 외 2"],c:"#b45309"},
            {l:"공급사 OTD",v:"94.2",u:"%",t:["up","+1.8%p"],c:"#0d7c4f"},
          ].map((k,i)=>(
            <div key={i} className="kpi" style={{gridColumn:`${i*2+1} / ${i*2+3}`,padding:"14px 16px",minHeight:96,gap:4,background:k.warn?"var(--knk-red-soft)":"var(--surface)",border:k.warn?"1px solid var(--knk-red-line)":"none"}}>
              <div className="kpi-label" style={{fontSize:11}}>{k.l}</div>
              <div style={{display:"flex",alignItems:"baseline",gap:3}}>
                <span className="kpi-value" style={{fontSize:30,color:k.c}}>{k.v}</span>
                <span className="kpi-unit" style={{fontSize:13}}>{k.u}</span>
              </div>
              <div style={{fontSize:10.5,color:"var(--ink-3)",marginTop:"auto",fontWeight:500}}>
                {k.t[0]==="up"?"↗":k.t[0]==="down"?"↘":"→"} {k.t[1]}
              </div>
              {k.sp && <div style={{position:"absolute",right:10,bottom:8,opacity:0.5}}><Sparkline data={k.sp} color={k.c} w={70} h={24}/></div>}
            </div>
          ))}

          {/* 발주 단계별 + 사업부별 발주액 */}
          <div className="card card-tight" style={{gridColumn:"1 / 8"}}>
            <div className="card-head"><div><div className="card-title">발주 흐름</div><div className="card-sub">단계별 건수 / 금액 (이번 달)</div></div>
              <div className="seg"><button className="is-active">건수</button><button>금액</button></div>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(7, 1fr)",gap:8,padding:"4px 0",alignItems:"end",height:160}}>
              {[
                {s:"품의",c:"#94a3b8",n:5,a:"42M"},
                {s:"승인",c:"#0d7c4f",n:4,a:"58M"},
                {s:"발주",c:"#6d28d9",n:12,a:"1.62억"},
                {s:"부분입고",c:"#b45309",n:2,a:"24M"},
                {s:"입고완료",c:"#1e5fbf",n:14,a:"1.18억"},
                {s:"검수",c:"#334155",n:3,a:"18M"},
                {s:"종결",c:"#0f172a",n:8,a:"82M"},
              ].map((b,i)=>(
                <div key={i} style={{display:"flex",flexDirection:"column",alignItems:"center",gap:4,height:"100%"}}>
                  <div style={{flex:1,display:"flex",alignItems:"end",width:"100%"}}>
                    <div style={{width:"100%",height:`${b.n*7+10}%`,background:b.c,borderRadius:"3px 3px 0 0",position:"relative"}}>
                      <span className="num" style={{position:"absolute",top:-18,left:0,right:0,textAlign:"center",fontSize:11,fontWeight:700,color:b.c}}>{b.n}</span>
                    </div>
                  </div>
                  <div style={{fontSize:11,fontWeight:600,color:"var(--ink-2)"}}>{b.s}</div>
                  <div className="num" style={{fontSize:10,color:"var(--ink-4)"}}>{b.a}</div>
                </div>
              ))}
            </div>
            <div style={{borderTop:"1px solid var(--line)",paddingTop:8,marginTop:8,display:"flex",justifyContent:"space-between",fontSize:11,color:"var(--ink-3)"}}>
              <span>리드타임 평균 <span className="num" style={{color:"var(--ink)",fontWeight:600}}>4.2일</span> · 단축 0.6일</span>
              <span>긴급 발주 비중 <span className="num" style={{color:"var(--warn)",fontWeight:600}}>12%</span></span>
            </div>
          </div>

          <div className="card card-tight" style={{gridColumn:"8 / 13"}}>
            <div className="card-head"><div className="card-title">사업부별 발주 vs 매출 비중</div></div>
            <div style={{display:"flex",flexDirection:"column",gap:10,padding:"4px 0"}}>
              {[
                {b:"T 정밀",po:38,sl:39.7,c:"#c2410c"},
                {b:"M 가공",po:30,sl:29.2,c:"#1e40af"},
                {b:"E 전기",po:18,sl:20.2,c:"#6d28d9"},
                {b:"C 화학",po:14,sl:10.9,c:"#047857"},
              ].map(d=>(
                <div key={d.b}>
                  <div style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:4}}>
                    <span style={{fontWeight:600}}>{d.b}</span>
                    <span className="num" style={{color:"var(--ink-3)"}}>구매 {d.po}% · 매출 {d.sl}%</span>
                  </div>
                  <div style={{position:"relative",height:14,background:"var(--surface-3)",borderRadius:3,overflow:"hidden"}}>
                    <div style={{position:"absolute",left:0,top:0,bottom:0,width:d.po+"%",background:d.c}}/>
                    <div style={{position:"absolute",left:0,top:0,bottom:0,width:d.sl+"%",borderRight:"2px solid var(--ink)",pointerEvents:"none"}}/>
                  </div>
                </div>
              ))}
            </div>
            <div style={{marginTop:10,padding:"8px 10px",background:"var(--surface-inset)",borderRadius:6,fontSize:11,color:"var(--ink-3)",lineHeight:1.5}}>
              <strong style={{color:"var(--ink)"}}>해석</strong> — T 사업부 구매 비중 38%로 매출 39.7% 대비 적정. C 화학은 구매가 매출 대비 +3%p 높아 마진 점검 필요.
            </div>
          </div>

          {/* 입고 임박 + 부족 알림 */}
          <div className="card card-tight" style={{gridColumn:"1 / 8",overflow:"hidden",padding:0}}>
            <div style={{padding:"12px 16px",display:"flex",alignItems:"center",borderBottom:"1px solid var(--line)"}}>
              <div className="card-title">입고 임박 (D-3 이내)</div>
              <span style={{marginLeft:8,fontSize:11,color:"var(--ink-3)"}}>7건 · 총 4,240만원</span>
              <button className="btn btn-ghost btn-sm" style={{marginLeft:"auto"}}>전체 발주표 →</button>
            </div>
            <div style={{flex:1,overflow:"auto"}}>
              <table className="tbl tbl-dense">
                <thead><tr>
                  <th style={{width:90}}>발주번호</th>
                  <th style={{width:60}}>D-day</th>
                  <th>품목</th>
                  <th style={{width:90}}>공급사</th>
                  <th style={{width:60}} className="num">수량</th>
                  <th style={{width:80}} className="num">금액</th>
                  <th style={{width:80}}>상태</th>
                  <th style={{width:60}}>담당</th>
                </tr></thead>
                <tbody>
                  {[
                    {n:"PO-25-0142",d:"오늘",dn:0,nm:"SCM440 ⌀120 환봉",v:"대성소재",q:"24EA",a:"4,200,000",s:"sent",p:"이",urg:1},
                    {n:"PO-25-0138",d:"D-1",dn:1,nm:"베어링 6308 (NSK)",v:"한국NSK",q:"40EA",a:"2,400,000",s:"partial",p:"박"},
                    {n:"PO-25-0140",d:"D-2",dn:2,nm:"S45C ⌀60 환봉",v:"동양철강",q:"80EA",a:"3,200,000",s:"sent",p:"이"},
                    {n:"PO-25-0145",d:"D-2",dn:2,nm:"SS400 12t 평판",v:"포스코강판",q:"15장",a:"5,400,000",s:"approved",p:"박"},
                    {n:"PO-25-0136",d:"D-3",dn:3,nm:"GC250 주조품",v:"한주물산",q:"4EA",a:"6,800,000",s:"sent",p:"최"},
                    {n:"PO-25-0148",d:"D-3",dn:3,nm:"PCB 어셈블리 (제어반)",v:"신성PCB",q:"6EA",a:"12,400,000",s:"sent",p:"이"},
                    {n:"PO-25-0149",d:"D-3",dn:3,nm:"분체도장 외주",v:"태영도장",q:"식",a:"1,800,000",s:"sent",p:"최"},
                  ].map(r=>(
                    <tr key={r.n} style={{background:r.urg?"var(--knk-red-soft)":"transparent"}}>
                      <td><Mgmt size="sm">{r.n}</Mgmt></td>
                      <td className="num" style={{fontWeight:700,color:r.dn===0?"var(--knk-red)":r.dn===1?"var(--warn)":"var(--ink-2)"}}>{r.d}</td>
                      <td style={{fontWeight:500}}>{r.nm}</td>
                      <td style={{color:"var(--ink-3)"}}>{r.v}</td>
                      <td className="num">{r.q}</td>
                      <td className="num" style={{fontWeight:600}}>{r.a}</td>
                      <td><POChip s={r.s}/></td>
                      <td style={{color:"var(--ink-3)"}}>{r.p}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot><tr>
                  <td colSpan={5}>합계 (7건)</td>
                  <td className="num">42,200,000</td>
                  <td colSpan={2}/>
                </tr></tfoot>
              </table>
            </div>
          </div>

          <div className="card card-tight" style={{gridColumn:"8 / 13",overflow:"hidden",padding:0}}>
            <div style={{padding:"12px 16px",display:"flex",alignItems:"center",borderBottom:"1px solid var(--line)"}}>
              <div className="card-title">⚠ 안전재고 미달 / 긴급</div>
              <span style={{marginLeft:8,fontSize:11,color:"var(--knk-red)",fontWeight:600}}>3 품목</span>
              <button className="btn btn-primary btn-sm" style={{marginLeft:"auto",height:24,padding:"0 8px",fontSize:11}}>＋ 일괄 발주</button>
            </div>
            <div style={{flex:1,overflow:"auto",display:"flex",flexDirection:"column"}}>
              {[
                {c:"M-SCM440-D120",nm:"SCM440 ⌀120 환봉",cur:8,safe:24,unit:"EA",lt:"5일",used:"25-T-0142, 25-T-0156",crit:1},
                {c:"M-S45C-D60",nm:"S45C ⌀60 환봉",cur:18,safe:40,unit:"EA",lt:"3일",used:"25-T-0156"},
                {c:"M-BRG-6308",nm:"베어링 6308 NSK",cur:6,safe:20,unit:"EA",lt:"2일",used:"25-T-0142, 25-T-0156"},
              ].map((it,i)=>(
                <div key={i} style={{padding:"10px 14px",borderBottom:"1px solid var(--line)",background:it.crit?"var(--danger-soft)":"transparent"}}>
                  <div style={{display:"flex",alignItems:"baseline",gap:8,marginBottom:4}}>
                    <Mgmt size="sm">{it.c}</Mgmt>
                    <span style={{fontWeight:600,fontSize:13}}>{it.nm}</span>
                    {it.crit && <span className="chip" style={{background:"var(--danger)",color:"#fff",height:18,fontSize:10,fontWeight:700,marginLeft:"auto"}}>긴급</span>}
                  </div>
                  <div style={{display:"grid",gridTemplateColumns:"1fr 60px",gap:8,alignItems:"center"}}>
                    <StkBar cur={it.cur} safe={it.safe} max={it.safe*1.5}/>
                    <span className="num" style={{fontSize:11,color:"var(--ink-3)",textAlign:"right"}}>L/T {it.lt}</span>
                  </div>
                  <div style={{fontSize:10.5,color:"var(--ink-3)",marginTop:4}}>사용중 프로젝트: <span className="num" style={{color:"var(--ink-2)"}}>{it.used}</span></div>
                </div>
              ))}
              <div style={{flex:1}}/>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   ② 발주 관리 — 다중 필터바 + sticky 컬럼 + 합계행 + sparkline
   ============================================================ */
const POManage = () => {
  const rows = [
    {n:"PO-25-0148",dt:"01/13",b:"E",v:"신성PCB",vc:"V-024",nm:"PCB 어셈블리 (제어반)",pr:"25-E-0034",q:"6EA",up:"2,066,667",a:"12,400,000",dl:"01/16",lt:"3d",s:"sent",p:"이"},
    {n:"PO-25-0145",dt:"01/13",b:"T",v:"포스코강판",vc:"V-001",nm:"SS400 12t 평판 1500×3000",pr:"25-T-0142",q:"15장",up:"360,000",a:"5,400,000",dl:"01/16",lt:"3d",s:"approved",p:"박"},
    {n:"PO-25-0144",dt:"01/12",b:"T",v:"대성소재",vc:"V-008",nm:"SCM440 ⌀120 환봉 L=1000",pr:"25-T-0142",q:"24EA",up:"175,000",a:"4,200,000",dl:"01/14",lt:"2d",s:"sent",p:"이",urg:1},
    {n:"PO-25-0143",dt:"01/12",b:"M",v:"한국NSK",vc:"V-012",nm:"베어링 6308 N급",pr:"25-T-0156",q:"40EA",up:"60,000",a:"2,400,000",dl:"01/15",lt:"3d",s:"partial",p:"박"},
    {n:"PO-25-0142",dt:"01/11",b:"T",v:"동양철강",vc:"V-005",nm:"S45C ⌀60 환봉 L=2000",pr:"25-T-0156",q:"80EA",up:"40,000",a:"3,200,000",dl:"01/16",lt:"5d",s:"sent",p:"이"},
    {n:"PO-25-0140",dt:"01/10",b:"T",v:"한주물산",vc:"V-018",nm:"GC250 주조품 (하우징)",pr:"25-T-0142",q:"4EA",up:"1,700,000",a:"6,800,000",dl:"01/16",lt:"6d",s:"sent",p:"최"},
    {n:"PO-25-0138",dt:"01/09",b:"M",v:"두산공구",vc:"V-009",nm:"엔드밀 ⌀12 (4F TiAlN)",pr:"25-M-0089",q:"30EA",up:"32,000",a:"960,000",dl:"01/12",lt:"3d",s:"received",p:"박"},
    {n:"PO-25-0137",dt:"01/09",b:"C",v:"태영도장",vc:"V-022",nm:"분체도장 외주 (커버)",pr:"25-C-0021",q:"식",up:"1,800,000",a:"1,800,000",dl:"01/16",lt:"7d",s:"sent",p:"최"},
    {n:"PO-25-0136",dt:"01/08",b:"E",v:"한솔전자",vc:"V-031",nm:"마그네틱 컨택터 (LS)",pr:"25-E-0034",q:"24EA",up:"68,000",a:"1,632,000",dl:"01/13",lt:"5d",s:"received",p:"이"},
    {n:"PO-25-0134",dt:"01/07",b:"T",v:"서일정밀",vc:"V-014",nm:"열처리 외주 (침탄)",pr:"25-T-0142",q:"식",up:"2,200,000",a:"2,200,000",dl:"01/13",lt:"6d",s:"overdue",p:"이",urg:1},
    {n:"PO-25-0132",dt:"01/06",b:"M",v:"한국BAS",vc:"V-016",nm:"체결구 일괄 (M6~M12)",pr:"25-M-0089",q:"식",up:"480,000",a:"480,000",dl:"01/10",lt:"4d",s:"closed",p:"박"},
    {n:"PO-25-0130",dt:"01/05",b:"T",v:"포스코강판",vc:"V-001",nm:"SS400 6t 평판",pr:"25-T-0156",q:"8장",up:"180,000",a:"1,440,000",dl:"01/09",lt:"4d",s:"closed",p:"박"},
  ];
  const total = rows.reduce((s,r)=>s+parseInt(r.a.replace(/,/g,"")),0);
  return (
    <div className="chrome">
      <TopBar/><Sidebar active="po"/>
      <div className="main">
        <PageHead crumb="구매·자재 / 발주" title="발주 관리"
          meta={<>전체 38건 · 진행 18 · 완료 17 · 지연 <span style={{color:"var(--knk-red)",fontWeight:700}}>2</span></>}
          actions={<>
            <div className="seg"><button>📋 표</button><button>📊 칸반</button><button className="is-active">🔬 분석</button></div>
            <button className="btn btn-sm">⤓ Excel</button>
            <button className="btn btn-primary btn-sm">＋ 신규 발주</button>
          </>}/>
        <FilterBar
          chips={[
            {t:"발주일",v:"01/01~01/14",on:1},"|",
            {t:"상태",v:"진행중",on:1},
            {t:"사업부",v:"전체"},
            {t:"공급사",v:"전체"},
            {t:"담당자"},
            {t:"금액"},"|",
            {t:"긴급만 보기",on:1},
          ]}
          search="발주번호 · 품명 · 공급사 검색"
          result={`${rows.length}건 / 전체 38건 · 합계 ${(total/100000000).toFixed(2)}억`}
        />
        <div className="main-body" style={{padding:0,overflow:"hidden",display:"flex",flexDirection:"column"}}>
          {/* mini summary strip */}
          <div style={{display:"grid",gridTemplateColumns:"repeat(8, 1fr)",gap:0,background:"var(--surface)",borderBottom:"1px solid var(--line)"}}>
            {[
              {l:"진행 발주",v:"18",u:"건",sub:"승인 4 · 발주 12 · 부분입고 2"},
              {l:"이번달 발주액",v:"3.62",u:"억",sub:"전월 대비 +8.2%",ok:1},
              {l:"평균 단가",v:"95.4",u:"만원",sub:"전월 동일",neutral:1},
              {l:"평균 리드타임",v:"4.2",u:"일",sub:"-0.6일 단축",ok:1},
              {l:"OTD 율",v:"94.2",u:"%",sub:"공급사 평균",ok:1},
              {l:"긴급 발주",v:"2",u:"건",sub:"비중 12%",warn:1},
              {l:"승인 대기",v:"4",u:"건",sub:"평균 1.8일 대기",neutral:1},
              {l:"미입고 잔액",v:"2.18",u:"억",sub:"입고 예정 14건",neutral:1},
            ].map((s,i)=>(
              <div key={i} style={{padding:"10px 14px",borderRight:i<7?"1px solid var(--line)":"none"}}>
                <div style={{fontSize:10.5,color:"var(--ink-3)",fontWeight:500}}>{s.l}</div>
                <div style={{display:"flex",alignItems:"baseline",gap:3,marginTop:2}}>
                  <span className="num" style={{fontSize:18,fontWeight:700,color:s.warn?"var(--knk-red)":s.ok?"var(--ok)":"var(--ink)"}}>{s.v}</span>
                  <span style={{fontSize:11,color:"var(--ink-4)"}}>{s.u}</span>
                </div>
                <div style={{fontSize:10,color:"var(--ink-4)",marginTop:1}}>{s.sub}</div>
              </div>
            ))}
          </div>

          <div style={{flex:1,overflow:"auto",background:"var(--surface)"}}>
            <table className="tbl tbl-dense" style={{minWidth:1400}}>
              <thead>
                <tr>
                  <th className="sticky-1" style={{width:32}}><input type="checkbox"/></th>
                  <th className="sticky-2" style={{width:104,left:32}}>발주번호</th>
                  <th style={{width:60}}>발주일</th>
                  <th style={{width:50}}>사업부</th>
                  <th style={{width:140}}>공급사</th>
                  <th style={{minWidth:240}}>품명·규격</th>
                  <th style={{width:90}}>프로젝트</th>
                  <th style={{width:60}} className="num">수량</th>
                  <th style={{width:80}} className="num">단가</th>
                  <th style={{width:90}} className="num">금액</th>
                  <th style={{width:60}} className="num">납기</th>
                  <th style={{width:50}} className="num">L/T</th>
                  <th style={{width:80}}>상태</th>
                  <th style={{width:40}}>담당</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r,i)=>(
                  <tr key={r.n} style={{background:r.urg?"var(--danger-soft)":undefined}}>
                    <td className="sticky-1" style={{background:r.urg?"var(--danger-soft)":i%2?"var(--surface-inset)":"var(--surface)"}}><input type="checkbox"/></td>
                    <td className="sticky-2" style={{left:32,background:r.urg?"var(--danger-soft)":i%2?"var(--surface-inset)":"var(--surface)"}}><Mgmt size="sm">{r.n}</Mgmt></td>
                    <td className="num" style={{color:"var(--ink-3)"}}>{r.dt}</td>
                    <td><BizChip biz={r.b}/></td>
                    <td><div style={{display:"flex",alignItems:"center",gap:4}}><span style={{fontWeight:500}}>{r.v}</span><span className="num" style={{fontSize:10,color:"var(--ink-4)"}}>{r.vc}</span></div></td>
                    <td style={{fontWeight:500}}>{r.nm}</td>
                    <td><Mgmt size="sm">{r.pr}</Mgmt></td>
                    <td className="num">{r.q}</td>
                    <td className="num">{r.up}</td>
                    <td className="num" style={{fontWeight:700}}>{r.a}</td>
                    <td className="num" style={{color:r.urg?"var(--danger)":"var(--ink-2)",fontWeight:r.urg?700:500}}>{r.dl}</td>
                    <td className="num" style={{color:"var(--ink-3)"}}>{r.lt}</td>
                    <td><POChip s={r.s}/></td>
                    <td style={{color:"var(--ink-3)"}}>{r.p}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td className="sticky-1"/>
                  <td className="sticky-2" style={{left:32}}>합계 ({rows.length}건)</td>
                  <td colSpan={6}/>
                  <td className="num">평균 360K</td>
                  <td className="num">{total.toLocaleString()}</td>
                  <td colSpan={4} style={{textAlign:"left",color:"var(--ink-3)",fontWeight:500}}>지연 2건 · 미입고 14건</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   ③ BOM·소요량 — 좌측 프로젝트 트리 + 우측 BOM 전개표
   ============================================================ */
const BOMExplosion = () => (
  <div className="chrome">
    <TopBar/><Sidebar active="bom"/>
    <div className="main">
      <PageHead crumb="구매·자재 / BOM" title="BOM·소요량 전개"
        mgmt="25-T-0142"
        meta={<><BizChip biz="T"/> &nbsp;정밀 기어박스 케이스 · 현대중공업 · 납기 25/01/22</>}
        actions={<>
          <div className="seg"><button className="is-active">소요량</button><button>원가</button><button>재고차감</button></div>
          <button className="btn btn-sm">⤓ Excel</button>
          <button className="btn btn-dark btn-sm">→ 일괄 발주 생성 (12)</button>
        </>}/>
      <div className="main-bento" style={{gridTemplateColumns:"260px 1fr",gridTemplateRows:"1fr",gap:12,overflow:"hidden",padding:12}}>
        {/* Left — project list */}
        <div className="card" style={{padding:0,overflow:"hidden"}}>
          <div style={{padding:"10px 14px",borderBottom:"1px solid var(--line)"}}><div className="card-title" style={{fontSize:13}}>진행 프로젝트</div><div className="card-sub" style={{fontSize:10}}>소요량 미확정 5건</div></div>
          <div style={{flex:1,overflow:"auto"}}>
            {[
              {n:"25-T-0142",p:"정밀 기어박스 케이스",b:"T",pct:62,active:1},
              {n:"25-T-0156",p:"베어링 하우징 (3종)",b:"T",pct:100},
              {n:"25-M-0089",p:"엔진 마운트 브라켓",b:"M",pct:18},
              {n:"25-E-0034",p:"제어반 PCB 어셈블리",b:"E",pct:84},
              {n:"25-C-0021",p:"표면처리 코팅 라인",b:"C",pct:32},
            ].map(p=>(
              <div key={p.n} style={{padding:"10px 14px",borderBottom:"1px solid var(--line)",cursor:"pointer",background:p.active?"var(--knk-red-soft)":"transparent",borderLeft:p.active?"3px solid var(--knk-red)":"3px solid transparent"}}>
                <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:4}}><BizChip biz={p.b}/><Mgmt size="sm">{p.n}</Mgmt></div>
                <div style={{fontSize:12,fontWeight:500,marginBottom:4}}>{p.p}</div>
                <Bar pct={p.pct} kind={p.pct===100?"ok":""}/>
                <div className="num" style={{fontSize:10,color:"var(--ink-3)",marginTop:2,textAlign:"right"}}>{p.pct}%</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right — BOM tree explosion */}
        <div className="card" style={{padding:0,overflow:"hidden"}}>
          <div style={{padding:"10px 16px",borderBottom:"1px solid var(--line)",display:"flex",alignItems:"center",gap:8,background:"var(--surface-2)"}}>
            <span style={{fontSize:11,color:"var(--ink-3)",fontWeight:600,letterSpacing:"0.04em"}}>BOM 전개</span>
            <Mgmt size="sm">25-T-0142</Mgmt>
            <span style={{fontSize:12,fontWeight:600}}>정밀 기어박스 케이스</span>
            <span style={{marginLeft:"auto",fontSize:11,color:"var(--ink-3)"}}>총 28 PARTS · 소요 자재 47종 · 부족 <span style={{color:"var(--danger)",fontWeight:700}}>3종</span> · 발주필요 <span style={{color:"var(--warn)",fontWeight:700}}>12종</span></span>
          </div>
          <div style={{flex:1,overflow:"auto"}}>
            <div className="bom-row is-h" style={{gridTemplateColumns:"24px 280px 90px 80px 80px 80px 90px 100px 120px"}}>
              <div></div><div>품목 / 자재</div><div>품번</div><div className="num" style={{textAlign:"right"}}>EA당</div><div className="num" style={{textAlign:"right"}}>총소요</div><div className="num" style={{textAlign:"right"}}>가용재고</div><div className="num" style={{textAlign:"right"}}>부족</div><div>액션</div><div>공급사</div>
            </div>
            {[
              {lv:0,c:"▼",nm:"정밀 기어박스 케이스 (Assy)",pn:"25-T-0142",ea:"-",t:"-",st:"-",sh:"-",a:"",v:""},
              {lv:1,c:"▼",nm:"기어 본체",pn:"P-001",ea:"1",t:"2 EA",st:"4 EA",sh:"0",a:"OK",v:"-"},
              {lv:2,c:"·",nm:"SCM440 ⌀120 환봉",pn:"M-SCM440-D120",ea:"0.8m",t:"1.6m / 24EA",st:"8 EA",sh:"-16 EA",a:"sh",v:"대성소재 ⌐"},
              {lv:2,c:"·",nm:"열처리 외주 (침탄+TF)",pn:"O-HT-CARB",ea:"공정",t:"24 EA",st:"-",sh:"-",a:"po",v:"서일정밀"},
              {lv:1,c:"▼",nm:"입력축",pn:"P-002",ea:"1",t:"2 EA",st:"3 EA",sh:"0",a:"OK",v:"-"},
              {lv:2,c:"·",nm:"SCM435 ⌀45 환봉",pn:"M-SCM435-D45",ea:"0.3m",t:"0.6m / 8EA",st:"22 EA",sh:"+14 EA",a:"OK",v:"대성소재"},
              {lv:2,c:"·",nm:"고주파 열처리",pn:"O-HT-IND",ea:"공정",t:"8 EA",st:"-",sh:"-",a:"po",v:"서일정밀"},
              {lv:1,c:"▼",nm:"출력축",pn:"P-003",ea:"1",t:"2 EA",st:"2 EA",sh:"0",a:"OK"},
              {lv:2,c:"·",nm:"SCM435 ⌀60 환봉",pn:"M-SCM435-D60",ea:"0.32m",t:"0.64m / 16EA",st:"34 EA",sh:"+18 EA",a:"OK",v:"동양철강"},
              {lv:1,c:"▼",nm:"하우징",pn:"P-007",ea:"1",t:"1 EA",st:"0",sh:"-1 EA",a:"po",v:"한주물산 ⌐"},
              {lv:2,c:"·",nm:"GC250 주조품 (소재)",pn:"M-GC250-RAW",ea:"1",t:"4 EA",st:"0",sh:"-4 EA",a:"sh",v:"한주물산"},
              {lv:1,c:"▼",nm:"베어링 캡 A·B",pn:"P-004,005",ea:"4",t:"8 EA",st:"12 EA",sh:"+4 EA",a:"OK"},
              {lv:2,c:"·",nm:"S45C ⌀160×40 블랭크",pn:"M-S45C-160",ea:"1",t:"8 EA",st:"24 EA",sh:"+16 EA",a:"OK",v:"동양철강"},
              {lv:2,c:"·",nm:"흑색산화 처리",pn:"O-SF-OX",ea:"공정",t:"8 EA",st:"-",sh:"-",a:"po",v:"태영도장"},
              {lv:1,c:"▼",nm:"베어링 6308 NSK (인서트)",pn:"M-BRG-6308",ea:"4",t:"8 EA",st:"6 EA",sh:"-2 EA",a:"sh",v:"한국NSK ⌐"},
              {lv:1,c:"▼",nm:"커버 플레이트",pn:"P-006",ea:"1",t:"1 EA",st:"5 EA",sh:"+4 EA",a:"OK"},
              {lv:2,c:"·",nm:"SS400 12t 평판",pn:"M-SS400-12T",ea:"0.09m²",t:"0.09m² / 1장",st:"4 장",sh:"+3 장",a:"OK",v:"포스코강판"},
              {lv:2,c:"·",nm:"분체도장 (블랙)",pn:"O-PT-BLK",ea:"공정",t:"1 식",st:"-",sh:"-",a:"po",v:"태영도장"},
              {lv:1,c:"▼",nm:"체결구 (Bolt/Nut)",pn:"P-FAS",ea:"식",t:"1 식",st:"충분",sh:"0",a:"OK",v:"한국BAS"},
            ].map((r,i)=>{
              const indent = "  ".repeat(r.lv);
              const aClr = r.a==="sh"?"var(--danger)":r.a==="po"?"var(--warn)":r.a==="OK"?"var(--ok)":"var(--ink-4)";
              const aLbl = r.a==="sh"?"부족 → 발주":r.a==="po"?"발주 필요":r.a==="OK"?"충당 가능":"";
              return (
                <div key={i} className="bom-row" style={{gridTemplateColumns:"24px 280px 90px 80px 80px 80px 90px 100px 120px",background:r.lv===0?"var(--surface-3)":r.lv===1?"var(--surface-2)":"transparent",fontWeight:r.lv===0?700:r.lv===1?600:400}}>
                  <div style={{textAlign:"center",color:"var(--ink-3)",fontSize:11}}>{r.c}</div>
                  <div><span className="bom-tw">{indent}</span>{r.nm}</div>
                  <div><Mgmt size="sm">{r.pn}</Mgmt></div>
                  <div className="num" style={{textAlign:"right",color:"var(--ink-3)"}}>{r.ea}</div>
                  <div className="num" style={{textAlign:"right",fontWeight:600}}>{r.t}</div>
                  <div className="num" style={{textAlign:"right"}}>{r.st}</div>
                  <div className="num" style={{textAlign:"right",fontWeight:700,color:r.sh && r.sh.startsWith("-")?"var(--danger)":r.sh && r.sh.startsWith("+")?"var(--ok)":"var(--ink-3)"}}>{r.sh}</div>
                  <div><span style={{fontSize:11,color:aClr,fontWeight:700}}>● {aLbl}</span></div>
                  <div style={{color:"var(--ink-3)",fontSize:11}}>{r.v}</div>
                </div>
              );
            })}
          </div>
          <div style={{padding:"10px 16px",borderTop:"1px solid var(--line)",background:"var(--surface-3)",display:"flex",alignItems:"center",gap:12,fontSize:12}}>
            <span style={{fontWeight:600}}>발주 필요 12종</span>
            <span style={{color:"var(--ink-3)"}}>예상 발주액 <span className="num" style={{color:"var(--ink)",fontWeight:700}}>2,840만원</span></span>
            <span style={{color:"var(--ink-3)"}}>최장 L/T <span className="num" style={{color:"var(--warn)",fontWeight:700}}>6일</span> (한주물산)</span>
            <span style={{color:"var(--ink-3)"}}>리스크 — 납기까지 <span className="num" style={{color:"var(--danger)",fontWeight:700}}>D-8</span></span>
            <button className="btn btn-dark btn-sm" style={{marginLeft:"auto"}}>→ 일괄 PO 생성</button>
          </div>
        </div>
      </div>
    </div>
  </div>
);

/* ============================================================
   ④ 재고 — 창고 사이드 + 재고 표 (안전재고 시각화)
   ============================================================ */
const Inventory = () => {
  const items = [
    {c:"M-SCM440-D120",nm:"SCM440 ⌀120 환봉 L=1000",cat:"환봉",wh:"본사창고",cur:8,safe:24,max:60,unit:"EA",lt:"5d",v:"대성소재",up:"175,000",val:"1,400,000",mv:"-12 / +24 (예정)"},
    {c:"M-SCM435-D45",nm:"SCM435 ⌀45 환봉 L=2000",cat:"환봉",wh:"본사창고",cur:22,safe:20,max:50,unit:"EA",lt:"3d",v:"대성소재",up:"68,000",val:"1,496,000",mv:"-3 / -"},
    {c:"M-SCM435-D60",nm:"SCM435 ⌀60 환봉 L=2000",cat:"환봉",wh:"본사창고",cur:34,safe:30,max:60,unit:"EA",lt:"3d",v:"동양철강",up:"82,000",val:"2,788,000",mv:"-2 / -"},
    {c:"M-S45C-D60",nm:"S45C ⌀60 환봉 L=2000",cat:"환봉",wh:"본사창고",cur:18,safe:40,max:80,unit:"EA",lt:"3d",v:"동양철강",up:"40,000",val:"720,000",mv:"-8 / +80 (예정)"},
    {c:"M-S45C-160",nm:"S45C ⌀160×40 블랭크",cat:"블랭크",wh:"본사창고",cur:24,safe:12,max:40,unit:"EA",lt:"4d",v:"동양철강",up:"32,000",val:"768,000",mv:"-2 / -"},
    {c:"M-SS400-12T",nm:"SS400 12t 평판 1500×3000",cat:"평판",wh:"제2창고",cur:4,safe:6,max:20,unit:"장",lt:"3d",v:"포스코강판",up:"360,000",val:"1,440,000",mv:"-1 / +15 (예정)"},
    {c:"M-SS400-6T",nm:"SS400 6t 평판 1500×3000",cat:"평판",wh:"제2창고",cur:8,safe:6,max:20,unit:"장",lt:"3d",v:"포스코강판",up:"180,000",val:"1,440,000",mv:"0 / -"},
    {c:"M-GC250-RAW",nm:"GC250 주조품 (하우징 소재)",cat:"주조",wh:"제2창고",cur:0,safe:4,max:10,unit:"EA",lt:"6d",v:"한주물산",up:"1,700,000",val:"0",mv:"0 / +4 (D-3)"},
    {c:"M-BRG-6308",nm:"베어링 6308 NSK (N급)",cat:"부품",wh:"본사창고",cur:6,safe:20,max:60,unit:"EA",lt:"2d",v:"한국NSK",up:"60,000",val:"360,000",mv:"-4 / +40 (D-1)"},
    {c:"M-BRG-6310",nm:"베어링 6310 NSK",cat:"부품",wh:"본사창고",cur:18,safe:12,max:40,unit:"EA",lt:"2d",v:"한국NSK",up:"82,000",val:"1,476,000",mv:"-2 / -"},
    {c:"M-FAS-M8",nm:"체결구 M8×40 (스테인리스)",cat:"체결",wh:"본사창고",cur:480,safe:200,max:1000,unit:"EA",lt:"3d",v:"한국BAS",up:"650",val:"312,000",mv:"-40 / -"},
    {c:"M-FAS-M10",nm:"체결구 M10×50 (스테인리스)",cat:"체결",wh:"본사창고",cur:240,safe:200,max:1000,unit:"EA",lt:"3d",v:"한국BAS",up:"950",val:"228,000",mv:"-20 / -"},
  ];
  return (
    <div className="chrome">
      <TopBar/><Sidebar active="stock"/>
      <div className="main">
        <PageHead crumb="구매·자재 / 재고" title="현재고·안전재고"
          meta={<>총 자재 47종 · 본사창고 38 · 제2창고 9 · 미달 <span style={{color:"var(--knk-red)",fontWeight:700}}>3종</span></>}
          actions={<>
            <div className="seg"><button className="is-active">표</button><button>창고맵</button><button>이동이력</button></div>
            <button className="btn btn-sm">실사 시작</button>
            <button className="btn btn-primary btn-sm">＋ 입고 등록</button>
          </>}/>
        <FilterBar
          chips={[
            {t:"창고",v:"전체"},
            {t:"카테고리",v:"전체"},
            {t:"상태",v:"미달만",on:1},"|",
            {t:"공급사"},
            {t:"L/T"},
          ]}
          search="자재코드 · 품명"
          result={`${items.length}종 표시 · 재고가치 합계 12,428,000원`}
        />
        <div className="main-body" style={{padding:0,overflow:"hidden",display:"flex",flexDirection:"column"}}>
          <div style={{flex:1,overflow:"auto",background:"var(--surface)"}}>
            <table className="tbl tbl-dense" style={{minWidth:1400}}>
              <thead><tr>
                <th className="sticky-1" style={{width:32}}><input type="checkbox"/></th>
                <th className="sticky-2" style={{width:120,left:32}}>자재코드</th>
                <th>품명·규격</th>
                <th style={{width:60}}>분류</th>
                <th style={{width:80}}>창고</th>
                <th style={{width:200}}>현재고 / 안전재고</th>
                <th style={{width:60}} className="num">단위</th>
                <th style={{width:50}} className="num">L/T</th>
                <th style={{width:100}}>주공급사</th>
                <th style={{width:80}} className="num">단가</th>
                <th style={{width:90}} className="num">재고가치</th>
                <th style={{width:120}}>최근 이동</th>
              </tr></thead>
              <tbody>
                {items.map((r,i)=>{
                  const lvl = r.cur < r.safe*0.5 ? "is-critical" : r.cur < r.safe ? "is-low" : "";
                  return (
                    <tr key={r.c}>
                      <td className="sticky-1" style={{background:i%2?"var(--surface-inset)":"var(--surface)"}}><input type="checkbox"/></td>
                      <td className="sticky-2" style={{left:32,background:i%2?"var(--surface-inset)":"var(--surface)"}}><Mgmt size="sm">{r.c}</Mgmt></td>
                      <td style={{fontWeight:500}}>{r.nm}</td>
                      <td style={{color:"var(--ink-3)"}}>{r.cat}</td>
                      <td style={{color:"var(--ink-3)"}}>{r.wh}</td>
                      <td>
                        <div style={{position:"relative",height:18,background:"var(--surface-3)",borderRadius:3,overflow:"hidden"}}>
                          <div style={{position:"absolute",left:0,top:0,bottom:0,width:Math.min(100,r.cur/r.max*100)+"%",background:lvl==="is-critical"?"var(--danger)":lvl==="is-low"?"var(--warn)":"var(--ok)"}}/>
                          <div style={{position:"absolute",left:r.safe/r.max*100+"%",top:-2,bottom:-2,width:2,background:"var(--ink)",zIndex:2}}/>
                          <span className="num" style={{position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,fontWeight:700,color:"#fff",mixBlendMode:"difference"}}>{r.cur} / {r.safe}</span>
                        </div>
                      </td>
                      <td className="num" style={{color:"var(--ink-3)"}}>{r.unit}</td>
                      <td className="num" style={{color:"var(--ink-3)"}}>{r.lt}</td>
                      <td style={{color:"var(--ink-3)"}}>{r.v}</td>
                      <td className="num">{r.up}</td>
                      <td className="num" style={{fontWeight:600}}>{r.val}</td>
                      <td className="num" style={{fontSize:10.5,color:"var(--ink-3)"}}>{r.mv}</td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot><tr>
                <td className="sticky-1"/>
                <td className="sticky-2" style={{left:32}}>합계 ({items.length}종)</td>
                <td colSpan={8} style={{textAlign:"left",color:"var(--ink-3)",fontWeight:500}}>
                  미달 3종 · 발주 진행 4종 · 입고 예정 7건
                </td>
                <td className="num">12,428,000</td>
                <td/>
              </tr></tfoot>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   ⑤ 공급사 — OTD율 / 거래액 / 평가 카드 + 표
   ============================================================ */
const VendorMgmt = () => {
  const vendors = [
    {c:"V-001",n:"포스코강판",cat:"평판·코일",t:"전략",otd:96.4,qual:"A",amt:"42.8",lt:3.2,po:38,risk:"low"},
    {c:"V-005",n:"동양철강",cat:"환봉·블랭크",t:"전략",otd:94.2,qual:"A",amt:"38.6",lt:3.8,po:42,risk:"low"},
    {c:"V-008",n:"대성소재",cat:"환봉(특수강)",t:"주력",otd:91.8,qual:"B+",amt:"24.4",lt:4.1,po:28,risk:"med"},
    {c:"V-012",n:"한국NSK",cat:"베어링",t:"단일소스",otd:98.2,qual:"A+",amt:"18.2",lt:2.4,po:18,risk:"high",risk_note:"단일소스 — 대체 검토"},
    {c:"V-014",n:"서일정밀",cat:"열처리 외주",t:"주력",otd:78.4,qual:"B",amt:"22.6",lt:5.8,po:24,risk:"high",risk_note:"OTD 78% · 지난 달 지연 3건"},
    {c:"V-016",n:"한국BAS",cat:"체결구",t:"일반",otd:99.1,qual:"A",amt:"4.8",lt:3.0,po:14,risk:"low"},
    {c:"V-018",n:"한주물산",cat:"주조품",t:"전략",otd:88.6,qual:"B+",amt:"31.2",lt:6.2,po:12,risk:"med"},
    {c:"V-022",n:"태영도장",cat:"표면처리",t:"주력",otd:93.4,qual:"A-",amt:"14.2",lt:5.0,po:22,risk:"low"},
    {c:"V-024",n:"신성PCB",cat:"PCB·기판",t:"전략",otd:95.8,qual:"A",amt:"28.6",lt:7.2,po:16,risk:"low"},
    {c:"V-031",n:"한솔전자",cat:"전기부품",t:"일반",otd:92.0,qual:"B+",amt:"6.4",lt:4.5,po:18,risk:"low"},
  ];
  const totalAmt = vendors.reduce((s,v)=>s+parseFloat(v.amt),0);
  const totalPO = vendors.reduce((s,v)=>s+v.po,0);
  return (
    <div className="chrome">
      <TopBar/><Sidebar active="vendor"/>
      <div className="main">
        <PageHead crumb="구매·자재 / 공급사" title="공급사 관리"
          meta={<>등록 공급사 47개 · 활성 32 · 전략 5 · 단일소스 <span style={{color:"var(--warn)",fontWeight:700}}>3</span></>}
          actions={<>
            <div className="seg"><button className="is-active">스코어카드</button><button>표</button><button>맵</button></div>
            <button className="btn btn-sm">평가 시작</button>
            <button className="btn btn-primary btn-sm">＋ 신규 공급사</button>
          </>}/>
        <FilterBar
          chips={[
            {t:"등급",v:"전략·주력",on:1},
            {t:"카테고리"},
            {t:"OTD",v:"<90%"},
            {t:"리스크",v:"high",on:1},
          ]}
          search="공급사명 · 코드 · 카테고리"
          result={`${vendors.length}/47 · 거래액 ${totalAmt.toFixed(1)}억 · OTD 평균 92.8%`}
        />
        <div className="main-body" style={{padding:16,overflow:"auto"}}>
          <div style={{display:"grid",gridTemplateColumns:"repeat(2, 1fr)",gap:12}}>
            {vendors.map(v=>(
              <div key={v.c} className="card card-tight" style={{padding:14,background:v.risk==="high"?"var(--danger-soft)":"var(--surface)",border:v.risk==="high"?"1px solid var(--knk-red-line)":"1px solid var(--line)",boxShadow:"none"}}>
                <div style={{display:"flex",alignItems:"flex-start",gap:10}}>
                  <div style={{width:42,height:42,borderRadius:8,background:"var(--ink)",color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",fontSize:13,fontWeight:700,flexShrink:0}}>{v.n.slice(0,2)}</div>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:2}}>
                      <Mgmt size="sm">{v.c}</Mgmt>
                      <span className="chip" style={{height:18,fontSize:10,background:v.t==="전략"?"var(--ink)":v.t==="주력"?"var(--info-soft)":v.t==="단일소스"?"var(--warn-soft)":"var(--surface-3)",color:v.t==="전략"?"#fff":v.t==="주력"?"var(--info)":v.t==="단일소스"?"var(--warn)":"var(--ink-3)",fontWeight:600}}>{v.t}</span>
                      <span style={{marginLeft:"auto",fontSize:11,color:"var(--ink-3)"}}>{v.cat}</span>
                    </div>
                    <div style={{fontSize:15,fontWeight:700,letterSpacing:"-0.01em",marginBottom:8}}>{v.n}</div>
                    <div style={{display:"grid",gridTemplateColumns:"repeat(4, 1fr)",gap:8}}>
                      {[
                        {l:"OTD",v:v.otd+"%",c:v.otd>=95?"var(--ok)":v.otd>=90?"var(--ink)":"var(--danger)"},
                        {l:"품질",v:v.qual,c:v.qual.startsWith("A")?"var(--ok)":v.qual.startsWith("B")?"var(--ink)":"var(--danger)"},
                        {l:"거래액",v:v.amt+"억",c:"var(--ink)"},
                        {l:"L/T",v:v.lt+"d",c:"var(--ink-2)"},
                      ].map((m,i)=>(
                        <div key={i} style={{padding:"6px 8px",background:"var(--surface-2)",borderRadius:5}}>
                          <div style={{fontSize:9.5,color:"var(--ink-3)",fontWeight:500,letterSpacing:"0.04em"}}>{m.l}</div>
                          <div className="num" style={{fontSize:14,fontWeight:700,color:m.c,marginTop:1}}>{m.v}</div>
                        </div>
                      ))}
                    </div>
                    {v.risk_note && <div style={{marginTop:8,fontSize:11,color:"var(--danger)",fontWeight:600,padding:"4px 8px",background:"var(--surface)",borderRadius:4}}>⚠ {v.risk_note}</div>}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div style={{marginTop:12,padding:"10px 14px",background:"var(--surface-3)",borderRadius:8,display:"flex",alignItems:"center",gap:16,fontSize:12}}>
            <span style={{fontWeight:700}}>합계</span>
            <span>거래액 <span className="num" style={{fontWeight:700}}>{totalAmt.toFixed(1)}억</span></span>
            <span>발주 <span className="num" style={{fontWeight:700}}>{totalPO}건</span></span>
            <span>OTD 평균 <span className="num" style={{fontWeight:700,color:"var(--ok)"}}>92.8%</span></span>
            <span style={{color:"var(--ink-3)"}}>· 평가 주기 분기 1회</span>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   ⑥ 입고·출고 — 입고 검수 폼 + 자재 출고 기록
   ============================================================ */
const IO = () => (
  <div className="chrome">
    <TopBar/><Sidebar active="io"/>
    <div className="main">
      <PageHead crumb="구매·자재 / 입고·출고" title="입고·출고"
        meta={<>오늘 입고 3건 · 출고 8건 · 검수 대기 2건</>}
        actions={<>
          <div className="seg"><button className="is-active">입고 검수</button><button>자재 출고</button><button>이동 이력</button></div>
          <button className="btn btn-sm">⤓ 일자 보고서</button>
        </>}/>
      <div className="main-bento" style={{gridTemplateColumns:"1fr 1fr",gridTemplateRows:"1fr",gap:12,padding:12}}>
        {/* Left — 입고 검수 폼 */}
        <div className="card" style={{padding:0,overflow:"hidden"}}>
          <div style={{padding:"12px 16px",background:"var(--surface-2)",borderBottom:"1px solid var(--line)"}}>
            <div style={{display:"flex",alignItems:"center",gap:8}}>
              <span style={{fontSize:11,color:"var(--ink-3)",fontWeight:600,letterSpacing:"0.04em"}}>입고 검수</span>
              <Mgmt size="sm">PO-25-0143</Mgmt>
              <span style={{fontSize:13,fontWeight:600}}>한국NSK · 베어링 6308</span>
              <POChip s="partial"/>
            </div>
            <div style={{fontSize:11,color:"var(--ink-3)",marginTop:4}}>발주일 01/12 · 납기 01/15 · 발주수량 40 EA · 단가 60,000원</div>
          </div>
          <div style={{flex:1,overflow:"auto",padding:16}}>
            {/* 발주 개요 */}
            <div style={{display:"grid",gridTemplateColumns:"repeat(4, 1fr)",gap:8,marginBottom:14,padding:12,background:"var(--surface-2)",borderRadius:8}}>
              {[["발주수량","40 EA"],["기입고","20 EA"],["이번 입고","20 EA"],["잔량","0 EA"]].map(([l,v],i)=>(
                <div key={i}>
                  <div style={{fontSize:10,color:"var(--ink-3)",fontWeight:500}}>{l}</div>
                  <div className="num" style={{fontSize:18,fontWeight:700,marginTop:1,color:i===3?"var(--ok)":"var(--ink)"}}>{v}</div>
                </div>
              ))}
            </div>
            {/* 검수 폼 */}
            <div style={{display:"flex",flexDirection:"column",gap:10}}>
              {[
                {l:"입고일자",v:"2025-01-14 10:24"},
                {l:"인수자",v:"박 차장"},
                {l:"송장번호",v:"NSK-INV-20250114-038"},
                {l:"실제 수량",v:"20 EA",ok:1},
                {l:"수량 차이",v:"0 EA",ok:1},
                {l:"외관 검사",v:"양호 (라벨/포장 OK)",ok:1},
                {l:"치수 검사",v:"규격 일치",ok:1},
                {l:"품질 등급",v:"A — 양품"},
              ].map((f,i)=>(
                <div key={i} style={{display:"grid",gridTemplateColumns:"100px 1fr 24px",gap:10,alignItems:"center",padding:"6px 0",borderBottom:"1px solid var(--line)"}}>
                  <span style={{fontSize:12,color:"var(--ink-3)",fontWeight:500}}>{f.l}</span>
                  <span style={{fontSize:13,fontWeight:f.ok?600:500}}>{f.v}</span>
                  {f.ok && <span style={{color:"var(--ok)",fontSize:14}}>✓</span>}
                </div>
              ))}
            </div>
            <div style={{marginTop:14}}>
              <div style={{fontSize:11,color:"var(--ink-3)",fontWeight:500,marginBottom:6}}>특이사항 / 메모</div>
              <textarea className="textarea" style={{minHeight:60,fontSize:13}} defaultValue="포장 양호. 시트지 라벨 일치. 5개 단위 박스 4개 — 모두 미개봉 정상 인수."/>
            </div>
            <div style={{marginTop:14,padding:12,background:"var(--ok-soft)",border:"1px solid #a7f3d0",borderRadius:8,display:"flex",alignItems:"center",gap:10}}>
              <div style={{width:32,height:32,borderRadius:"50%",background:"var(--ok)",color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",fontWeight:700}}>✓</div>
              <div style={{flex:1}}>
                <div style={{fontSize:13,fontWeight:700,color:"var(--ok)"}}>검수 완료 — 발주 종결 가능</div>
                <div style={{fontSize:11,color:"var(--ink-3)",marginTop:2}}>본사창고 입고 / 자재코드 M-BRG-6308 재고 +20 EA</div>
              </div>
            </div>
          </div>
          <div style={{padding:"10px 16px",borderTop:"1px solid var(--line)",display:"flex",gap:8}}>
            <button className="btn btn-sm">반려 (수량 부족)</button>
            <button className="btn btn-sm">일부 입고 처리</button>
            <button className="btn btn-dark btn-sm" style={{marginLeft:"auto"}}>검수 확정 + 발주 종결</button>
          </div>
        </div>

        {/* Right — 자재 출고 (프로젝트로) */}
        <div className="card" style={{padding:0,overflow:"hidden"}}>
          <div style={{padding:"12px 16px",background:"var(--surface-2)",borderBottom:"1px solid var(--line)",display:"flex",alignItems:"center",gap:8}}>
            <span style={{fontSize:11,color:"var(--ink-3)",fontWeight:600,letterSpacing:"0.04em"}}>오늘 자재 출고</span>
            <span style={{fontSize:13,fontWeight:600,marginLeft:4}}>8건 · 4 프로젝트</span>
            <button className="btn btn-primary btn-sm" style={{marginLeft:"auto",height:24,padding:"0 8px",fontSize:11}}>＋ 출고 등록</button>
          </div>
          <div style={{flex:1,overflow:"auto"}}>
            <table className="tbl tbl-dense">
              <thead><tr>
                <th style={{width:50}} className="num">시각</th>
                <th style={{width:100}}>자재코드</th>
                <th>품명</th>
                <th style={{width:50}} className="num">수량</th>
                <th style={{width:100}}>프로젝트</th>
                <th style={{width:80}}>공정·작업자</th>
                <th style={{width:60}} className="num">잔여재고</th>
              </tr></thead>
              <tbody>
                {[
                  {t:"09:14",c:"M-S45C-160",nm:"S45C ⌀160×40 블랭크",q:"4 EA",pr:"25-T-0142",p:"선반 · 이",rm:"24"},
                  {t:"09:32",c:"M-SCM435-D60",nm:"SCM435 ⌀60 환봉",q:"2 EA",pr:"25-T-0156",p:"선반 · 박",rm:"34"},
                  {t:"10:08",c:"M-FAS-M8",nm:"체결구 M8×40",q:"40 EA",pr:"25-T-0142",p:"조립 · 김",rm:"480"},
                  {t:"10:42",c:"M-SCM435-D45",nm:"SCM435 ⌀45 환봉",q:"3 EA",pr:"25-T-0142",p:"선반 · 이",rm:"22"},
                  {t:"11:18",c:"M-BRG-6310",nm:"베어링 6310 NSK",q:"2 EA",pr:"25-T-0156",p:"조립 · 김",rm:"18"},
                  {t:"13:24",c:"M-S45C-D60",nm:"S45C ⌀60 환봉",q:"8 EA",pr:"25-T-0156",p:"선반 · 박",rm:"18",low:1},
                  {t:"14:06",c:"M-SS400-12T",nm:"SS400 12t 평판",q:"1 장",pr:"25-T-0142",p:"레이저 · 최",rm:"4"},
                  {t:"15:38",c:"M-SCM440-D120",nm:"SCM440 ⌀120 환봉",q:"12 EA",pr:"25-T-0142",p:"선반 · 이",rm:"8",low:1,crit:1},
                ].map((r,i)=>(
                  <tr key={i} style={{background:r.crit?"var(--danger-soft)":undefined}}>
                    <td className="num" style={{color:"var(--ink-3)"}}>{r.t}</td>
                    <td><Mgmt size="sm">{r.c}</Mgmt></td>
                    <td>{r.nm}</td>
                    <td className="num" style={{fontWeight:600}}>{r.q}</td>
                    <td><Mgmt size="sm">{r.pr}</Mgmt></td>
                    <td style={{color:"var(--ink-3)",fontSize:11}}>{r.p}</td>
                    <td className="num" style={{fontWeight:700,color:r.crit?"var(--danger)":r.low?"var(--warn)":"var(--ink)"}}>{r.rm}{r.crit && " ⚠"}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot><tr>
                <td colSpan={3}>합계 (8건)</td>
                <td className="num">72 단위</td>
                <td colSpan={3} style={{textAlign:"left",color:"var(--ink-3)",fontWeight:500}}>4개 프로젝트 / 안전재고 미달 발생 1건</td>
              </tr></tfoot>
            </table>
          </div>
          <div style={{padding:"10px 14px",background:"var(--knk-red-soft)",borderTop:"1px solid var(--knk-red-line)",display:"flex",alignItems:"center",gap:10,fontSize:12}}>
            <span style={{color:"var(--knk-red)",fontWeight:700}}>⚠ 안전재고 미달 발생</span>
            <Mgmt size="sm">M-SCM440-D120</Mgmt>
            <span>현재 8 EA / 안전재고 24 EA</span>
            <button className="btn btn-primary btn-sm" style={{marginLeft:"auto",height:24,padding:"0 8px",fontSize:11}}>긴급 발주 →</button>
          </div>
        </div>
      </div>
    </div>
  </div>
);

/* ============================================================
   App — 통합 마운트
   ============================================================ */
const App = () => (
  <DesignCanvas title="HAIST WORKS · 시안 1" subtitle="Quiet Ops — ERP-grade · 다중 필터바 / sticky 컬럼 / 합계행 / 정보 밀도 ↑">
    <DCSection id="po" title="STEP 2 · 구매·자재 (신규 · 6 페이지)" subtitle="다중 필터바 · sticky 컬럼 · 합계행 · BOM 트리 · 안전재고 시각화">
      <DCArtboard id="po-home" label="① 구매 홈 — 6 KPI + 발주 흐름 + 사업부 비교 + 입고 임박 + 부족 알림" width={1440} height={900}><PurchaseHome/></DCArtboard>
      <DCArtboard id="po-manage" label="② 발주 관리 — 다중 필터바 + sticky 2컬럼 + 합계행 + 8 KPI 스트립" width={1440} height={900}><POManage/></DCArtboard>
      <DCArtboard id="bom" label="③ BOM·소요량 — 좌 프로젝트 / 우 BOM 전개 (가용재고 · 부족수량 · 액션)" width={1440} height={900}><BOMExplosion/></DCArtboard>
      <DCArtboard id="stock" label="④ 재고 — 안전재고 시각화 / 창고별 / 재고가치" width={1440} height={900}><Inventory/></DCArtboard>
      <DCArtboard id="vendor" label="⑤ 공급사 — OTD/품질/거래액 스코어카드 + 리스크 표시" width={1440} height={900}><VendorMgmt/></DCArtboard>
      <DCArtboard id="io" label="⑥ 입고·출고 — 검수 폼 + 자재 출고 기록 + 안전재고 미달 알림" width={1440} height={900}><IO/></DCArtboard>
    </DCSection>
    <DCSection id="pages" title="STEP 1 · 영업·생산 (기존 5 페이지)" subtitle="동일 토큰 / 같은 ERP 톤으로 정렬">
      <DCArtboard id="sales-home" label="① 매출 홈" width={1440} height={900}><SalesHome/></DCArtboard>
      <DCArtboard id="orders" label="② 수주 관리 — 캘린더 + 일정" width={1440} height={900}><OrdersPage/></DCArtboard>
      <DCArtboard id="project" label="③ 프로젝트 상세 — PARTS 28컬럼" width={1440} height={900}><ProjectDetail/></DCArtboard>
      <DCArtboard id="calendar" label="④ 캘린더" width={1440} height={900}><CalendarPage/></DCArtboard>
      <DCArtboard id="daily" label="⑤ 일일 업무" width={1440} height={900}><DailyWork/></DCArtboard>
    </DCSection>
    <DCSection id="tokens" title="토큰·컴포넌트">
      <DCArtboard id="tokens" label="토큰 시스템" width={1280} height={1100}><TokensV2/></DCArtboard>
      <DCArtboard id="components" label="공통 컴포넌트" width={1280} height={1000}><ComponentsV2/></DCArtboard>
    </DCSection>
    <DCSection id="closing" title="마무리">
      <DCArtboard id="closing" label="v1 → v2 · 무엇이 달라졌나" width={1100} height={760}><Closing/></DCArtboard>
    </DCSection>
  </DesignCanvas>
);

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
