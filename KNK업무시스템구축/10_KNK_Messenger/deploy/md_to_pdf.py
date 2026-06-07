#!/usr/bin/env python3
"""
Markdown → PDF 변환 스크립트 (Chrome 헤드리스 렌더링)
한글 폰트(맑은 고딕) · A4 · 인쇄 적합 형식
"""
import sys, os, re, subprocess, tempfile, textwrap
import markdown

_DEF_IN  = r"C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\10_KNK_Messenger\deploy\서버담당자_HTTPS_작업서.md"
_DEF_OUT = r"C:\Users\top00\JR\Claude 코드\KNK업무시스템구축\10_KNK_Messenger\deploy\서버담당자_HTTPS_작업서.pdf"
# 사용법: python md_to_pdf.py [입력.md] [출력.pdf] [문서제목]  (인자 없으면 기존 HTTPS 작업서 변환)
INPUT  = sys.argv[1] if len(sys.argv) > 1 else _DEF_IN
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else _DEF_OUT
TITLE  = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(os.path.basename(OUTPUT))[0]
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

CSS = """
@page {
  size: A4;
  margin: 20mm 18mm 22mm 18mm;
  @top-right { content: "__DOC_TITLE__"; font-size: 9pt; color: #888; font-family: 'Malgun Gothic', sans-serif; }
  @bottom-center { content: counter(page) " / " counter(pages); font-size: 9pt; color: #888; font-family: 'Malgun Gothic', sans-serif; }
}

* { box-sizing: border-box; }

body {
  font-family: 'Malgun Gothic', '맑은 고딕', 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif;
  font-size: 10pt;
  line-height: 1.7;
  color: #1a1a1a;
  background: #fff;
  word-break: keep-all;
}

h1 {
  font-size: 16pt;
  font-weight: 700;
  border-bottom: 2.5px solid #1a73e8;
  padding-bottom: 6px;
  margin: 0 0 14px;
  color: #0d47a1;
  page-break-after: avoid;
}

h2 {
  font-size: 13pt;
  font-weight: 700;
  border-left: 4px solid #1a73e8;
  padding-left: 10px;
  margin: 22px 0 10px;
  color: #1565c0;
  page-break-after: avoid;
}

h3 {
  font-size: 11pt;
  font-weight: 700;
  margin: 16px 0 8px;
  color: #1a237e;
  page-break-after: avoid;
}

h4 {
  font-size: 10.5pt;
  font-weight: 700;
  margin: 12px 0 6px;
  color: #283593;
  page-break-after: avoid;
}

p {
  margin: 0 0 8px;
}

a {
  color: #1a73e8;
  text-decoration: none;
}

strong { font-weight: 700; }
em { font-style: italic; }

code {
  background: #f1f3f4;
  border: 1px solid #dadce0;
  border-radius: 3px;
  padding: 1px 5px;
  font-family: 'Consolas', 'D2Coding', 'Courier New', monospace;
  font-size: 9pt;
  color: #d32f2f;
}

pre {
  background: #f8f9fa;
  border: 1px solid #e0e0e0;
  border-left: 4px solid #1a73e8;
  border-radius: 4px;
  padding: 10px 14px;
  font-family: 'Consolas', 'D2Coding', 'Courier New', monospace;
  font-size: 8.5pt;
  line-height: 1.5;
  overflow: visible;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 8px 0 12px;
  page-break-inside: avoid;
}

pre code {
  background: none;
  border: none;
  padding: 0;
  color: #212121;
  font-size: inherit;
}

blockquote {
  border-left: 4px solid #bdbdbd;
  margin: 8px 0;
  padding: 4px 12px;
  color: #555;
  background: #fafafa;
}

hr {
  border: none;
  border-top: 1.5px solid #e0e0e0;
  margin: 18px 0;
}

/* 표 */
table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 14px;
  font-size: 9.5pt;
  page-break-inside: avoid;
}

th {
  background: #1565c0;
  color: #fff;
  padding: 6px 10px;
  text-align: left;
  font-weight: 700;
  border: 1px solid #0d47a1;
}

td {
  padding: 5px 10px;
  border: 1px solid #dee2e6;
  vertical-align: top;
}

tr:nth-child(even) td {
  background: #f5f8ff;
}

tr:last-child td {
  border-bottom: 1.5px solid #90caf9;
}

/* 목록 */
ul, ol {
  margin: 4px 0 10px 0;
  padding-left: 22px;
}

li {
  margin-bottom: 4px;
}

/* 체크박스 목록 */
li.task-list-item {
  list-style: none;
  margin-left: -18px;
}

li.task-list-item input[type=checkbox] {
  margin-right: 6px;
  width: 13px;
  height: 13px;
  accent-color: #1a73e8;
}

/* 메타 정보 블록 (문서 헤더) */
.meta-block {
  background: #e8f0fe;
  border: 1px solid #90caf9;
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 16px;
  font-size: 9.5pt;
  line-height: 1.8;
}

/* 강조 박스 */
.notice-box {
  background: #fff3e0;
  border-left: 4px solid #ff9800;
  padding: 8px 12px;
  margin: 8px 0;
  border-radius: 2px;
  font-size: 9.5pt;
}

/* 페이지 나누기 */
.page-break { page-break-after: always; }

/* 들여쓰기 코드 (중첩 목록에 있는 코드) */
li code { font-size: 8.5pt; }

/* 섹션 구분 */
section {
  margin-bottom: 20px;
}
"""

