# ============================================================
# Are ssh:32201 and ssh:32203 THE SAME container or TWO? - READ ONLY. 2026-11-14.
#
# WHY: Session 10 saw only 4 containers in DSM Docker
#      (KNKDEV / KNKGIT / KNKHAIST / Portainer) - no KNKHAIST.MAIL
#      (though that card row was cut off on the right, so more may exist).
#      But my 32203 probe reported hostname "KNKHAIST.MAIL" AND had no supervisorctl,
#      while KNKHAIST definitely has supervisorctl (used during the Aug outage).
#      => The two readings disagree. Guessing is dangerous: if they ARE one container,
#         stopping "the old mail app" the wrong way could take down WORKS + Eum + portal.
#
# !! READ ONLY !!  No writes, no restarts, no stop, no deploy. Identity only.
#    No mail content, no secrets - not even secret NAMES here.
# ASCII-ONLY (PowerShell 5.1 mis-reads UTF-8 -> Korean breaks the remote script).
#
# !! HOW WE DECIDE (corrected 2026-11-14 after session 10's catch) !!
#   DO NOT use boot_id  : /proc/sys/kernel/random/boot_id comes from the HOST kernel,
#                         so separate containers show the SAME value. Useless here.
#   DO NOT use machine_id alone : baked into the image - clones share it.
#   USE namespace inodes: /proc/self/ns/{pid,net,mnt}. Different inode = different
#                         namespace = DIFFERENT container. Same inode = same container.
#   USE the cross-visibility test: if port 32201 can SEE the old mail processes
#                         (run.py / mail_watchdog.sh), they share a PID namespace
#                         => same container.
#
# Usage (PowerShell):  ./compare_containers_readonly.ps1
#   You will be asked for the SSH password ONCE PER PORT.
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
echo ""
echo "--- DECIDING MARKS (compare these between the two ports) ---"
echo "ns_pid          : $(readlink /proc/self/ns/pid  2>/dev/null)"
echo "ns_net          : $(readlink /proc/self/ns/net  2>/dev/null)"
echo "ns_mnt          : $(readlink /proc/self/ns/mnt  2>/dev/null)"
CID1=$(grep -oE '[0-9a-f]{64}' /proc/1/cgroup 2>/dev/null | head -1)
CID2=$(grep -oE '[0-9a-f]{64}' /proc/self/mountinfo 2>/dev/null | head -1)
echo "container_id(cgroup)    : ${CID1:-NONE}"
echo "container_id(mountinfo) : ${CID2:-NONE}"
echo ""
echo "--- NOT usable for deciding (shown only so nobody is tempted) ---"
echo "machine_id      : $(cat /etc/machine-id 2>/dev/null || echo NONE)   <- image clones share this"
echo "boot_id         : $(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo NONE)   <- HOST kernel, always same"
echo ""
echo "--- cross-visibility (decisive) ---"
PSOUT=$( (ps -eo pid,etime,args 2>/dev/null || ps aux 2>/dev/null) )
# !! match the FULL PATH. A bare "run.py" also matches the portal quality app
#    (/opt/knk_portal/src/quality/run.py) on 32201 -> false positive, wrong verdict.
#    Caught by session 10 on 2026-11-14 against real output.
echo "sees old-mail run.py        : $(echo "$PSOUT" | grep -c '[/]opt/knk_mail/run\.py')"
echo "sees old-mail watchdog      : $(echo "$PSOUT" | grep -c '[/]opt/knk_mail/mail_watchdog')"
echo "  (any run.py at all, FYI)  : $(echo "$PSOUT" | grep -c '[r]un\.py')   <- NOT a verdict"
echo "sees WORKS (knk_haist)      : $(echo "$PSOUT" | grep -c '[k]nk_haist')"
echo "sees messenger (knk_msg)    : $(echo "$PSOUT" | grep -cE '[k]nk_msg|[k]nk_messenger')"
echo "total processes             : $(ls -1 /proc 2>/dev/null | grep -cE '^[0-9]+$')"
echo ""
echo "--- environment ---"
echo "pid1_cmd        : $(tr '\0' ' ' < /proc/1/cmdline 2>/dev/null)"
echo "uptime          : $(cut -d' ' -f1 /proc/uptime 2>/dev/null) sec"
echo "supervisorctl   : $(command -v supervisorctl >/dev/null 2>&1 && echo PRESENT || echo absent)"
for D in /opt/knk_haist /opt/knk_mail /opt/knk_messenger /opt/knk_msg; do
  if [ -d "$D" ]; then echo "dir $D : EXISTS ($(du -sh $D 2>/dev/null | cut -f1))"; else echo "dir $D : -"; fi
done
echo "-- processes (first 14, name only) --"
echo "$PSOUT" | head -14
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
Write-Host "HOW TO READ IT" -ForegroundColor Cyan
Write-Host "  PRIMARY (trust these):  ns_pid and ns_mnt and container_id"
Write-Host "     DIFFER between the ports  -> TWO SEPARATE containers"
Write-Host "     IDENTICAL                 -> ONE container (two ssh doors)"
Write-Host ""
Write-Host "  ns_net may be IDENTICAL even for separate containers" -ForegroundColor Yellow
Write-Host "     (host network mode - that is why 5051 and 5053 share one port space)."
Write-Host "     So ns_net alone decides NOTHING."
Write-Host ""
Write-Host "  IGNORE machine_id and boot_id - they match even for separate containers." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Cross-visibility is only CORROBORATION, and only the FULL-PATH lines count:" -ForegroundColor Yellow
Write-Host "     'sees old-mail run.py / watchdog' use /opt/knk_mail/... and are meaningful."
Write-Host "     'any run.py at all' is NOT - the portal quality app is also a run.py."
Write-Host ""
Write-Host "[DONE] Paste the FULL output above to Victor (session 15_KNK_Mail)." -ForegroundColor Green
