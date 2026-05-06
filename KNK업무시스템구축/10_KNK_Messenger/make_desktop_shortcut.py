"""KNK Messenger 바탕화면 바로가기 생성 (Python — Windows 한글 경로 안전).

사용:
  py make_desktop_shortcut.py [URL]
  기본 URL: http://localhost:5050
"""
import os
import sys
import subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5050"

# Chrome / Edge 자동 탐색
candidates = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]
browser = next((p for p in candidates if os.path.exists(p)), None)
if not browser:
    print("[오류] Chrome 또는 Edge 를 찾을 수 없습니다.")
    sys.exit(1)

# 데스크톱 실제 경로 자동 탐지 (OneDrive 리디렉션 대응)
def find_desktop():
    # 1. PowerShell의 정식 GetFolderPath
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "[Environment]::GetFolderPath('Desktop')"],
            capture_output=True, text=True, encoding="utf-8", timeout=10
        )
        p = (r.stdout or "").strip()
        if p and os.path.isdir(p):
            return Path(p)
    except Exception:
        pass
    # 2. 흔한 후보들
    home = Path(os.path.expanduser("~"))
    for cand in [
        home / "OneDrive" / "Desktop",
        home / "OneDrive" / "바탕 화면",
        home / "OneDrive - KNK" / "Desktop",
        home / "Desktop",
        home / "바탕 화면",
    ]:
        if cand.is_dir():
            return cand
    return home  # 최후의 폴백

desktop = find_desktop()
print(f"[INFO] 데스크톱 경로: {desktop}")
shortcut_path = desktop / "KNK 메신저.lnk"

ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut('{shortcut_path}')
$sc.TargetPath = '{browser}'
$sc.Arguments = '--app={url} --window-size=1200,800'
$sc.IconLocation = '{browser}, 0'
$sc.WorkingDirectory = '{os.path.expanduser("~")}'
$sc.Description = 'KNK 사내 메신저'
$sc.Save()
"""

result = subprocess.run(
    ["powershell", "-NoProfile", "-Command", ps_script],
    capture_output=True, text=True, encoding="utf-8"
)

if result.returncode != 0:
    print(f"[오류] 단축아이콘 생성 실패: {result.stderr}")
    sys.exit(1)

print(f"[OK] 브라우저:        {browser}")
print(f"[OK] 접속 URL:        {url}")
print(f"[OK] 바탕화면 아이콘: {shortcut_path}")
print()
print("바탕화면에 'KNK 메신저' 아이콘 생성 완료.")
print("더블클릭하면 별도 창으로 실행됩니다 (브라우저 탭·주소창 없는 깔끔 모드).")
