# KNK Messenger - single instance helper
# Brings an already-open KNK server window to the front instead of opening a new one.
#   Exit code 0 = found an existing server cmd window and focused it (already running)
#   Exit code 1 = no existing window (caller should start normally)
# 2026-05-27 fix: Match exact English title "KNK Messenger Server" only.
#   Previous Korean needle "메신저" matched other apps/browser tabs that contain
#   the word, causing the BAT to exit immediately at first launch.

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class KnkWin {
  public delegate bool EnumProc(IntPtr h, IntPtr p);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr p);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
}
"@

# needle = exact English cmd window title from 메신저START.bat (`title KNK Messenger Server`)
# Using ASCII so encoding is irrelevant. Specific enough to avoid false matches.
$needle = "KNK Messenger Server"

$script:found = [IntPtr]::Zero
$cb = [KnkWin+EnumProc]{
  param([IntPtr]$h, [IntPtr]$p)
  if (-not [KnkWin]::IsWindowVisible($h)) { return $true }
  $len = [KnkWin]::GetWindowTextLength($h)
  if ($len -le 0) { return $true }
  $sb = New-Object System.Text.StringBuilder ($len + 1)
  [void][KnkWin]::GetWindowText($h, $sb, $sb.Capacity)
  if ($sb.ToString().Contains($needle)) { $script:found = $h; return $false }
  return $true
}

[void][KnkWin]::EnumWindows($cb, [IntPtr]::Zero)

if ($script:found -ne [IntPtr]::Zero) {
  if ([KnkWin]::IsIconic($script:found)) { [void][KnkWin]::ShowWindow($script:found, 9) }  # 9 = SW_RESTORE
  [void][KnkWin]::SetForegroundWindow($script:found)
  exit 0
}
exit 1
