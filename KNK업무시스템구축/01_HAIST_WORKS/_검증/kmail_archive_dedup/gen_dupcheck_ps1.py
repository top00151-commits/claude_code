# -*- coding: utf-8 -*-
"""dupcheck_a.py · dupcheck_b.py 를 그대로 품은 대표 실행용 .ps1 을 만든다(시험한 파이썬과 글자가 어긋나지 않게)."""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]
A = io.open(os.path.join(HERE, "dupcheck_a.py"), encoding="ascii").read().replace("\r\n", "\n").rstrip("\n")
B = io.open(os.path.join(HERE, "dupcheck_b.py"), encoding="ascii").read().replace("\r\n", "\n").rstrip("\n")
for name, src in (("A", A), ("B", B)):
    assert "PYEOF" not in src and "\n'@" not in src, name

PS = r'''# ============================================================
# Old mail archive - DUPLICATE CHECK.  READ ONLY.  2026-11-16.
#
# WHY: CEO decision 2026-11-16: "keep the old mail as an archive only; delete the
#      duplicate mails so they do not take up space". Before anything is deleted
#      we COUNT, with the real data:
#        (1) container KNKHAIST.MAIL (ssh 32203) - the old archive /opt/knk_mail/data/mail.db
#            how many mails are exact copies of another mail in the archive
#        (2) container KNKHAIST (ssh 32201) - the WORKS mailbox
#            how many archive mails are ALSO in WORKS (so the archive copy is redundant)
#
# !! READ ONLY !!  Both databases are opened read-only. Nothing is written, deleted,
#    restarted or stopped. No temporary file is created on the servers.
# !! NO MAIL CONTENT leaves the server or reaches the screen: no subject, no address,
#    no body, no file name. Only counts, sizes, dates and short one-way fingerprints
#    (8 hex digits of a hash) are handed from step 1 to step 2, packed, in memory.
# ASCII-ONLY (PowerShell 5.1 mis-reads UTF-8 -> Korean breaks the remote script).
#
# Usage (PowerShell):  ./kmail_old_archive_dupcheck_readonly.ps1
#   It connects twice (32203, then 32201). Type the SSH password each time.
#   Step 1 prints nothing until it ends (it reads about 220 MB) - wait a little.
#   Then paste the whole output back to Victor.
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [string]$User    = "root"
)
$ErrorActionPreference = "Continue"

# NOTE: PowerShell names are case-insensitive - keep these names different from the parameters above.
function Get-Remote([int]$Port, [string]$bash, [string]$packed = "") {
    $sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15")
    # the remote side is bash: it must get LF only
    $bash = $bash -replace "`r`n", "`n"
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    $cmd = "echo $b64 | base64 -d | bash"
    if ($packed) { $cmd = "export OLD_GZ_B64=$packed; " + $cmd }
    if ($cmd.Length -gt 31000) {
        Write-Host ("ABORT: the command would be too long ({0} characters). Nothing was run. Tell Victor." -f $cmd.Length) -ForegroundColor Red
        return $null
    }
    ssh @sshOpts "$User@$SshHost" $cmd
}

$bodyA = @'
set +e
[ "$(hostname)" = "KNKHAIST.MAIL" ] || { echo "ABORT: this is not container KNKHAIST.MAIL. Nothing was read."; exit 10; }
PY=${KNK_DUPCHECK_PY:-/opt/knk_mail/.venv/bin/python}
[ -x "$PY" ] || { echo "ABORT: $PY not found. Nothing was read."; exit 11; }
"$PY" - <<'PYEOF'
__PY_A__
PYEOF
'@

$bodyB = @'
set +e
[ "$(hostname)" = "KNKHAIST" ] || { echo "ABORT: this is not container KNKHAIST. Nothing was read."; exit 10; }
PY=${KNK_DUPCHECK_PY:-/opt/knk_haist/.venv/bin/python}
[ -x "$PY" ] || { echo "ABORT: $PY not found. Nothing was read."; exit 11; }
"$PY" - <<'PYEOF'
__PY_B__
PYEOF
'@

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Old mail archive - duplicate check - READ ONLY" -ForegroundColor Cyan
Write-Host "  counts and sizes only / no mail content / nothing is changed" -ForegroundColor Yellow
Write-Host "=================================================="
Write-Host ""
Write-Host ">>> (1/2) KNKHAIST.MAIL - ssh port 32203   (type the SSH password)" -ForegroundColor Green
Write-Host "    reading the old archive ... nothing is shown until it ends (about 220 MB) - please wait"
$outA = @(Get-Remote 32203 $bodyA | ForEach-Object { "$_" })
$packLines = @($outA | Where-Object { $_ -match '^(H|U)\|' })
$outA | Where-Object { $_ -notmatch '^(H|U)\|' } | ForEach-Object { Write-Host $_ }
$doneA = @($outA | Where-Object { $_ -match '^\[done 32203\]' }).Count
if ($doneA -eq 0 -or $packLines.Count -eq 0) {
    Write-Host ""
    Write-Host "ABORT: step 1 did not finish (see above). Step 2 was NOT run. Paste this output to Victor." -ForegroundColor Red
    return
}

# pack the fingerprints (ASCII text -> gzip -> base64), all in memory
$raw = [Text.Encoding]::ASCII.GetBytes(($packLines -join "`n"))
$ms = New-Object System.IO.MemoryStream
$gz = New-Object System.IO.Compression.GZipStream($ms, [System.IO.Compression.CompressionMode]::Compress)
$gz.Write($raw, 0, $raw.Length)
$gz.Close()
$packed = [Convert]::ToBase64String($ms.ToArray())
Write-Host ""
Write-Host ("    handing over {0} fingerprint lines ({1} characters packed) - no mail content" -f $packLines.Count, $packed.Length)
Write-Host ""
Write-Host ">>> (2/2) KNKHAIST - ssh port 32201   (type the SSH password)" -ForegroundColor Green
Get-Remote 32201 $bodyB $packed

Write-Host ""
Write-Host "[check finished] Nothing was changed. Please paste the whole output to Victor." -ForegroundColor Green
'''
PS = PS.replace("__PY_A__", A).replace("__PY_B__", B)
assert "__PY_" not in PS
PS.encode("ascii")
io.open(OUT, "w", encoding="ascii", newline="\n").write(PS)
print("generated", OUT, len(PS), "bytes")