def preprocess_md(text: str) -> str:
    """체크박스·이모지 전처리"""
    # 체크박스: - [ ] → 실제 HTML checkbox (markdown-extensions 로 처리됨)
    # 이모지는 그대로 유지 (Chrome이 렌더링)
    return text

def build_html(md_text: str) -> str:
    md_proc = preprocess_md(md_text)

    # markdown → HTML 변환
    md_parser = markdown.Markdown(extensions=[
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.nl2br',
        'markdown.extensions.toc',
        'markdown.extensions.sane_lists',
        'markdown.extensions.def_list',
        'markdown.extensions.attr_list',
        'markdown.extensions.md_in_html',
    ])

    body_html = md_parser.convert(md_proc)

    # 체크박스 후처리: - [ ] and - [x] 항목을 checkbox input으로 변환
    # markdown이 <li>[ ] ... 로 변환하는 것을 실제 체크박스로
    body_html = re.sub(r'<li>\s*\[ \]', '<li class="task-list-item"><input type="checkbox" disabled>', body_html)
    body_html = re.sub(r'<li>\s*\[x\]', '<li class="task-list-item"><input type="checkbox" checked disabled>', body_html)
    body_html = re.sub(r'<li>\s*\[X\]', '<li class="task-list-item"><input type="checkbox" checked disabled>', body_html)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>서버 담당자 작업 지시서 — KNK 메신저 HTTPS 전환</title>
<style>
{CSS.replace("__DOC_TITLE__", TITLE)}
</style>
</head>
<body>
{body_html}
</body>
</html>"""
    return html


def main():
    print(f"[1/4] 마크다운 읽기: {INPUT}")
    with open(INPUT, encoding='utf-8') as f:
        md_text = f.read()

    print("[2/4] HTML 변환 중...")
    html_content = build_html(md_text)

    # 임시 HTML 파일 저장
    tmp_html = os.path.join(tempfile.gettempdir(), "knk_https_guide.html")
    with open(tmp_html, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"       HTML 임시 저장: {tmp_html}")

    print("[3/4] Chrome 헤드리스로 PDF 생성 중...")
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-extensions",
        "--run-all-compositor-stages-before-draw",
        "--print-to-pdf-no-header",
        f"--print-to-pdf={OUTPUT}",
        "--no-pdf-header-footer",
        f"file:///{tmp_html.replace(os.sep, '/')}"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if result.returncode != 0:
        print(f"  Chrome stderr: {result.stderr[:500]}")

    if os.path.exists(OUTPUT) and os.path.getsize(OUTPUT) > 1000:
        size_kb = os.path.getsize(OUTPUT) // 1024
        print(f"[4/4] ✅ PDF 생성 완료: {OUTPUT} ({size_kb} KB)")
    else:
        print(f"[4/4] ❌ PDF 생성 실패 또는 파일 크기 이상")
        print(f"  returncode: {result.returncode}")
        print(f"  stderr: {result.stderr[:500]}")
        sys.exit(1)

if __name__ == "__main__":
    main()
