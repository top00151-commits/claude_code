# -*- coding: utf-8 -*-
"""dedup_1/2/3 · purge · restore 파이썬을 그대로 품은 대표 실행용 .ps1 을 만든다(시험한 글자와 어긋나지 않게)."""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1]


def py(name):
    s = io.open(os.path.join(HERE, name), encoding="ascii").read().replace("\r\n", "\n").rstrip("\n")
    assert "PYEOF" not in s and "\n'@" not in s, name
    return s


PS = r'''# ============================================================
# Old mail archive - REMOVE DUPLICATES.  2026-11-16.
#
# CEO decision 2026-11-16: "keep the old mail as an archive only; delete the duplicate
# mails so they do not take up space".
# The read-only check of the same day found: 464 archived mails, of which about 459
# are duplicates (3 exact copies inside the archive + 456 fully present in WORKS).
#
#   -Apply         three connections, three SSH passwords:
#                  1) KNKHAIST.MAIL (32203)  read the archive            (read only)
#                  2) KNKHAIST      (32201)  compare with WORKS          (read only)
#                     a mail counts as "in WORKS" only if: same owner, same sender+subject+text,
#                     the WORKS mail is NOT in the trash, and EVERY attachment is in that WORKS
#                     mail with its file really on disk (each file is re-read and re-hashed)
#                  -- you are shown the numbers and must type DELETE --
#                  3) KNKHAIST.MAIL (32203)  backup -> delete -> verify -> compact
#                     a full backup copy is made and VERIFIED first, and is KEPT.
#                     if any check fails, nothing is changed (or the backup is put back).
#   -PurgeBackup   remove the backup copy made by -Apply (this is what finally frees the space)
#   -Restore       put the backup back (undo of -Apply; only possible before -PurgeBackup)
#
# !! Only the OLD archive (/opt/knk_mail/data/mail.db) is ever written. WORKS is only READ.
# !! No mail content reaches the screen or leaves the servers: counts, sizes and short
#    one-way fingerprints only.
# ASCII-ONLY (PowerShell 5.1 mis-reads UTF-8 -> Korean breaks the remote script).
#
# Usage (PowerShell):  ./kmail_old_archive_dedup.ps1 -Apply
# ============================================================
param(
    [switch]$Apply,
    [switch]$PurgeBackup,
    [switch]$Restore,
    [string]$SshHost = "o.knknara.co.kr",
    [string]$User    = "root"
)
$ErrorActionPreference = "Continue"

# NOTE: PowerShell names are case-insensitive - variable names below must differ from the parameters above.
function Get-Remote([int]$Port, [string]$bash, [string]$envName = "", [string]$envValue = "") {
    $sshOpts = @("-p", "$Port", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=15")
    $bash = $bash -replace "`r`n", "`n"
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($bash))
    $cmd = "echo $b64 | base64 -d | bash"
    if ($envName) { $cmd = "export $envName=$envValue; " + $cmd }
    if ($cmd.Length -gt 31000) {
        Write-Host ("ABORT: the command would be too long ({0} characters). Nothing was run. Tell Victor." -f $cmd.Length) -ForegroundColor Red
        return $null
    }
    ssh @sshOpts "$User@$SshHost" $cmd
}

function Pack-Lines([string[]]$lines) {
    $raw = [Text.Encoding]::ASCII.GetBytes(($lines -join "`n"))
    $ms = New-Object System.IO.MemoryStream
    $gz = New-Object System.IO.Compression.GZipStream($ms, [System.IO.Compression.CompressionMode]::Compress)
    $gz.Write($raw, 0, $raw.Length)
    $gz.Close()
    return [Convert]::ToBase64String($ms.ToArray())
}

$guardMail = @'
set +e
[ "$(hostname)" = "KNKHAIST.MAIL" ] || { echo "ABORT: this is not container KNKHAIST.MAIL. Nothing was changed."; exit 10; }
PY=${KNK_DEDUP_PY:-/opt/knk_mail/.venv/bin/python}
[ -x "$PY" ] || { echo "ABORT: $PY not found. Nothing was changed."; exit 11; }
'@
$guardStopped = @'
if pgrep -f '/opt/knk_mail/mail_watchdog\.sh|/opt/knk_mail/.*run\.py' >/dev/null 2>&1; then
  echo "ABORT: the old mail app (or its watchdog) is running - the archive must not be touched while it runs. Nothing was changed."
  exit 12
fi
'@
$guardWorks = @'
set +e
[ "$(hostname)" = "KNKHAIST" ] || { echo "ABORT: this is not container KNKHAIST. Nothing was read."; exit 10; }
PY=${KNK_DEDUP_PY:-/opt/knk_haist/.venv/bin/python}
[ -x "$PY" ] || { echo "ABORT: $PY not found. Nothing was read."; exit 11; }
'@

$py1 = @'
__PY_1__
'@
$py2 = @'
__PY_2__
'@
$py3 = @'
__PY_3__
'@
$pyPurge = @'
__PY_PURGE__
'@
$pyRestore = @'
__PY_RESTORE__
'@

function Wrap-Py([string]$guard, [string]$pyText) {
    return $guard + "`n" + '"$PY" - <<' + "'PYEOF'`n" + $pyText + "`nPYEOF`n"
}

$picked = @(@($Apply.IsPresent, $PurgeBackup.IsPresent, $Restore.IsPresent) | Where-Object { $_ }).Count
if ($picked -ne 1) {
    Write-Host "Choose exactly ONE of:  -Apply   -PurgeBackup   -Restore" -ForegroundColor Yellow
    Write-Host "  -Apply        remove the duplicates from the OLD archive (backup first; 3 SSH passwords)"
    Write-Host "  -PurgeBackup  remove the backup made by -Apply (frees the space; cannot be undone)"
    Write-Host "  -Restore      put the backup back (undo of -Apply)"
    return
}

Write-Host "==================================================" -ForegroundColor Cyan
if ($Apply) {
    Write-Host "  Old mail archive - remove duplicates" -ForegroundColor Cyan
    Write-Host "  read archive -> compare with WORKS -> (you confirm) -> backup, delete, verify" -ForegroundColor Yellow
    Write-Host "=================================================="
    Write-Host ""
    Write-Host ">>> (1/3) KNKHAIST.MAIL - ssh 32203 - read the archive   (type the SSH password)" -ForegroundColor Green
    Write-Host "    nothing is shown until it ends (about 220 MB) - please wait"
    $out1 = @(Get-Remote 32203 (Wrap-Py $guardMail $py1) | ForEach-Object { "$_" })
    $out1 | Where-Object { $_ -notmatch '^(M|U|S)\|' } | ForEach-Object { Write-Host $_ }
    $pack1 = @($out1 | Where-Object { $_ -match '^(M|U)\|' })
    $snapLine = @($out1 | Where-Object { $_ -match '^S\|' })
    if (@($out1 | Where-Object { $_ -match '^\[step1 done\]' }).Count -eq 0 -or $pack1.Count -eq 0 -or $snapLine.Count -ne 1) {
        Write-Host "ABORT: step 1 did not finish. Nothing was changed. Paste this output to Victor." -ForegroundColor Red
        return
    }
    Write-Host ""
    Write-Host ">>> (2/3) KNKHAIST - ssh 32201 - compare with WORKS (read only)   (type the SSH password)" -ForegroundColor Green
    Write-Host "    the WORKS attachment files are re-read one by one - this can take a little while"
    $out2 = @(Get-Remote 32201 (Wrap-Py $guardWorks $py2) "OLD_GZ_B64" (Pack-Lines $pack1) | ForEach-Object { "$_" })
    $out2 | Where-Object { $_ -notmatch '^(D|C)\|' } | ForEach-Object { Write-Host $_ }
    $delLines = @($out2 | Where-Object { $_ -match '^D\|' })
    $countLine = @($out2 | Where-Object { $_ -match '^C\|' })
    if (@($out2 | Where-Object { $_ -match '^\[step2 done\]' }).Count -eq 0 -or $countLine.Count -ne 1) {
        Write-Host "ABORT: step 2 did not finish. Nothing was changed. Paste this output to Victor." -ForegroundColor Red
        return
    }
    $nums = $countLine[0].Split("|")
    if ([int]$nums[2] -ne $delLines.Count) {
        Write-Host "ABORT: the delete list is incomplete. Nothing was changed. Paste this output to Victor." -ForegroundColor Red
        return
    }
    Write-Host ""
    Write-Host "--------------------------------------------------" -ForegroundColor Yellow
    Write-Host ("  OLD archive: {0} mails.   Fully present in WORKS: {1} mails." -f $nums[1], $nums[2]) -ForegroundColor Yellow
    Write-Host "  Step 3 will PERMANENTLY remove from the OLD archive:" -ForegroundColor Yellow
    Write-Host ("    - those {0} mails (WORKS keeps its own copy - WORKS is not touched)" -f $nums[2]) -ForegroundColor Yellow
    Write-Host "    - exact copies inside the archive (one of each is kept)" -ForegroundColor Yellow
    Write-Host "  A full backup is made and verified first, and is kept until you run -PurgeBackup." -ForegroundColor Yellow
    Write-Host "--------------------------------------------------" -ForegroundColor Yellow
    $answer = Read-Host "Type DELETE (capital letters) to continue, anything else to stop"
    if ($answer -cne "DELETE") {
        Write-Host "Stopped. Nothing was changed." -ForegroundColor Green
        return
    }
    Write-Host ""
    Write-Host ">>> (3/3) KNKHAIST.MAIL - ssh 32203 - backup, delete, verify   (type the SSH password)" -ForegroundColor Green
    Get-Remote 32203 (Wrap-Py ($guardMail + "`n" + $guardStopped) $py3) "DEL_GZ_B64" (Pack-Lines ($delLines + $snapLine))
} elseif ($PurgeBackup) {
    Write-Host "  Old mail archive - remove the backup copy" -ForegroundColor Cyan
    Write-Host "=================================================="
    Write-Host "  This removes the backup made by -Apply. After this, -Restore is no longer possible." -ForegroundColor Yellow
    $answer = Read-Host "Type PURGE (capital letters) to continue, anything else to stop"
    if ($answer -cne "PURGE") {
        Write-Host "Stopped. Nothing was changed." -ForegroundColor Green
        return
    }
    Write-Host "(type the SSH password)" -ForegroundColor Green
    Get-Remote 32203 (Wrap-Py $guardMail $pyPurge)
} else {
    Write-Host "  Old mail archive - put the backup back (undo)" -ForegroundColor Cyan
    Write-Host "=================================================="
    $answer = Read-Host "Type RESTORE (capital letters) to continue, anything else to stop"
    if ($answer -cne "RESTORE") {
        Write-Host "Stopped. Nothing was changed." -ForegroundColor Green
        return
    }
    Write-Host "(type the SSH password)" -ForegroundColor Green
    Get-Remote 32203 (Wrap-Py ($guardMail + "`n" + $guardStopped) $pyRestore)
}
Write-Host ""
Write-Host "[finished] Please paste the whole output to Victor." -ForegroundColor Green
'''
for key, name in (("__PY_1__", "dedup_1.py"), ("__PY_2__", "dedup_2.py"), ("__PY_3__", "dedup_3.py"),
                  ("__PY_PURGE__", "dedup_purge.py"), ("__PY_RESTORE__", "dedup_restore.py")):
    assert PS.count(key) == 1, key
    PS = PS.replace(key, py(name))
assert "__PY_" not in PS
PS.encode("ascii")
io.open(OUT, "w", encoding="ascii", newline="\n").write(PS)
print("generated", os.path.basename(OUT), len(PS), "bytes")
