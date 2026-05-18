/* HAIST WORKS · v2 Mockups — Quiet Ops aesthetic
 * Bento layouts · cool neutrals · single accent · inline data viz
 */

/* ============================================================
   Primitives
   ============================================================ */
const TopBar = ({ user = "김 부장 (영업1팀)" }) => (
  <div className="topbar">
    <div className="brand">
      <div style={{width:24,height:24,borderRadius:6,background:"var(--ink)",display:"flex",alignItems:"center",justifyContent:"center",color:"#fff",fontSize:12,fontWeight:800,letterSpacing:"-0.02em"}}>K</div>
      <div style={{fontSize:14,fontWeight:700,letterSpacing:"-0.01em"}}>HAIST WORKS</div>
      <div style={{fontSize:11,color:"var(--ink-4)",marginLeft:6,fontWeight:500}}>v5.0</div>
    </div>
    <nav>
      <a className="is-active">대시보드</a>
      <a>프로젝트</a>
      <a>고객사</a>
      <a>결재</a>
      <a>리포트</a>
    </nav>
    <div style={{marginLeft:"auto",display:"flex",gap:8,alignItems:"center"}}>
      <div style={{position:"relative",width:240}}>
        <input className="input" style={{height:34,fontSize:13,paddingLeft:30}} placeholder="검색 (관리번호 · 거래처 · 프로젝트)" />
        <div style={{position:"absolute",left:10,top:9,fontSize:14,color:"var(--ink-4)"}}>⌕</div>
      </div>
      <button className="btn btn-icon btn-sm" style={{height:34,width:34}}>
        <span style={{fontSize:14}}>🔔</span>
      </button>
      <div style={{display:"flex",alignItems:"center",gap:8,padding:"4px 8px",borderRadius:8,background:"var(--surface-2)"}}>
        <div style={{width:24,height:24,borderRadius:"50%",background:"var(--biz-m)",color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",fontSize:11,fontWeight:700}}>김</div>
        <div style={{fontSize:12,fontWeight:500}}>{user}</div>
      </div>
    </div>
  </div>
);

const Sidebar = ({ active = "sales-home" }) => {
  const items = [
    {g:"영업"},
    {id:"sales-home", e:"📊", t:"매출 홈", b:""},
    {id:"orders", e:"📑", t:"수주 관리", b:"24"},
    {id:"quotes", e:"📝", t:"견적 관리", b:"7"},
    {id:"customers", e:"🏢", t:"고객사", b:""},
    {id:"receivables", e:"💰", t:"미수금", b:"12"},
    {g:"구매·자재"},
    {id:"po-home", e:"🧭", t:"구매 홈", b:""},
    {id:"po", e:"🛒", t:"발주 관리", b:"18"},
    {id:"bom", e:"🧬", t:"BOM·소요량", b:""},
    {id:"stock", e:"📦", t:"재고", b:"3"},
    {id:"vendor", e:"🤝", t:"공급사", b:""},
    {id:"io", e:"🚛", t:"입고·출고", b:""},
    {g:"생산"},
    {id:"projects", e:"📦", t:"프로젝트", b:"38"},
    {id:"production", e:"🛠", t:"생산 현황", b:""},
    {id:"shipments", e:"🚚", t:"납품·수금", b:""},
    {g:"공통"},
    {id:"daily", e:"✅", t:"일일 업무", b:"8"},
    {id:"calendar", e:"📅", t:"캘린더", b:""},
    {id:"approvals", e:"📨", t:"결재함", b:"3"},
  ];
  return (
    <div className="sidebar">
      {items.map((it,i)=> it.g
        ? <div key={i} className="sb-group">{it.g}</div>
        : <div key={i} className={"sb-item"+(active===it.id?" is-active":"")}>
            <span className="sb-emoji">{it.e}</span>
            <span>{it.t}</span>
            {it.b && <span className="sb-badge">{it.b}</span>}
          </div>
      )}
    </div>
  );
};

const PageHead = ({ crumb, title, mgmt, badges = [], meta, actions }) => (
  <div className="page-head">
    <div>
      {crumb && <div className="crumb">{crumb}</div>}
      <div className="page-title">
        {title}
        {mgmt && <span className="mgmt-no mgmt-no-lg">{mgmt}</span>}
        {badges.map((b,i)=>b)}
      </div>
    </div>
    {meta && <div className="meta-line" style={{marginLeft:16,paddingLeft:16,borderLeft:"1px solid var(--line-2)"}}>{meta}</div>}
    {actions && <div className="page-actions">{actions}</div>}
  </div>
);

/* ============================================================
   Inline data viz
   ============================================================ */
const Sparkline = ({ data, color = "currentColor", w = 80, h = 32, area = true }) => {
  const min = Math.min(...data), max = Math.max(...data);
  const range = max - min || 1;
  const pts = data.map((v, i) => [i / (data.length - 1) * w, h - ((v - min) / range) * (h - 4) - 2]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const areaD = area ? d + ` L${w} ${h} L0 ${h} Z` : "";
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width={w} height={h} style={{display:"block"}}>
      {area && <path d={areaD} fill={color} fillOpacity="0.08" />}
      <path d={d} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length-1][0]} cy={pts[pts.length-1][1]} r="2.5" fill={color} />
    </svg>
  );
};

const Bar = ({ pct, kind = "" }) => (
  <div className={"bar" + (kind ? " is-" + kind : "")}>
    <i style={{ width: Math.min(100, Math.max(0, pct)) + "%" }} />
  </div>
);

const Trend = ({ dir, value }) => {
  const arrow = dir === "up" ? "↗" : dir === "down" ? "↘" : "→";
  return <span className={"kpi-trend " + dir}>{arrow} {value}</span>;
};

/* ============================================================
   Mgmt-no & chips
   ============================================================ */
const Mgmt = ({ children, size }) => <span className={"mgmt-no" + (size === "sm" ? " mgmt-no-sm" : size === "lg" ? " mgmt-no-lg" : "")}>{children}</span>;
const BizChip = ({ biz }) => {
  const map = { T: "T 정밀", M: "M 가공", E: "E 전기", C: "C 화학" };
  return <span className={"chip-biz biz-" + biz.toLowerCase()}>{map[biz]}</span>;
};
const StatusChip = ({ status }) => {
  const map = {
    draft: ["s-draft", "초안"],
    confirmed: ["s-confirmed", "확정"],
    "in-production": ["s-in-production", "생산중"],
    shipped: ["s-shipped", "납품"],
    invoiced: ["s-invoiced", "청구"],
    paid: ["s-paid", "수금완료"],
    cancelled: ["s-cancelled", "취소"],
  };
  const [cls, label] = map[status] || ["s-draft", status];
  return <span className={"chip-status " + cls}><span className="dot"/>{label}</span>;
};

/* ============================================================
   1. SALES HOME (매출 홈) — Bento, no scroll
   ============================================================ */
