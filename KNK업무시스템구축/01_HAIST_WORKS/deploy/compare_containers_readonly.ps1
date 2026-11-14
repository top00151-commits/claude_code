# ============================================================
# Are ssh:32201 and ssh:32203 THE SAME container or TWO? - READ ONLY. 2026-11-14.
#
# WHY: Session 10 saw only 4 containers in DSM Docker
#      (KNKDEV / KNKGIT / KNKHAIST / Portainer) - no KNKHAIST.MAIL.
#      But my 32203 probe reported hostname "KNKHAIST.MAIL" AND had no supervisorctl,
#      while KNKHAIST definitely has supervisorctl (used it during the Aug outage).
#      => The two readings disagree. Guessing here is dangerous:
#         if they ARE one container, stopping "the old mail app" the wrong way
#         could take down WORKS + Eum + portal.
#      This script settles it with facts.
#
# !! READ ONLY !!  No writes, no restarts, no stop, no deploy. Reads identity only.
#    No mail content, no secrets - not even secret NAMES here.
# ASCII-ONLY (PowerShell 5.1 mis-reads UTF-8 -> Korean breaks the remote script).
#
# Usage (PowerShell):  ./compare_containers_readonly.ps1
#   You will be asked for the SSH password TWICE (once per port).
# ============================================================
param(
    [string]$SshHost = "o.knknara.co.kr",
    [string]$User    = "root",
    [int[]]$Ports    = @(32201, 32203)
)
$ErrorActionPreference = "Continue"

$probe = @'
set +e
echo "hostname        : $(hostname)"
echo "etc_hostname    : $(cat /etc/hostname 2>/dev/null)"
echo "machine_id      : $(cat /etc/machine-id 2>/dev/null || echo NONE)"
echo "boot_id         : $(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo NONE)"
echo "pid1_cmd        : $(tr '\0' ' ' < /proc/1/cmdline 2>/dev/null)"
echo "pid1_started    : $(stat -c %y /proc/1 2>/dev/null | cut -c1-19)"
echo "uptime          : $(cut -d' ' -f1 /proc/uptime 2>/dev/null) sec"
echo "supervisorctl   : $(command -v supervisorctl >/dev/null 2>&1 && echo PRESENT || echo absent)"
for D in /opt/knk_haist /opt/knk_mail /opt/knk_messenger /opt/knk_msg; do
  if [ -d "$D" ]; then echo "dir $D : EXISTS ($(du -sh $D 2>/dev/null | cut -f1))"; else echo "dir $D : -"; fi
done
echo "proc_count      : $(ls -1 /proc 2>/dev/null | grep -cE '^[0-9]+$')"
echo "-- processes (name only) --"
(ps -eo pid,etime,comm 2>/dev/null || ps -eo pid,comm 2>/dev/null) | head -14
echo "-- listening ports (if tool exists) --"
(ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | awk 'NR>1{print "   "$4}' | head -10
if [ ! -x "$(command -v ss)" ] && [ ! -x "$(command -v netstat)" ]; then
  echo "   (ss/netstat missing - reading /proc/net/tcp)"
  awk 'NR>1{split($2,a,":"); p=strtonum("0x" a[2]); if(p>0) print "   port " p}' /proc/net/tcp 2>/dev/null | sort -u | head -10
fi
echo "[end]"
'@
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($probe))

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Same container or two?  (READ ONLY)" -ForegroundColor Cyan
Write-Host "  nothing is stopped / restarted / changed" -ForegroundColor Yellow
Write-Host "  type the SSH password once per port" -ForegroundColor Yellow
Write-Host "=================================================="

foreach ($p in $Ports) {
    Write-Host ""
    Write-Host "########## ssh port $p ##########" -ForegroundColor Green
    ssh -p $p -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "$User@$SshHost" "echo $b64 | base64 -d | bash"
}

Write-Host ""
Write-Host "HOW TO READ IT:" -ForegroundColor Cyan
Write-Host "  machine_id / boot_id / pid1_started SAME on both  -> ONE container (two ssh doors)"
Write-Host "  any of them DIFFERENT                            -> TWO separate containers"
Write-Host ""
Write-Host "[DONE] Paste the FULL output above to Victor (session 15_KNK_Mail)." -ForegroundColor Green
