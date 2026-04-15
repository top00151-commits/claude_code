"""
KNK 물류허브 — FastAPI 메인 앱
1단계: 부품 등록 (parts CRUD)
"""
import os
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import database as db

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title="HAIST WORKS")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATE_DIR)

# DB 초기화 (앱 시작 시 1회)
db.init_db()


# ─────────────────────────────────────────────────────────────
# 컨텍스트 헬퍼
# ─────────────────────────────────────────────────────────────
def ctx(request: Request, **extra) -> dict:
    """모든 템플릿에 공통 주입되는 컨텍스트"""
    return {
        "request": request,
        "app_name": "HAIST WORKS",
        "app_subtitle": "KNK 통합 업무 플랫폼",
        "company": "㈜케이엔케이",
        "brand": "HAIST Innovation",
        "slogan": "Human & AI create the Best",
        "lang": "ko",  # 향후 i18n: ko / vi / en
        "css_ver": "v=20260415b",
        **extra,
    }


# ─────────────────────────────────────────────────────────────
# 라우트
# ─────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    parts_stats = db.count_parts()
    proj_stats = db.count_projects()
    return templates.TemplateResponse(
        "home.html",
        ctx(request, parts_stats=parts_stats, proj_stats=proj_stats),
    )


# ── 부품 마스터 (parts) ────────────────────────────────────
@app.get("/parts", response_class=HTMLResponse)
async def parts_list(
    request: Request,
    q: str = "",
    biz_div: str = "",
    category: str = "",
):
    rows = db.list_parts(q=q, biz_div=biz_div, category=category)
    return templates.TemplateResponse(
        "parts.html",
        ctx(request, parts=rows, q=q, biz_div=biz_div, category=category),
    )


@app.get("/parts/new", response_class=HTMLResponse)
async def parts_new_form(request: Request):
    return templates.TemplateResponse("part_form.html", ctx(request, part=None))


@app.post("/parts/new")
async def parts_new_submit(
    part_no: str = Form(...),
    part_name: str = Form(...),
    spec: str = Form(""),
    maker: str = Form(""),
    origin: str = Form(""),
    unit: str = Form("EA"),
    currency: str = Form("KRW"),
    std_price: str = Form("0"),
    biz_div: str = Form(""),
    category: str = Form(""),
    note: str = Form(""),
    is_active: str = Form("1"),
):
    db.create_part({
        "part_no": part_no, "part_name": part_name, "spec": spec,
        "maker": maker, "origin": origin, "unit": unit,
        "currency": currency, "std_price": std_price,
        "biz_div": biz_div, "category": category, "note": note,
        "is_active": is_active,
    })
    return RedirectResponse("/parts", status_code=303)


@app.get("/parts/{pid}/edit", response_class=HTMLResponse)
async def parts_edit_form(request: Request, pid: int):
    part = db.get_part(pid)
    if not part:
        return RedirectResponse("/parts", status_code=303)
    return templates.TemplateResponse("part_form.html", ctx(request, part=part))


@app.post("/parts/{pid}/edit")
async def parts_edit_submit(
    pid: int,
    part_no: str = Form(...),
    part_name: str = Form(...),
    spec: str = Form(""),
    maker: str = Form(""),
    origin: str = Form(""),
    unit: str = Form("EA"),
    currency: str = Form("KRW"),
    std_price: str = Form("0"),
    biz_div: str = Form(""),
    category: str = Form(""),
    note: str = Form(""),
    is_active: str = Form("1"),
):
    db.update_part(pid, {
        "part_no": part_no, "part_name": part_name, "spec": spec,
        "maker": maker, "origin": origin, "unit": unit,
        "currency": currency, "std_price": std_price,
        "biz_div": biz_div, "category": category, "note": note,
        "is_active": is_active,
    })
    return RedirectResponse("/parts", status_code=303)


@app.post("/parts/{pid}/delete")
async def parts_delete(pid: int):
    db.delete_part(pid)
    return RedirectResponse("/parts", status_code=303)


# ── 프로젝트 / 관리코드 발행대장 ─────────────────────────
@app.get("/projects", response_class=HTMLResponse)
async def projects_list(
    request: Request,
    q: str = "",
    biz_div: str = "",
    stage: str = "",
    status: str = "",
):
    rows = db.list_projects(q=q, biz_div=biz_div, stage=stage, status=status)
    return templates.TemplateResponse(
        "projects.html",
        ctx(request, projects=rows, q=q, biz_div=biz_div, stage=stage, status=status,
            STAGES=db.STAGES, STATUSES=db.STATUSES),
    )


@app.get("/projects/new", response_class=HTMLResponse)
async def projects_new_form(request: Request):
    return templates.TemplateResponse(
        "project_form.html",
        ctx(request, project=None,
            STAGES=db.STAGES, STATUSES=db.STATUSES, PO_TYPES=db.PO_TYPES),
    )


@app.post("/projects/new")
async def projects_new_submit(
    biz_div: str = Form(...),
    project_name: str = Form(...),
    customer: str = Form(""),
    model: str = Form(""),
    stage: str = Form("제안작성"),
    po_type: str = Form("신규"),
    status: str = Form("수주예정"),
    customer_po: str = Form(""),
    currency: str = Form("KRW"),
    order_amount: str = Form("0"),
    order_date: str = Form(""),
    due_date: str = Form(""),
    pm: str = Form(""),
    sales: str = Form(""),
    note: str = Form(""),
):
    db.create_project({
        "biz_div": biz_div, "project_name": project_name, "customer": customer,
        "model": model, "stage": stage, "po_type": po_type, "status": status,
        "customer_po": customer_po, "currency": currency,
        "order_amount": order_amount, "order_date": order_date, "due_date": due_date,
        "pm": pm, "sales": sales, "note": note,
    })
    return RedirectResponse("/projects", status_code=303)


@app.get("/projects/{pid}/edit", response_class=HTMLResponse)
async def projects_edit_form(request: Request, pid: int):
    p = db.get_project(pid)
    if not p:
        return RedirectResponse("/projects", status_code=303)
    return templates.TemplateResponse(
        "project_form.html",
        ctx(request, project=p,
            STAGES=db.STAGES, STATUSES=db.STATUSES, PO_TYPES=db.PO_TYPES),
    )


@app.post("/projects/{pid}/edit")
async def projects_edit_submit(
    pid: int,
    biz_div: str = Form(...),
    project_name: str = Form(...),
    customer: str = Form(""),
    model: str = Form(""),
    stage: str = Form("제안작성"),
    po_type: str = Form("신규"),
    status: str = Form("수주예정"),
    customer_po: str = Form(""),
    currency: str = Form("KRW"),
    order_amount: str = Form("0"),
    order_date: str = Form(""),
    due_date: str = Form(""),
    pm: str = Form(""),
    sales: str = Form(""),
    note: str = Form(""),
):
    db.update_project(pid, {
        "biz_div": biz_div, "project_name": project_name, "customer": customer,
        "model": model, "stage": stage, "po_type": po_type, "status": status,
        "customer_po": customer_po, "currency": currency,
        "order_amount": order_amount, "order_date": order_date, "due_date": due_date,
        "pm": pm, "sales": sales, "note": note,
    })
    return RedirectResponse("/projects", status_code=303)


@app.post("/projects/{pid}/delete")
async def projects_delete(pid: int):
    db.delete_project(pid)
    return RedirectResponse("/projects", status_code=303)