const SalesHome = () => {
  const sparkSales = [320,340,310,380,420,400,460,510,490,540,580,620];
  const sparkOrders = [12,15,11,18,22,20,24,28,26,30,32,35];
  const sparkRecv = [820,840,830,810,790,820,800,780,760,740,710,690];
  return (
    <div className="chrome">
      <TopBar />
      <Sidebar active="sales-home" />
      <div className="main">
        <PageHead
          crumb="영업"
          title="매출 홈"
          meta={<>2025년 1월 · 영업1팀 김 부장 · <span className="num">10:24</span> 갱신</>}
          actions={<>
            <div className="seg">
              <button>일</button>
              <button>주</button>
              <button className="is-active">월</button>
              <button>분기</button>
              <button>연</button>
            </div>
            <button className="btn btn-sm">⤓ 내보내기</button>
            <button className="btn btn-primary btn-sm">＋ 견적 등록</button>
          </>}
        />
        <div className="main-bento" style={{gridTemplateColumns:"repeat(12, 1fr)",gridTemplateRows:"auto auto 1fr",gap:16}}>
          {/* KPI Row */}
          <div className="kpi" style={{gridColumn:"1 / 4"}}>
            <div className="kpi-label">이번 달 매출 <span style={{color:"var(--ink-4)"}}>억</span></div>
            <div><span className="kpi-value">62.4</span></div>
            <Trend dir="up" value="전월 대비 +12.4%" />
            <div className="kpi-spark"><Sparkline data={sparkSales} color="#0f172a" w={100} h={32} /></div>
          </div>
          <div className="kpi" style={{gridColumn:"4 / 7"}}>
            <div className="kpi-label">신규 수주 <span style={{color:"var(--ink-4)"}}>건</span></div>
            <div><span className="kpi-value">35</span></div>
            <Trend dir="up" value="전월 대비 +9건" />
            <div className="kpi-spark"><Sparkline data={sparkOrders} color="#1e5fbf" w={100} h={32} /></div>
          </div>
          <div className="kpi" style={{gridColumn:"7 / 10"}}>
            <div className="kpi-label">미수금 <span style={{color:"var(--ink-4)"}}>억</span></div>
            <div><span className="kpi-value">6.9</span><span className="kpi-unit">/ 84.2</span></div>
            <Trend dir="down" value="전월 대비 -3.4%" />
            <div className="kpi-spark"><Sparkline data={sparkRecv} color="#0d7c4f" w={100} h={32} /></div>
          </div>
          <div className="kpi" style={{gridColumn:"10 / 13",background:"var(--ink)",color:"#fff"}}>
            <div className="kpi-label" style={{color:"rgba(255,255,255,0.6)"}}>목표 달성률</div>
            <div><span className="kpi-value" style={{color:"#fff"}}>78</span><span className="kpi-unit" style={{color:"rgba(255,255,255,0.6)"}}>%</span></div>
            <div style={{marginTop:8}}>
              <div className="bar" style={{background:"rgba(255,255,255,0.15)"}}><i style={{width:"78%",background:"#fff"}}/></div>
              <div style={{fontSize:11,marginTop:6,color:"rgba(255,255,255,0.7)"}}>62.4 / 80.0 (억) · 잔여 17.6</div>
            </div>
          </div>

          {/* Mid row — 사업부별 매출 / 일별 매출 */}
          <div className="card" style={{gridColumn:"1 / 8"}}>
            <div className="card-head">
              <div>
                <div className="card-title">사업부별 매출 분포</div>
                <div className="card-sub">정밀(T) · 가공(M) · 전기(E) · 화학(C)</div>
              </div>
              <div className="seg">
                <button className="is-active">금액</button>
                <button>건수</button>
                <button>마진</button>
              </div>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:24,flex:1}}>
              <div style={{display:"flex",flexDirection:"column",gap:14,justifyContent:"center"}}>
                {[
                  {biz:"T",label:"정밀",val:24.8,pct:39.7,color:"#c2410c"},
                  {biz:"M",label:"가공",val:18.2,pct:29.2,color:"#1e40af"},
                  {biz:"E",label:"전기",val:12.6,pct:20.2,color:"#6d28d9"},
                  {biz:"C",label:"화학",val:6.8,pct:10.9,color:"#047857"},
                ].map(d=>(
                  <div key={d.biz}>
                    <div style={{display:"flex",justifyContent:"space-between",alignItems:"baseline",marginBottom:6}}>
                      <div style={{display:"flex",alignItems:"center",gap:8}}>
                        <div style={{width:10,height:10,borderRadius:2,background:d.color}}/>
                        <span style={{fontWeight:600,fontSize:14}}>{d.label}</span>
                      </div>
                      <div style={{fontFamily:"var(--font-mono)",fontSize:14,fontWeight:600}}>
                        {d.val} <span style={{color:"var(--ink-4)",fontSize:11}}>억 · {d.pct}%</span>
                      </div>
                    </div>
                    <div className="bar"><i style={{width:d.pct+"%",background:d.color}}/></div>
                  </div>
                ))}
              </div>
              {/* Donut */}
              <div style={{display:"flex",alignItems:"center",justifyContent:"center"}}>
                <svg viewBox="0 0 200 200" width="220" height="220">
                  {(()=>{
                    const data = [{p:39.7,c:"#c2410c"},{p:29.2,c:"#1e40af"},{p:20.2,c:"#6d28d9"},{p:10.9,c:"#047857"}];
                    let acc = 0; const r = 70, cx = 100, cy = 100;
                    return data.map((d,i)=>{
                      const a0 = acc*Math.PI*2 - Math.PI/2;
                      acc += d.p/100;
                      const a1 = acc*Math.PI*2 - Math.PI/2;
                      const x0 = cx + r*Math.cos(a0), y0 = cy + r*Math.sin(a0);
                      const x1 = cx + r*Math.cos(a1), y1 = cy + r*Math.sin(a1);
                      const large = (a1-a0) > Math.PI ? 1 : 0;
                      return <path key={i} d={`M${cx} ${cy} L${x0} ${y0} A${r} ${r} 0 ${large} 1 ${x1} ${y1} Z`} fill={d.c}/>;
                    });
                  })()}
                  <circle cx="100" cy="100" r="44" fill="#fff"/>
                  <text x="100" y="96" textAnchor="middle" fontSize="11" fill="var(--ink-3)" fontFamily="Pretendard">총 매출</text>
                  <text x="100" y="118" textAnchor="middle" fontSize="22" fontWeight="700" fill="var(--ink)" fontFamily="ui-monospace, monospace" letterSpacing="-0.04em">62.4 억</text>
                </svg>
              </div>
            </div>
          </div>

          <div className="card" style={{gridColumn:"8 / 13"}}>
            <div className="card-head">
              <div className="card-title">일별 매출 추이</div>
              <div className="card-sub">최근 14일</div>
            </div>
            <div style={{flex:1,display:"flex",alignItems:"flex-end",gap:6,padding:"12px 0"}}>
              {[18,22,16,28,32,12,8,24,30,38,42,36,52,44].map((v,i)=>(
                <div key={i} style={{flex:1,display:"flex",flexDirection:"column",alignItems:"center",gap:4}}>
                  <div style={{width:"100%",height:v*3,background:i===13?"var(--knk-red)":"var(--ink)",opacity:i===13?1:0.2+i*0.06,borderRadius:"3px 3px 0 0",transition:"all .2s"}}/>
                  <div style={{fontSize:10,color:"var(--ink-4)",fontFamily:"var(--font-mono)"}}>{i+1}</div>
                </div>
              ))}
            </div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:11,color:"var(--ink-3)",paddingTop:8,borderTop:"1px solid var(--line)"}}>
              <span>1월 1일</span>
              <span style={{color:"var(--knk-red)",fontWeight:600}}>● 오늘 5.2 억</span>
              <span>1월 14일</span>
            </div>
          </div>

          {/* Bottom row — 진행 중인 프로젝트 + 곧 도래 마일스톤 */}
          <div className="card" style={{gridColumn:"1 / 8",overflow:"hidden"}}>
            <div className="card-head">
              <div className="card-title">진행 중인 프로젝트 <span style={{color:"var(--ink-4)",fontSize:13,fontWeight:500,marginLeft:6}}>38건</span></div>
              <button className="btn btn-ghost btn-sm">전체 보기 →</button>
            </div>
            <div style={{flex:1,overflow:"auto",margin:"-4px -4px"}}>
              <table className="tbl tbl-compact">
                <thead><tr>
                  <th style={{width:90}}>관리번호</th>
                  <th style={{width:60}}>사업부</th>
                  <th>프로젝트</th>
                  <th style={{width:100}}>거래처</th>
                  <th style={{width:90}}>상태</th>
                  <th style={{width:140}}>진척률</th>
                  <th style={{width:80}} className="num">금액</th>
                </tr></thead>
                <tbody>
                  {[
                    {n:"25-T-0142",b:"T",p:"정밀 기어박스 케이스",c:"현대중공업",s:"in-production",pct:62,amt:"3.2"},
                    {n:"25-M-0089",b:"M",p:"엔진 마운트 브라켓",c:"두산밥캣",s:"confirmed",pct:18,amt:"1.8"},
                    {n:"25-E-0034",b:"E",p:"제어반 PCB 어셈블리",c:"한국전력",s:"in-production",pct:84,amt:"2.4"},
                    {n:"25-T-0156",b:"T",p:"베어링 하우징 (3종)",c:"포스코",s:"shipped",pct:100,amt:"4.1"},
                    {n:"25-C-0021",b:"C",p:"표면처리 코팅 라인",c:"LG화학",s:"confirmed",pct:32,amt:"5.6"},
                  ].map(r=>(
                    <tr key={r.n}>
                      <td><Mgmt size="sm">{r.n}</Mgmt></td>
                      <td><BizChip biz={r.b}/></td>
                      <td style={{fontWeight:500}}>{r.p}</td>
                      <td style={{color:"var(--ink-3)"}}>{r.c}</td>
                      <td><StatusChip status={r.s}/></td>
                      <td>
                        <div style={{display:"flex",alignItems:"center",gap:8}}>
                          <div style={{flex:1}}><Bar pct={r.pct} kind={r.pct===100?"ok":r.pct>=80?"info":r.pct<=20?"warn":""}/></div>
                          <span className="num" style={{fontSize:11,color:"var(--ink-3)",minWidth:30,textAlign:"right"}}>{r.pct}%</span>
                        </div>
                      </td>
                      <td className="num" style={{fontWeight:600}}>{r.amt}<span style={{color:"var(--ink-4)",marginLeft:2,fontSize:10}}>억</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card" style={{gridColumn:"8 / 13",overflow:"hidden"}}>
            <div className="card-head">
              <div className="card-title">곧 도래 · 일정</div>
              <div className="seg" style={{transform:"scale(0.95)"}}>
                <button className="is-active">7일</button>
                <button>14일</button>
                <button>30일</button>
              </div>
            </div>
            <div style={{flex:1,overflow:"auto",display:"flex",flexDirection:"column",gap:8}}>
              {[
                {d:"오늘",dt:"01/14",t:"포스코 — 베어링 하우징 납품",sub:"25-T-0156",urg:"high"},
                {d:"내일",dt:"01/15",t:"한국전력 — 중간 검수 일정",sub:"25-E-0034",urg:""},
                {d:"D-3",dt:"01/17",t:"현대중공업 — 1차 검수",sub:"25-T-0142",urg:""},
                {d:"D-4",dt:"01/18",t:"두산밥캣 — 견적 회신 마감",sub:"Q25-M-0034",urg:"high"},
                {d:"D-6",dt:"01/20",t:"LG화학 — 코팅 라인 시작",sub:"25-C-0021",urg:""},
                {d:"D-7",dt:"01/21",t:"분기 정산 마감",sub:"내부 일정",urg:""},
              ].map((it,i)=>(
                <div key={i} style={{display:"flex",gap:12,padding:"10px 12px",borderRadius:8,background:i===0?"var(--knk-red-soft)":"var(--surface-2)",border:i===0?"1px solid var(--knk-red-line)":"1px solid transparent"}}>
                  <div style={{minWidth:48,textAlign:"center"}}>
                    <div style={{fontSize:11,fontWeight:600,color:i===0?"var(--knk-red)":it.urg==="high"?"var(--warn)":"var(--ink-3)"}}>{it.d}</div>
                    <div style={{fontFamily:"var(--font-mono)",fontSize:10,color:"var(--ink-4)",marginTop:2}}>{it.dt}</div>
                  </div>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontSize:13,fontWeight:500,marginBottom:2,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis"}}>{it.t}</div>
                    <div style={{fontSize:11,color:"var(--ink-3)",fontFamily:"var(--font-mono)"}}>{it.sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   2. ORDERS (수주 관리) — Calendar + List, no page scroll
   ============================================================ */
const OrdersPage = () => {
  return (
    <div className="chrome">
      <TopBar />
      <Sidebar active="orders" />
      <div className="main">
        <PageHead
          crumb="영업 / 수주"
          title="수주 관리"
          meta={<>전체 38건 · 진행 24 · 완료 11 · 취소 3</>}
          actions={<>
            <div className="seg">
              <button>📋 표</button>
              <button className="is-active">📅 캘린더</button>
              <button>📊 차트</button>
            </div>
            <button className="btn btn-sm">필터 ⌄</button>
            <button className="btn btn-primary btn-sm">＋ 신규 수주</button>
          </>}
        />
        <div className="main-bento" style={{gridTemplateColumns:"1fr 360px",gridTemplateRows:"1fr",gap:16,overflow:"hidden"}}>
          {/* Calendar */}
          <div className="card" style={{padding:0,overflow:"hidden"}}>
            <div style={{padding:"16px 20px",borderBottom:"1px solid var(--line)",display:"flex",alignItems:"center",gap:12}}>
              <button className="btn btn-icon btn-sm">←</button>
              <h3 style={{fontSize:18,fontWeight:700}}>2025년 1월</h3>
              <button className="btn btn-icon btn-sm">→</button>
              <button className="btn btn-sm" style={{marginLeft:8}}>오늘</button>
              <div style={{marginLeft:"auto",display:"flex",gap:14,fontSize:11,color:"var(--ink-3)"}}>
                <span style={{display:"flex",alignItems:"center",gap:6}}><span style={{width:8,height:8,borderRadius:2,background:"#c2410c"}}/>정밀 T</span>
                <span style={{display:"flex",alignItems:"center",gap:6}}><span style={{width:8,height:8,borderRadius:2,background:"#1e40af"}}/>가공 M</span>
                <span style={{display:"flex",alignItems:"center",gap:6}}><span style={{width:8,height:8,borderRadius:2,background:"#6d28d9"}}/>전기 E</span>
                <span style={{display:"flex",alignItems:"center",gap:6}}><span style={{width:8,height:8,borderRadius:2,background:"#047857"}}/>화학 C</span>
              </div>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(7, 1fr)",borderBottom:"1px solid var(--line)"}}>
              {["월","화","수","목","금","토","일"].map((d,i)=>(
                <div key={d} style={{padding:"8px 12px",fontSize:11,fontWeight:600,color:i>=5?"var(--ink-4)":"var(--ink-3)",letterSpacing:"0.04em"}}>{d}</div>
              ))}
            </div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(7, 1fr)",gridTemplateRows:"repeat(5, 1fr)",flex:1,minHeight:0}}>
              {(()=>{
                const events = {
                  3:[{c:"#c2410c",t:"현대重 검수"}],
                  6:[{c:"#1e40af",t:"두산밥캣"},{c:"#c2410c",t:"포스코"}],
                  8:[{c:"#6d28d9",t:"한전 PCB"}],
                  10:[{c:"#c2410c",t:"기어박스"}],
                  13:[{c:"#047857",t:"LG화학"}],
                  14:[{c:"#c2410c",t:"포스코 납품",b:1},{c:"#1e40af",t:"두산밥캣 회의"}],
                  15:[{c:"#6d28d9",t:"한전 검수"}],
                  17:[{c:"#c2410c",t:"현대重 1차"}],
                  20:[{c:"#047857",t:"코팅 시작"}],
                  21:[{c:"#1e40af",t:"분기 정산"}],
                  23:[{c:"#c2410c",t:"베어링"},{c:"#6d28d9",t:"PCB"},{c:"#1e40af",t:"마운트"}],
                  27:[{c:"#047857",t:"LG화학"}],
                  29:[{c:"#c2410c",t:"포스코"}],
                };
                const cells=[];
                for(let i=0;i<35;i++){
                  const day = i - 2;
                  const inMonth = day >= 1 && day <= 31;
                  const isToday = day === 14;
                  const isWk = (i % 7) >= 5;
                  const evs = events[day] || [];
                  cells.push(
                    <div key={i} style={{borderRight:i%7!==6?"1px solid var(--line)":"none",borderBottom:i<28?"1px solid var(--line)":"none",padding:"6px 8px",minHeight:0,display:"flex",flexDirection:"column",gap:3,background:isToday?"var(--knk-red-soft)":"transparent",position:"relative",overflow:"hidden"}}>
                      <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                        <span style={{fontSize:11,fontFamily:"var(--font-mono)",fontWeight:isToday?700:500,color:!inMonth?"var(--ink-4)":isToday?"var(--knk-red)":isWk?"var(--ink-3)":"var(--ink-2)"}}>{inMonth?day:""}</span>
                        {evs.length>2 && <span style={{fontSize:9,color:"var(--ink-4)",fontFamily:"var(--font-mono)"}}>+{evs.length}</span>}
                      </div>
                      {evs.slice(0,2).map((e,j)=>(
                        <div key={j} style={{fontSize:10,padding:"2px 5px",borderRadius:3,background:e.b?e.c:e.c+"15",color:e.b?"#fff":e.c,fontWeight:e.b?600:500,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",borderLeft:e.b?"none":"2px solid "+e.c}}>{e.t}</div>
                      ))}
                    </div>
                  );
                }
                return cells;
              })()}
            </div>
          </div>

          {/* Right rail — selected day list */}
          <div className="card" style={{padding:0,overflow:"hidden"}}>
            <div style={{padding:"16px 20px",borderBottom:"1px solid var(--line)"}}>
              <div style={{fontSize:11,color:"var(--ink-3)",fontWeight:500,letterSpacing:"0.04em"}}>2025년 1월 14일 화요일 · 오늘</div>
              <h3 style={{fontSize:20,fontWeight:700,marginTop:4}}>일정 4건</h3>
            </div>
            <div style={{flex:1,overflow:"auto",padding:"12px 16px",display:"flex",flexDirection:"column",gap:10}}>
              {[
                {t:"포스코 — 베어링 하우징 납품",mn:"25-T-0156",b:"T",amt:"4.1억",time:"10:00",s:"shipped",urg:1},
                {t:"두산밥캣 회의 (3분기 협력안)",mn:"내부 회의",b:"M",time:"14:00",s:"draft"},
                {t:"한국전력 PCB 견적 회신",mn:"Q25-E-0089",b:"E",amt:"2.8억",time:"16:30",s:"draft"},
                {t:"현대중공업 1차 검수 준비",mn:"25-T-0142",b:"T",time:"종일",s:"in-production"},
              ].map((e,i)=>(
                <div key={i} style={{padding:14,borderRadius:10,background:e.urg?"var(--knk-red-soft)":"var(--surface-2)",border:e.urg?"1px solid var(--knk-red-line)":"1px solid var(--line)",display:"flex",flexDirection:"column",gap:8}}>
                  <div style={{display:"flex",alignItems:"center",gap:8}}>
                    <BizChip biz={e.b}/>
                    <span style={{fontFamily:"var(--font-mono)",fontSize:11,fontWeight:600,color:e.urg?"var(--knk-red)":"var(--ink-3)"}}>{e.time}</span>
                    {e.urg ? <span style={{marginLeft:"auto",fontSize:10,color:"var(--knk-red)",fontWeight:600}}>● 오늘 마감</span> : null}
                  </div>
                  <div style={{fontWeight:600,fontSize:14,letterSpacing:"-0.01em"}}>{e.t}</div>
                  <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
                    <Mgmt size="sm">{e.mn}</Mgmt>
                    <div style={{display:"flex",alignItems:"center",gap:8}}>
                      {e.amt && <span style={{fontFamily:"var(--font-mono)",fontSize:13,fontWeight:600}}>{e.amt}</span>}
                      <StatusChip status={e.s}/>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div style={{padding:"12px 16px",borderTop:"1px solid var(--line)"}}>
              <button className="btn btn-dark" style={{width:"100%"}}>＋ 일정 추가</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   3. PROJECT DETAIL (PARTS 28-col redesigned with column groups)
   ============================================================ */
const ProjectDetail = () => {
  const [activeGroup, setActiveGroup] = React.useState("기본");
  const groups = {
    "기본": ["품번","품명","규격","수량","단가","금액"],
    "재질": ["재질","열처리","경도","표면처리"],
    "공정": ["공정","공차","가공시간","담당자"],
    "납기": ["납기일","현재공정","진척률","상태"],
    "원가": ["재료비","가공비","외주비","마진"],
  };
  const cols = groups[activeGroup];
  const sample = [
    {pn:"P-001",nm:"기어 본체",sp:"⌀120×85",qty:2,pr:"1,250,000",am:"2,500,000",mat:"SCM440",ht:"침탄+ TF",hd:"HRC 58-62",sf:"흑색산화",pc:"선반→밀링→연삭",tol:"±0.005",tm:"4.5h",po:"이 기사",dl:"01/22",cp:"밀링중",pct:62,st:"in-production",mc:"180,000",pc2:"420,000",oc:"180,000",mg:"35%"},
    {pn:"P-002",nm:"입력축",sp:"⌀45×280",qty:2,pr:"680,000",am:"1,360,000",mat:"SCM435",ht:"고주파",hd:"HRC 50-55",sf:"-",pc:"선반→연삭",tol:"±0.003",tm:"2.0h",po:"박 차장",dl:"01/24",cp:"연삭중",pct:78,st:"in-production",mc:"82,000",pc2:"180,000",oc:"-",mg:"42%"},
    {pn:"P-003",nm:"출력축",sp:"⌀60×320",qty:2,pr:"890,000",am:"1,780,000",mat:"SCM435",ht:"고주파",hd:"HRC 50-55",sf:"-",pc:"선반→연삭",tol:"±0.003",tm:"2.4h",po:"박 차장",dl:"01/24",cp:"선반",pct:34,st:"in-production",mc:"108,000",pc2:"230,000",oc:"-",mg:"40%"},
    {pn:"P-004",nm:"베어링 캡 A",sp:"⌀160×40",qty:4,pr:"320,000",am:"1,280,000",mat:"S45C",ht:"-",hd:"-",sf:"흑색산화",pc:"선반→밀링",tol:"±0.02",tm:"1.5h",po:"최 대리",dl:"01/20",cp:"완료",pct:100,st:"shipped",mc:"42,000",pc2:"95,000",oc:"-",mg:"38%"},
    {pn:"P-005",nm:"베어링 캡 B",sp:"⌀160×40",qty:4,pr:"320,000",am:"1,280,000",mat:"S45C",ht:"-",hd:"-",sf:"흑색산화",pc:"선반→밀링",tol:"±0.02",tm:"1.5h",po:"최 대리",dl:"01/20",cp:"완료",pct:100,st:"shipped",mc:"42,000",pc2:"95,000",oc:"-",mg:"38%"},
    {pn:"P-006",nm:"커버 플레이트",sp:"320×280×12t",qty:1,pr:"180,000",am:"180,000",mat:"SS400",ht:"-",hd:"-",sf:"분체도장",pc:"레이저→밴딩",tol:"±0.1",tm:"0.8h",po:"최 대리",dl:"01/18",cp:"완료",pct:100,st:"shipped",mc:"24,000",pc2:"38,000",oc:"22,000",mg:"45%"},
    {pn:"P-007",nm:"하우징",sp:"500×420×280",qty:1,pr:"4,200,000",am:"4,200,000",mat:"GC250",ht:"-",hd:"-",sf:"흑색산화",pc:"주조→가공",tol:"±0.05",tm:"12h",po:"이 기사",dl:"01/26",cp:"주조중",pct:18,st:"in-production",mc:"680,000",pc2:"1,200,000",oc:"800,000",mg:"32%"},
  ];
  const colMap = {
    "품번":r=>(<Mgmt size="sm">{r.pn}</Mgmt>), "품명":r=>r.nm,"규격":r=>r.sp,
    "수량":r=>(<span className="num">{r.qty}</span>),"단가":r=>(<span className="num">{r.pr}</span>),"금액":r=>(<span className="num" style={{fontWeight:600}}>{r.am}</span>),
    "재질":r=>r.mat,"열처리":r=>r.ht,"경도":r=>r.hd,"표면처리":r=>r.sf,
    "공정":r=>(<span style={{fontSize:12,color:"var(--ink-3)"}}>{r.pc}</span>),"공차":r=>(<span className="num">{r.tol}</span>),"가공시간":r=>(<span className="num">{r.tm}</span>),"담당자":r=>r.po,
    "납기일":r=>(<span className="num">{r.dl}</span>),"현재공정":r=>(<span style={{fontSize:12}}>{r.cp}</span>),
    "진척률":r=>(<div style={{display:"flex",alignItems:"center",gap:8,minWidth:120}}><div style={{flex:1}}><Bar pct={r.pct} kind={r.pct===100?"ok":r.pct>=80?"info":""}/></div><span className="num" style={{fontSize:11,minWidth:30,textAlign:"right",color:"var(--ink-3)"}}>{r.pct}%</span></div>),
    "상태":r=>(<StatusChip status={r.st}/>),
    "재료비":r=>(<span className="num">{r.mc}</span>),"가공비":r=>(<span className="num">{r.pc2}</span>),"외주비":r=>(<span className="num">{r.oc}</span>),"마진":r=>(<span className="num" style={{fontWeight:600,color:"var(--ok)"}}>{r.mg}</span>),
  };
  const numCols = new Set(["수량","단가","금액","공차","가공시간","납기일","재료비","가공비","외주비","마진"]);

  return (
    <div className="chrome">
      <TopBar />
      <Sidebar active="projects" />
      <div className="main">
        <PageHead
          crumb="생산 / 프로젝트"
          title={<>정밀 기어박스 케이스</>}
          mgmt="25-T-0142"
          meta={<><BizChip biz="T"/> &nbsp;현대중공업 · 김 부장 · 납기 25/01/22</>}
          actions={<>
            <button className="btn btn-sm">⤓ Excel</button>
            <button className="btn btn-sm">📋 복사</button>
            <button className="btn btn-dark btn-sm">＋ PARTS 추가</button>
          </>}
        />
        <div className="main-body" style={{padding:0,display:"flex",flexDirection:"column",overflow:"hidden"}}>
          {/* Sub-summary strip */}
          <div style={{padding:"16px 24px",background:"var(--surface)",borderBottom:"1px solid var(--line)",display:"grid",gridTemplateColumns:"repeat(6, 1fr)",gap:24}}>
            {[
              {l:"전체 PARTS",v:"7",u:"종"},
              {l:"총 수량",v:"16",u:"EA"},
              {l:"수주금액",v:"12,580,000",u:"₩",hi:1},
              {l:"평균 마진",v:"38",u:"%",ok:1},
              {l:"진척률",v:"62",u:"%",bar:62},
              {l:"잔여 일수",v:"D-8",u:"",warn:1},
            ].map((s,i)=>(
              <div key={i}>
                <div style={{fontSize:11,color:"var(--ink-3)",fontWeight:500,marginBottom:4}}>{s.l}</div>
                <div style={{display:"flex",alignItems:"baseline",gap:4}}>
                  <span className="num" style={{fontSize:24,fontWeight:700,letterSpacing:"-0.02em",color:s.warn?"var(--warn)":s.ok?"var(--ok)":s.hi?"var(--ink)":"var(--ink)"}}>{s.v}</span>
                  <span style={{fontSize:12,color:"var(--ink-4)"}}>{s.u}</span>
                </div>
                {s.bar && <div style={{marginTop:6}}><Bar pct={s.bar} kind="info"/></div>}
              </div>
            ))}
          </div>

          {/* Section tabs (segmented) */}
          <div style={{padding:"12px 24px",background:"var(--surface)",borderBottom:"1px solid var(--line)",display:"flex",alignItems:"center",gap:12}}>
            <div className="seg">
              <button className="is-active">PARTS (28)</button>
              <button>일정</button>
              <button>견적</button>
              <button>도면</button>
              <button>수금</button>
              <button>이력</button>
            </div>
            <div style={{marginLeft:"auto",display:"flex",alignItems:"center",gap:8}}>
              <span style={{fontSize:11,color:"var(--ink-3)"}}>컬럼 그룹:</span>
              <div className="seg">
                {Object.keys(groups).map(g=>(
                  <button key={g} className={activeGroup===g?"is-active":""} onClick={()=>setActiveGroup(g)}>{g} <span style={{fontFamily:"var(--font-mono)",fontSize:10,opacity:0.6,marginLeft:4}}>{groups[g].length}</span></button>
                ))}
              </div>
              <button className="btn btn-sm" style={{marginLeft:8}}>⊞ 전체 28개</button>
            </div>
          </div>

          {/* Table */}
          <div style={{flex:1,overflow:"auto",background:"var(--surface)"}}>
            <table className="tbl tbl-zebra" style={{minWidth:"100%"}}>
              <thead>
                <tr>
                  <th style={{width:32,position:"sticky",left:0,background:"var(--surface)",zIndex:4}}><input type="checkbox"/></th>
                  <th style={{width:90,position:"sticky",left:32,background:"var(--surface)",zIndex:4,boxShadow:"1px 0 0 var(--line)"}}>품번</th>
                  <th style={{width:160,position:"sticky",left:122,background:"var(--surface)",zIndex:4,boxShadow:"1px 0 0 var(--line-2)"}}>품명</th>
                  {cols.filter(c=>c!=="품번"&&c!=="품명").map(c=>(
                    <th key={c} className={numCols.has(c)?"num":""}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sample.map((r,i)=>(
                  <tr key={i}>
                    <td style={{position:"sticky",left:0,background:i%2?"var(--surface-inset)":"var(--surface)",zIndex:1}}><input type="checkbox"/></td>
                    <td style={{position:"sticky",left:32,background:i%2?"var(--surface-inset)":"var(--surface)",zIndex:1,boxShadow:"1px 0 0 var(--line)"}}>{colMap["품번"](r)}</td>
                    <td style={{position:"sticky",left:122,background:i%2?"var(--surface-inset)":"var(--surface)",zIndex:1,boxShadow:"1px 0 0 var(--line-2)",fontWeight:500}}>{colMap["품명"](r)}</td>
                    {cols.filter(c=>c!=="품번"&&c!=="품명").map(c=>(
                      <td key={c} className={numCols.has(c)?"num":""}>{colMap[c](r)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Bottom bar */}
          <div style={{padding:"10px 24px",background:"var(--surface)",borderTop:"1px solid var(--line)",display:"flex",alignItems:"center",justifyContent:"space-between",fontSize:12}}>
            <div style={{color:"var(--ink-3)"}}>전체 7건 · 선택 0건 · <span style={{color:"var(--ink)"}}>{activeGroup}</span> 그룹 ({cols.length} 컬럼)</div>
            <div style={{display:"flex",gap:8}}>
              <button className="btn btn-sm">← 이전</button>
              <span style={{padding:"6px 12px",background:"var(--ink)",color:"#fff",borderRadius:6,fontSize:12,fontWeight:600}}>1</span>
              <span style={{padding:"6px 12px",fontSize:12,color:"var(--ink-3)"}}>2</span>
              <span style={{padding:"6px 12px",fontSize:12,color:"var(--ink-3)"}}>3</span>
              <span style={{padding:"6px 12px",fontSize:12,color:"var(--ink-3)"}}>4</span>
              <button className="btn btn-sm">다음 →</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

/* ============================================================
   4. CALENDAR (full-month with sidebar)
   ============================================================ */
const CalendarPage = () => (
  <div className="chrome">
    <TopBar />
    <Sidebar active="calendar" />
    <div className="main">
      <PageHead
        crumb="공통"
        title="캘린더"
        meta="개인 일정 + 프로젝트 마일스톤 + 결재 마감"
        actions={<>
          <div className="seg">
            <button>일</button>
            <button>주</button>
            <button className="is-active">월</button>
            <button>연</button>
          </div>
          <button className="btn btn-sm">필터</button>
          <button className="btn btn-primary btn-sm">＋ 일정</button>
        </>}
      />
      <div className="main-bento" style={{gridTemplateColumns:"260px 1fr",gridTemplateRows:"1fr",gap:16,overflow:"hidden"}}>
        {/* Left rail — categories + mini cal */}
        <div style={{display:"flex",flexDirection:"column",gap:12,overflow:"auto"}}>
          <div className="card-flat" style={{padding:14}}>
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:8}}>
              <span style={{fontSize:13,fontWeight:600}}>2025년 1월</span>
              <div style={{display:"flex",gap:4}}>
                <button className="btn btn-icon btn-sm" style={{height:24,width:24,fontSize:11}}>‹</button>
                <button className="btn btn-icon btn-sm" style={{height:24,width:24,fontSize:11}}>›</button>
              </div>
            </div>
            <div style={{display:"grid",gridTemplateColumns:"repeat(7,1fr)",gap:1,fontSize:10,fontFamily:"var(--font-mono)"}}>
              {["월","화","수","목","금","토","일"].map(d=>(<div key={d} style={{textAlign:"center",color:"var(--ink-4)",fontWeight:500,padding:"4px 0"}}>{d}</div>))}
              {Array.from({length:35}).map((_,i)=>{
                const d=i-2; const inM=d>=1&&d<=31; const today=d===14;
                return <div key={i} style={{textAlign:"center",padding:"4px 0",borderRadius:4,color:!inM?"var(--ink-4)":today?"#fff":"var(--ink-2)",background:today?"var(--knk-red)":"transparent",fontWeight:today?700:400,cursor:"pointer"}}>{inM?d:""}</div>;
              })}
            </div>
          </div>
          <div className="card-flat" style={{padding:14}}>
            <div style={{fontSize:12,fontWeight:600,marginBottom:10,color:"var(--ink-3)",letterSpacing:"0.04em"}}>일정 분류</div>
            {[
              {c:"#0f172a",t:"개인 일정",n:4,on:1},
              {c:"#c2410c",t:"정밀 (T)",n:8,on:1},
              {c:"#1e40af",t:"가공 (M)",n:5,on:1},
              {c:"#6d28d9",t:"전기 (E)",n:3,on:1},
              {c:"#047857",t:"화학 (C)",n:2,on:1},
              {c:"#b45309",t:"결재 마감",n:3,on:1},
              {c:"#94a3b8",t:"휴일·공식",n:2,on:0},
            ].map((it,i)=>(
              <label key={i} style={{display:"flex",alignItems:"center",gap:8,padding:"6px 0",fontSize:13,cursor:"pointer"}}>
                <input type="checkbox" defaultChecked={it.on}/>
                <div style={{width:8,height:8,borderRadius:2,background:it.c}}/>
                <span style={{flex:1}}>{it.t}</span>
                <span style={{fontSize:11,color:"var(--ink-4)",fontFamily:"var(--font-mono)"}}>{it.n}</span>
              </label>
            ))}
          </div>
          <div className="card-flat" style={{padding:14}}>
            <div style={{fontSize:12,fontWeight:600,marginBottom:10,color:"var(--ink-3)",letterSpacing:"0.04em"}}>이번 달 요약</div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:6}}><span>전체 일정</span><span className="num" style={{fontWeight:600}}>27</span></div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:6}}><span>완료</span><span className="num" style={{fontWeight:600,color:"var(--ok)"}}>14</span></div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:12,marginBottom:6}}><span>진행</span><span className="num" style={{fontWeight:600,color:"var(--info)"}}>9</span></div>
            <div style={{display:"flex",justifyContent:"space-between",fontSize:12}}><span>지연 위험</span><span className="num" style={{fontWeight:600,color:"var(--danger)"}}>2</span></div>
          </div>
        </div>

        {/* Big calendar */}
        <div className="card" style={{padding:0,overflow:"hidden"}}>
          <div style={{display:"grid",gridTemplateColumns:"repeat(7, 1fr)",borderBottom:"1px solid var(--line)"}}>
            {["월","화","수","목","금","토","일"].map((d,i)=>(<div key={d} style={{padding:"12px 16px",fontSize:12,fontWeight:600,color:i>=5?"var(--ink-4)":"var(--ink-2)",letterSpacing:"0.04em",borderRight:i<6?"1px solid var(--line)":"none"}}>{d}요일</div>))}
          </div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(7,1fr)",gridTemplateRows:"repeat(5,1fr)",flex:1,minHeight:0}}>
            {(()=>{
              const events={
                3:[{c:"#c2410c",t:"현대중공업 검수",mn:"25-T-0142"}],
                6:[{c:"#1e40af",t:"두산밥캣 견적",mn:"Q25-M-0034"},{c:"#c2410c",t:"포스코 회의"}],
                8:[{c:"#6d28d9",t:"한전 PCB 발주",mn:"25-E-0034"}],
                10:[{c:"#0f172a",t:"전사 월례 회의"}],
                13:[{c:"#047857",t:"LG화학 코팅 시작"}],
                14:[{c:"#c2410c",t:"포스코 베어링 납품",b:1,mn:"25-T-0156"},{c:"#1e40af",t:"두산밥캣 회의"},{c:"#6d28d9",t:"한전 견적 회신",mn:"Q25-E-0089"}],
                15:[{c:"#6d28d9",t:"한전 검수 일정"}],
                17:[{c:"#c2410c",t:"현대重 1차 검수"}],
                20:[{c:"#047857",t:"코팅 라인 가동"},{c:"#b45309",t:"결재 마감",b:1}],
                22:[{c:"#c2410c",t:"기어박스 납기",b:1}],
                23:[{c:"#c2410c",t:"베어링 출하"},{c:"#6d28d9",t:"PCB 검수"},{c:"#1e40af",t:"마운트 가공"}],
                27:[{c:"#047857",t:"LG화학 중간보고"}],
                29:[{c:"#c2410c",t:"포스코 추가발주"}],
                31:[{c:"#0f172a",t:"분기 마감",b:1}],
              };
              const cells=[];
              for(let i=0;i<35;i++){
                const day=i-2; const inM=day>=1&&day<=31; const today=day===14; const wk=(i%7)>=5;
                const evs=events[day]||[];
                cells.push(
                  <div key={i} style={{borderRight:i%7!==6?"1px solid var(--line)":"none",borderBottom:i<28?"1px solid var(--line)":"none",padding:"8px 10px",minHeight:0,display:"flex",flexDirection:"column",gap:3,background:today?"var(--knk-red-soft)":"transparent",overflow:"hidden",cursor:"pointer"}}>
                    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:2}}>
                      <span style={{fontSize:13,fontFamily:"var(--font-mono)",fontWeight:today?700:500,color:!inM?"var(--ink-4)":today?"var(--knk-red)":wk?"var(--ink-3)":"var(--ink-2)"}}>{inM?day:""}</span>
                      {evs.length>3 && <span style={{fontSize:10,color:"var(--ink-4)",fontFamily:"var(--font-mono)",fontWeight:500}}>+{evs.length-3}</span>}
                    </div>
                    {evs.slice(0,3).map((e,j)=>(
                      <div key={j} style={{fontSize:11,padding:"3px 6px",borderRadius:4,background:e.b?e.c:e.c+"15",color:e.b?"#fff":e.c,fontWeight:e.b?600:500,whiteSpace:"nowrap",overflow:"hidden",textOverflow:"ellipsis",borderLeft:e.b?"none":"2px solid "+e.c,lineHeight:1.4}}>{e.t}</div>
                    ))}
                  </div>
                );
              }
              return cells;
            })()}
          </div>
        </div>
      </div>
    </div>
  </div>
);

/* ============================================================
   5. DAILY WORK (일일 업무)
   ============================================================ */
const DailyWork = () => (
  <div className="chrome">
    <TopBar />
    <Sidebar active="daily" />
    <div className="main">
      <PageHead
        crumb="공통"
        title="일일 업무"
        meta={<>2025년 1월 14일 화요일 · 김 부장</>}
        actions={<>
          <button className="btn btn-sm">📅 어제</button>
          <button className="btn btn-sm">📅 내일</button>
          <button className="btn btn-primary btn-sm">＋ 업무 추가</button>
        </>}
      />
      <div className="main-bento" style={{gridTemplateColumns:"1fr 1fr 320px",gridTemplateRows:"auto 1fr",gap:16,overflow:"hidden"}}>
        {/* Top KPI strip */}
        <div className="card" style={{gridColumn:"1 / 4",padding:0,display:"grid",gridTemplateColumns:"repeat(5, 1fr)"}}>
          {[
            {l:"오늘 할 일",v:"8",u:"건",sub:"4 진행 · 4 대기"},
            {l:"완료",v:"3",u:"건",sub:"진척 37%",ok:1},
            {l:"지연",v:"1",u:"건",sub:"포스코 납품",warn:1},
            {l:"회의",v:"2",u:"건",sub:"오전 1 · 오후 1"},
            {l:"결재 대기",v:"3",u:"건",sub:"승인 2 · 반려 1"},
          ].map((k,i)=>(
            <div key={i} style={{padding:"18px 20px",borderRight:i<4?"1px solid var(--line)":"none"}}>
              <div style={{fontSize:11,color:"var(--ink-3)",fontWeight:500,marginBottom:6}}>{k.l}</div>
              <div style={{display:"flex",alignItems:"baseline",gap:4,marginBottom:4}}>
                <span className="num" style={{fontSize:32,fontWeight:700,letterSpacing:"-0.02em",color:k.warn?"var(--warn)":k.ok?"var(--ok)":"var(--ink)"}}>{k.v}</span>
                <span style={{fontSize:13,color:"var(--ink-4)"}}>{k.u}</span>
              </div>
              <div style={{fontSize:11,color:"var(--ink-3)"}}>{k.sub}</div>
            </div>
          ))}
        </div>

        {/* Tasks list */}
        <div className="card" style={{gridColumn:"1 / 3",overflow:"hidden",padding:0}}>
          <div style={{padding:"16px 20px",borderBottom:"1px solid var(--line)",display:"flex",alignItems:"center"}}>
            <div className="card-title">업무 리스트</div>
            <div style={{marginLeft:"auto"}}>
              <div className="seg">
                <button className="is-active">전체 (8)</button>
                <button>진행 (4)</button>
                <button>완료 (3)</button>
                <button>지연 (1)</button>
              </div>
            </div>
          </div>
          <div style={{flex:1,overflow:"auto"}}>
            {[
              {t:"포스코 — 베어링 하우징 납품 확인",mn:"25-T-0156",b:"T",p:"high",time:"10:00",done:0,delay:1,sub:"창고 출고 확인 + 송장 발행 + 거래처 확인 전화"},
              {t:"한국전력 PCB 견적 회신",mn:"Q25-E-0089",b:"E",p:"high",time:"16:30",done:0,sub:"단가 검토 후 견적서 송부 (마감 D-Day)"},
              {t:"두산밥캣 3분기 협력안 회의",mn:"내부 회의",b:"M",p:"med",time:"14:00",done:0,sub:"본사 3층 회의실 — 박 차장 동석"},
              {t:"현대중공업 1차 검수 자료 정리",mn:"25-T-0142",b:"T",p:"med",time:"종일",done:0,sub:"검수 체크리스트 작성 및 도면 출력"},
              {t:"지난 주 매출 보고서 작성",mn:"내부",b:null,p:"low",time:"완료",done:1},
              {t:"신규 고객사 등록 — (주)대성테크",mn:"신규",b:null,p:"low",time:"완료",done:1},
              {t:"이메일 회신 (15건)",mn:"-",b:null,p:"low",time:"완료",done:1},
              {t:"LG화학 코팅 라인 일정 조율",mn:"25-C-0021",b:"C",p:"med",time:"미정",done:0,sub:"공정팀과 시작일 협의"},
            ].map((t,i)=>(
              <div key={i} style={{display:"flex",gap:12,padding:"12px 20px",borderBottom:"1px solid var(--line)",alignItems:"flex-start",opacity:t.done?0.55:1,background:t.delay?"var(--knk-red-soft)":t.done?"var(--surface-2)":"transparent"}}>
                <input type="checkbox" defaultChecked={t.done} style={{marginTop:4,width:16,height:16}}/>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:4,flexWrap:"wrap"}}>
                    {t.b && <BizChip biz={t.b}/>}
                    {t.p==="high" && <span className="chip" style={{background:"var(--danger-soft)",color:"var(--danger)"}}>● 긴급</span>}
                    <Mgmt size="sm">{t.mn}</Mgmt>
                    <span style={{fontFamily:"var(--font-mono)",fontSize:11,color:t.delay?"var(--knk-red)":"var(--ink-3)",fontWeight:t.delay?700:500,marginLeft:"auto"}}>{t.delay?"⚠ 지연":t.time}</span>
                  </div>
                  <div style={{fontSize:14,fontWeight:t.done?400:500,textDecoration:t.done?"line-through":"none",color:t.done?"var(--ink-3)":"var(--ink)"}}>{t.t}</div>
                  {t.sub && !t.done && <div style={{fontSize:12,color:"var(--ink-3)",marginTop:2}}>{t.sub}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right column — schedule + quick stats */}
        <div className="card" style={{gridColumn:"3",overflow:"hidden",padding:0,display:"flex",flexDirection:"column"}}>
          <div style={{padding:"16px 20px",borderBottom:"1px solid var(--line)"}}>
            <div className="card-title">오늘의 시간표</div>
          </div>
          <div style={{flex:1,overflow:"auto",padding:"12px 16px"}}>
            {[
              {time:"09:00",t:"이메일 정리",d:"30분",done:1},
              {time:"10:00",t:"포스코 납품 확인",d:"1시간",urg:1},
              {time:"11:00",t:"PARTS 검토",d:"1시간"},
              {time:"12:00",t:"점심",d:"1시간",rest:1},
              {time:"14:00",t:"두산밥캣 회의",d:"1시간 30분"},
              {time:"16:00",t:"검수 자료 작성",d:"30분"},
              {time:"16:30",t:"한전 견적 회신",d:"1시간",urg:1},
              {time:"17:30",t:"일일 마감 보고",d:"30분"},
            ].map((s,i)=>(
              <div key={i} style={{display:"flex",gap:10,padding:"6px 0",alignItems:"flex-start"}}>
                <div className="num" style={{fontSize:11,fontWeight:600,color:s.urg?"var(--knk-red)":s.done?"var(--ok)":"var(--ink-3)",minWidth:38,paddingTop:2}}>{s.time}</div>
                <div style={{flex:1,padding:"6px 10px",borderRadius:6,background:s.urg?"var(--knk-red-soft)":s.rest?"var(--surface-3)":s.done?"var(--ok-soft)":"var(--surface-2)",borderLeft:`3px solid ${s.urg?"var(--knk-red)":s.rest?"var(--ink-4)":s.done?"var(--ok)":"var(--line-3)"}`}}>
                  <div style={{fontSize:12,fontWeight:500,color:s.done?"var(--ink-3)":"var(--ink)",textDecoration:s.done?"line-through":"none"}}>{s.t}</div>
                  <div style={{fontSize:10,color:"var(--ink-4)",marginTop:1}}>{s.d}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
);

/* ============================================================
   Tokens & Components reference artboards (compact, modern)
   ============================================================ */
const TokensV2 = () => (
  <div style={{padding:32,background:"var(--surface-2)",height:"100%",overflow:"auto"}}>
    <div style={{maxWidth:1200,margin:"0 auto"}}>
      <div style={{marginBottom:32}}>
        <div style={{fontSize:11,letterSpacing:"0.06em",color:"var(--ink-3)",fontWeight:600,marginBottom:6}}>HAIST WORKS · v2 TOKENS</div>
        <h1 style={{fontSize:36,letterSpacing:"-0.02em"}}>고요한 운영실 (Quiet Ops)</h1>
        <p style={{fontSize:15,color:"var(--ink-3)",maxWidth:680,marginTop:8}}>차가운 흰색 표면 · 진한 잉크 텍스트 · 단일 KNK 빨강 액센트 (≤5%) · 큰 type scale로 한눈에 데이터가 들어오게.</p>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:24}}>
        {/* Surfaces & ink */}
        <div className="card">
          <div className="card-head"><div className="card-title">표면 (Surfaces)</div></div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(2, 1fr)",gap:8}}>
            {[
              ["#ffffff","surface","기본 카드"],
              ["#f7f8fa","surface-2","앱 배경"],
              ["#eef0f4","surface-3","구분선/탭"],
              ["#fafbfc","surface-inset","조용한 강조"],
            ].map(([c,n,d])=>(
              <div key={n} style={{padding:14,background:c,borderRadius:10,border:"1px solid var(--line)"}}>
                <div className="num" style={{fontSize:12,fontWeight:600}}>{c}</div>
                <div style={{fontSize:11,color:"var(--ink-3)"}}>{n}</div>
                <div style={{fontSize:10,color:"var(--ink-4)",marginTop:2}}>{d}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head"><div className="card-title">잉크 (Ink) — 콘트라스트 ≥7:1</div></div>
          <div style={{display:"flex",flexDirection:"column",gap:8}}>
            {[
              ["#0f172a","ink","본문 — 16.7:1 (AAA)"],
              ["#334155","ink-2","보조 — 9.6:1 (AAA)"],
              ["#64748b","ink-3","메타 — 5.7:1 (AA)"],
              ["#94a3b8","ink-4","비활성 — 3.2:1"],
            ].map(([c,n,d])=>(
              <div key={n} style={{display:"flex",alignItems:"center",gap:12,padding:"10px 12px",background:"var(--surface-2)",borderRadius:8}}>
                <div style={{width:32,height:32,borderRadius:8,background:c}}/>
                <div style={{flex:1}}>
                  <div style={{color:c,fontSize:14,fontWeight:600}}>한글 가독성 — Quiet Ops</div>
                  <div style={{fontSize:10,color:"var(--ink-4)"}}>{n} · {c}</div>
                </div>
                <div style={{fontSize:11,color:"var(--ink-3)"}}>{d}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head"><div className="card-title">단일 액센트 (Accent) — KNK 빨강</div></div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8,marginBottom:12}}>
            {[
              ["#a5282c","knk-red","주 액센트 — CTA, 알림"],
              ["#fef2f2","knk-red-soft","배경 강조"],
              ["#fecaca","knk-red-line","경계선"],
              ["#0f172a","ink","대비 — 본문/대시보드"],
            ].map(([c,n,d])=>(
              <div key={n} style={{padding:12,background:"var(--surface-2)",borderRadius:8}}>
                <div style={{height:36,background:c,borderRadius:6,marginBottom:6}}/>
                <div className="num" style={{fontSize:11,fontWeight:600}}>{c}</div>
                <div style={{fontSize:10,color:"var(--ink-3)"}}>{d}</div>
              </div>
            ))}
          </div>
          <div style={{padding:12,background:"var(--surface-inset)",borderRadius:8,fontSize:12,color:"var(--ink-3)",lineHeight:1.6}}>
            <strong style={{color:"var(--ink)"}}>규칙</strong> — 빨강은 <strong>≤5% 픽셀</strong>만 차지. 주 CTA 1개 / 마감 임박 알림 / 오늘 표시. 그 외엔 진한 잉크 + 회색 단계로.
          </div>
        </div>

        <div className="card">
          <div className="card-head"><div className="card-title">사업부 (Business)</div></div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
            {[
              ["T","정밀","#c2410c"],
              ["M","가공","#1e40af"],
              ["E","전기","#6d28d9"],
              ["C","화학","#047857"],
            ].map(([k,n,c])=>(
              <div key={k} style={{padding:14,background:"var(--surface-2)",borderRadius:10,display:"flex",alignItems:"center",gap:10}}>
                <div style={{width:36,height:36,borderRadius:8,background:c,color:"#fff",display:"flex",alignItems:"center",justifyContent:"center",fontSize:16,fontWeight:700,fontFamily:"var(--font-mono)"}}>{k}</div>
                <div>
                  <div style={{fontSize:13,fontWeight:600}}>{n} {k}</div>
                  <div className="num" style={{fontSize:10,color:"var(--ink-3)"}}>{c}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{marginTop:12,fontSize:11,color:"var(--ink-3)",lineHeight:1.6,padding:"8px 12px",background:"var(--surface-inset)",borderRadius:6}}>
            v1과 동일한 hue를 유지하되 더 진한 톤으로 → 회색 위에서 dot 한 개로 식별 가능 (배경 채움 X).
          </div>
        </div>

        {/* Type scale */}
        <div className="card" style={{gridColumn:"1 / 3"}}>
          <div className="card-head">
            <div>
              <div className="card-title">Type scale — 큰 단계</div>
              <div className="card-sub">v1 13px 본문 → v2 14px 본문 / KPI 24px → 40px</div>
            </div>
          </div>
          <div style={{display:"grid",gridTemplateColumns:"100px 100px 1fr 80px",gap:24,fontSize:13,padding:"8px 0",alignItems:"baseline",borderBottom:"1px solid var(--line)",fontWeight:600,fontSize:11,color:"var(--ink-3)",letterSpacing:"0.04em",paddingBottom:10}}>
            <div>토큰</div><div>크기</div><div>예시</div><div>용도</div>
          </div>
          {[
            ["display","40px","62.4 억","KPI 메인 숫자",36],
            ["3xl","30px","매출 홈","페이지 제목",26],
            ["2xl","24px","사업부별 매출","섹션 제목",22],
            ["xl","20px","2025년 1월 14일","카드 제목",18],
            ["lg","17px","현대중공업 — 베어링 하우징","리스트 강조",16],
            ["md","15px","오늘의 시간표 / 14:00 회의 시작","카드 본문",14],
            ["base","14px","본문 — 한글 가독성을 위한 기본 사이즈","바디 텍스트",13],
            ["sm","13px","09:00 이메일 정리 — 30분",  "캡션",12],
            ["xs","12px","D-3 · 25-T-0142 · 4.1억",  "메타",11],
          ].map(([n,s,ex,p,sz])=>(
            <div key={n} style={{display:"grid",gridTemplateColumns:"100px 100px 1fr 80px",gap:24,alignItems:"baseline",padding:"12px 0",borderBottom:"1px solid var(--line)"}}>
              <div className="num" style={{fontSize:11,color:"var(--ink-3)",fontWeight:600}}>--text-{n}</div>
              <div className="num" style={{fontSize:11,color:"var(--ink-4)"}}>{s}</div>
              <div style={{fontSize:sz,fontWeight:n==="display"||n==="3xl"?700:n==="2xl"||n==="xl"?600:500,letterSpacing:n==="display"?"-0.03em":n==="3xl"?"-0.02em":"-0.01em",fontFamily:n==="display"?"var(--font-mono)":"inherit",color:"var(--ink)"}}>{ex}</div>
              <div style={{fontSize:11,color:"var(--ink-3)"}}>{p}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const ComponentsV2 = () => (
  <div style={{padding:32,background:"var(--surface-2)",height:"100%",overflow:"auto"}}>
    <div style={{maxWidth:1200,margin:"0 auto"}}>
      <div style={{marginBottom:32}}>
        <div style={{fontSize:11,letterSpacing:"0.06em",color:"var(--ink-3)",fontWeight:600,marginBottom:6}}>HAIST WORKS · v2 COMPONENTS</div>
        <h1 style={{fontSize:36,letterSpacing:"-0.02em"}}>공통 컴포넌트</h1>
      </div>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:24}}>
        {/* Buttons */}
        <div className="card">
          <div className="card-head"><div className="card-title">버튼</div></div>
          <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:12}}>
            <button className="btn btn-primary">＋ 견적 등록</button>
            <button className="btn btn-dark">저장</button>
            <button className="btn">취소</button>
            <button className="btn btn-ghost">처음부터 →</button>
          </div>
          <div style={{display:"flex",gap:8,flexWrap:"wrap",marginBottom:12}}>
            <button className="btn btn-primary btn-sm">＋ 신규</button>
            <button className="btn btn-sm">필터 ⌄</button>
            <button className="btn btn-icon btn-sm">⚙</button>
          </div>
          <div style={{display:"flex",gap:8,flexWrap:"wrap"}}>
            <button className="btn btn-primary btn-lg">결재 상신</button>
            <button className="btn btn-lg">반려</button>
          </div>
        </div>

        {/* Mgmt-no */}
        <div className="card">
          <div className="card-head"><div className="card-title">관리번호 (Mgmt-no)</div></div>
          <p style={{fontSize:12,color:"var(--ink-3)",marginBottom:12}}>호박 → 진한 잉크 알약 (눈 피로 경감, AAA 콘트라스트)</p>
          <div style={{display:"flex",gap:10,flexWrap:"wrap",alignItems:"center"}}>
            <Mgmt size="lg">25-T-0142</Mgmt>
            <Mgmt>25-M-0089</Mgmt>
            <Mgmt size="sm">Q25-E-0089</Mgmt>
          </div>
          <div style={{marginTop:16,padding:"10px 12px",background:"var(--surface-inset)",borderRadius:6,fontSize:11,color:"var(--ink-3)",lineHeight:1.6}}>
            형식: <span className="num" style={{color:"var(--ink)",fontWeight:600}}>YY-{`{T|M|E|C}`}-####</span>. 견적은 Q 접두어.
          </div>
        </div>

        {/* Status chips */}
        <div className="card" style={{gridColumn:"1 / 3"}}>
          <div className="card-head"><div className="card-title">상태 chip — 회색 기본 / 임팩트 시에만 채색</div></div>
          <div style={{display:"flex",gap:10,flexWrap:"wrap",alignItems:"center"}}>
            {["draft","confirmed","in-production","shipped","invoiced","paid","cancelled"].map(s=><StatusChip key={s} status={s}/>)}
          </div>
          <div style={{marginTop:16,display:"flex",gap:10,flexWrap:"wrap"}}>
            <BizChip biz="T"/><BizChip biz="M"/><BizChip biz="E"/><BizChip biz="C"/>
          </div>
        </div>

        {/* KPIs */}
        <div className="card" style={{gridColumn:"1 / 3"}}>
          <div className="card-head"><div className="card-title">KPI 카드 — 큰 숫자 + 인라인 스파크라인</div></div>
          <div style={{display:"grid",gridTemplateColumns:"repeat(4, 1fr)",gap:12}}>
            <div className="kpi">
              <div className="kpi-label">이번 달 매출 <span style={{color:"var(--ink-4)"}}>억</span></div>
              <div><span className="kpi-value">62.4</span></div>
              <Trend dir="up" value="+12.4%"/>
              <div className="kpi-spark"><Sparkline data={[20,30,28,35,42,38,46,52,50,58,62]} color="#0f172a"/></div>
            </div>
            <div className="kpi">
              <div className="kpi-label">신규 수주</div>
              <div><span className="kpi-value">35</span><span className="kpi-unit">건</span></div>
              <Trend dir="up" value="+9건"/>
              <div className="kpi-spark"><Sparkline data={[12,15,11,18,22,28,32,35]} color="#1e5fbf"/></div>
            </div>
            <div className="kpi">
              <div className="kpi-label">미수금</div>
              <div><span className="kpi-value">6.9</span><span className="kpi-unit">/ 84.2</span></div>
              <Trend dir="down" value="-3.4%"/>
              <div className="kpi-spark"><Sparkline data={[82,84,80,78,76,74,71,69]} color="#0d7c4f"/></div>
            </div>
            <div className="kpi" style={{background:"var(--ink)",color:"#fff"}}>
              <div className="kpi-label" style={{color:"rgba(255,255,255,0.6)"}}>달성률</div>
              <div><span className="kpi-value" style={{color:"#fff"}}>78</span><span className="kpi-unit" style={{color:"rgba(255,255,255,0.6)"}}>%</span></div>
              <div style={{marginTop:8}}>
                <div className="bar" style={{background:"rgba(255,255,255,0.15)"}}><i style={{width:"78%",background:"#fff"}}/></div>
              </div>
            </div>
          </div>
        </div>

        {/* Table sample */}
        <div className="card" style={{gridColumn:"1 / 3",padding:0,overflow:"hidden"}}>
          <div style={{padding:"16px 20px",borderBottom:"1px solid var(--line)"}}>
            <div className="card-title">표 — 행 48px / 메타 회색 / 진척바 인라인</div>
          </div>
          <div style={{overflow:"auto",maxHeight:280}}>
            <table className="tbl">
              <thead><tr>
                <th style={{width:30}}><input type="checkbox"/></th>
                <th style={{width:90}}>관리번호</th>
                <th style={{width:60}}>사업부</th>
                <th>프로젝트</th>
                <th style={{width:100}}>거래처</th>
                <th style={{width:100}}>상태</th>
                <th style={{width:160}}>진척률</th>
                <th style={{width:80}} className="num">금액</th>
              </tr></thead>
              <tbody>
                {[
                  {n:"25-T-0142",b:"T",p:"정밀 기어박스 케이스",c:"현대중공업",s:"in-production",pct:62,amt:"3.2"},
                  {n:"25-M-0089",b:"M",p:"엔진 마운트 브라켓",c:"두산밥캣",s:"confirmed",pct:18,amt:"1.8"},
                  {n:"25-E-0034",b:"E",p:"제어반 PCB 어셈블리",c:"한국전력",s:"in-production",pct:84,amt:"2.4"},
                  {n:"25-T-0156",b:"T",p:"베어링 하우징 (3종)",c:"포스코",s:"shipped",pct:100,amt:"4.1"},
                ].map(r=>(
                  <tr key={r.n}>
                    <td><input type="checkbox"/></td>
                    <td><Mgmt size="sm">{r.n}</Mgmt></td>
                    <td><BizChip biz={r.b}/></td>
                    <td style={{fontWeight:500}}>{r.p}</td>
                    <td style={{color:"var(--ink-3)"}}>{r.c}</td>
                    <td><StatusChip status={r.s}/></td>
                    <td>
                      <div style={{display:"flex",alignItems:"center",gap:8}}>
                        <div style={{flex:1}}><Bar pct={r.pct} kind={r.pct===100?"ok":""}/></div>
                        <span className="num" style={{fontSize:11,color:"var(--ink-3)",minWidth:30,textAlign:"right"}}>{r.pct}%</span>
                      </div>
                    </td>
                    <td className="num" style={{fontWeight:600}}>{r.amt} <span style={{color:"var(--ink-4)",fontSize:10}}>억</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
);

/* ============================================================
   Closing — comparison & integration
   ============================================================ */
const Closing = () => (
  <div style={{padding:48,background:"var(--surface)",height:"100%",overflow:"auto"}}>
    <div style={{maxWidth:1100,margin:"0 auto"}}>
      <div style={{fontSize:11,letterSpacing:"0.06em",color:"var(--ink-3)",fontWeight:600,marginBottom:6}}>CLOSING</div>
      <h1 style={{fontSize:40,letterSpacing:"-0.02em",marginBottom:16}}>v1 → v2, 무엇이 달라졌나</h1>
      <p style={{fontSize:16,color:"var(--ink-3)",maxWidth:760,marginBottom:32}}>피드백: 기존과 비슷 / 눈 피로 / 한눈에 안 들어옴 / 스크롤 과대. 이를 4가지 축으로 해소합니다.</p>

      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:20,marginBottom:32}}>
        {[
          {t:"눈 피로 ↓",d:"호박 베이스 제거 → 차가운 흰색 + 진한 잉크. AAA 16.7:1 콘트라스트. 액센트는 빨강 ≤5%만."},
          {t:"한눈에 데이터",d:"KPI 숫자 24px → 40px (+ 스파크라인 인라인). 본문 13px → 14px. 진척바 표 안에 직접."},
          {t:"스크롤 제거",d:"벤토 그리드 (1440×900 고정). 페이지 스크롤 0. 영역별 내부 스크롤만. 사이드바 + 상단바 고정."},
          {t:"트렌드 부합",d:"세그먼트 컨트롤 / 다크 잉크 칩 / 도넛 + 카드 elevation. SaaS 트레이드 드레스 직접 모방 X."},
        ].map((p,i)=>(
          <div key={i} style={{padding:24,background:"var(--surface-2)",borderRadius:14,borderLeft:"3px solid var(--knk-red)"}}>
            <div className="num" style={{fontSize:11,color:"var(--knk-red)",fontWeight:700,marginBottom:8,letterSpacing:"0.04em"}}>0{i+1}</div>
            <h3 style={{fontSize:20,marginBottom:8,letterSpacing:"-0.01em"}}>{p.t}</h3>
            <p style={{fontSize:14,color:"var(--ink-3)",lineHeight:1.6}}>{p.d}</p>
          </div>
        ))}
      </div>

      <div style={{padding:24,background:"var(--surface-inset)",borderRadius:14,border:"1px solid var(--line)"}}>
        <h3 style={{fontSize:18,marginBottom:12}}>다음 단계</h3>
        <ol style={{fontSize:14,color:"var(--ink-2)",lineHeight:2,paddingLeft:20,margin:0}}>
          <li>이 v2 방향성 확정 (이 메시지에서 OK)</li>
          <li>나머지 페이지 (견적 / 고객사 / 미수금 / 생산현황 / 납품수금 / 결재함)도 같은 시스템으로 발행</li>
          <li><span className="num">assets/haist-tokens-v2.css</span> 빅터 합성 — Jinja base.html에 link 한 줄 + page-* 페이지별 리팩토링</li>
          <li>다크 모드 / 모바일 리액티브 옵션 (필요 시)</li>
        </ol>
      </div>
    </div>
  </div>
);

// Expose primitives so 시안1-po-mockups.jsx can compose the same chrome and mount the App.
Object.assign(window, {
  TopBar, Sidebar, PageHead, Sparkline, Bar, Trend, Mgmt, BizChip, StatusChip,
  SalesHome, OrdersPage, ProjectDetail, CalendarPage, DailyWork, TokensV2, ComponentsV2, Closing,
});
