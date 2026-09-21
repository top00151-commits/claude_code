#!/bin/bash
# 사용: killport.sh <port> — 그 포트를 듣는 프로세스를 멈추고, 비었는지 확인(비면 0)
# 🔴 netstat 는 포트가 LISTENING 보다 먼저 찍힌다 → 'LISTENING.*:port' grep 은 아무것도 못 잡았다(2026-09-21 23:3x 발견)
P="$1"
powershell -NoProfile -Command "Get-NetTCPConnection -State Listen -LocalPort $P -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id \$_.OwningProcess -Force -ErrorAction SilentlyContinue }" >/dev/null 2>&1
for i in $(seq 1 20); do
  powershell -NoProfile -Command "if (Get-NetTCPConnection -State Listen -LocalPort $P -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }" >/dev/null 2>&1 && exit 0
  sleep 1
done
exit 1
