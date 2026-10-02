# z1132b - 소모품 세금계산서 발행일의 "회차 표기" 정리 (2026-10-02)
#
#   2026-03-31-1  ->  2026-03-31   (뒤 -회차만 제거 · 43건)
#
# 그냥 실행하면 **확인만** 합니다(아무것도 바꾸지 않음).
# 실제로 바꾸려면 뒤에 -Apply 를 붙이세요.
#
#   확인 :  powershell -ExecutionPolicy Bypass -File "이 파일"
#   적용 :  powershell -ExecutionPolicy Bypass -File "이 파일" -Apply
#
# 적용하면 먼저 DB 사본을 뜨고(data/backups/knk.db.bak_z1132b_<시각>) 바꿉니다.
param([switch]$Apply)

$ErrorActionPreference = "Stop"
# 한글이 깨지지 않게 — PowerShell 이 파이프/화면에 쓰는 글자표를 UTF-8 로
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
try { $OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}
$mode = "CHECK"
if ($Apply) { $mode = "APPLY" }

Write-Host ""
Write-Host "=== 소모품 세금계산서 발행일 회차표기 정리 ($mode) ===" -ForegroundColor Cyan
Write-Host ""

$py = @'
import sqlite3, re, shutil, sys, datetime, os
MODE = sys.argv[1]
DB = "/opt/knk_haist/data/knk.db"
PAT = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{1,2})$")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
rows = []
for r in con.execute("SELECT id, mgmt_code, customer_name, tax_invoice_date FROM consumable_orders "
                     "WHERE tax_invoice_date IS NOT NULL AND TRIM(tax_invoice_date) <> ''"):
    m = PAT.match((r["tax_invoice_date"] or "").strip())
    if not m:
        continue
    d = m.group(1)
    try:
        datetime.datetime.strptime(d, "%Y-%m-%d")
    except ValueError:
        continue
    rows.append((r["id"], r["mgmt_code"], r["customer_name"], r["tax_invoice_date"], d, m.group(2)))

print("대상 %d건" % len(rows))
for x in rows[:50]:
    print("   %-10s %-22s %s  ->  %s   (회차 %s)" % (x[1] or "", (x[2] or "")[:22], x[3], x[4], x[5]))
if len(rows) > 50:
    print("   ... 외 %d건" % (len(rows) - 50))

if len(rows) > 60:
    print("!! 예상(43건)보다 훨씬 많습니다 - 멈춥니다. 빅터에게 알려 주세요.")
    sys.exit(2)

if MODE != "APPLY":
    print("")
    print("확인만 했습니다. 아무것도 바꾸지 않았습니다.")
    print("실제로 바꾸려면 -Apply 를 붙여 다시 실행하세요.")
    sys.exit(0)

ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
bak = "/opt/knk_haist/data/backups/knk.db.bak_z1132b_%s" % ts
os.makedirs(os.path.dirname(bak), exist_ok=True)
b = sqlite3.connect(bak)
con.backup(b)
b.close()
print("")
print("DB 사본: %s (%.0f MB)" % (bak, os.path.getsize(bak) / 1048576.0))

n = 0
for x in rows:
    cur = con.execute("UPDATE consumable_orders SET tax_invoice_date=? WHERE id=? AND tax_invoice_date=?",
                      (x[4], x[0], x[3]))
    n += cur.rowcount
con.commit()

left = con.execute("SELECT COUNT(*) FROM consumable_orders WHERE tax_invoice_date IS NOT NULL "
                   "AND TRIM(tax_invoice_date) <> '' "
                   "AND tax_invoice_date NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'").fetchone()[0]
ok = con.execute("PRAGMA integrity_check").fetchone()[0]
print("바꾼 건수 : %d" % n)
print("남은 비정상 발행일 : %d 건" % left)
print("DB 무결성 : %s" % ok)
con.close()
'@

# 파이프로 그냥 보내면 한글이 CP949 로 바뀌며 깨진다(실제로 겪음) → base64 로 실어 보낸다
$b64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($py))
ssh -p 32201 root@o.knknara.co.kr "echo $b64 | base64 -d > /tmp/_z1132b.py; python3 /tmp/_z1132b.py $mode; rm -f /tmp/_z1132b.py"

Write-Host ""
Write-Host "끝났습니다." -ForegroundColor Green
