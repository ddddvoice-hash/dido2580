@echo off
chcp 65001 >nul
rem 성우 김디도 AI 비서 시작: 이 파일을 두 번 누르면 비서가 앱 창으로 열려요. 이 검은 창을 닫으면 비서도 꺼져요.
title 성우 김디도 AI 비서 (이 창을 닫으면 비서가 꺼져요)
cd /d "%~dp0dido-assistant"
set URL=http://127.0.0.1:8770/
set PY=
python -c "import sys" >nul 2>nul && set PY=python
if not defined PY (py -3 -c "import sys" >nul 2>nul && set PY=py -3)
if not defined PY (
  echo [Python 없음] PowerShell에 아래 한 줄을 붙여 넣고 Enter. Y를 물으면 Y.
  echo winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
  pause
  exit /b 1
)
%PY% -c "import anthropic" >nul 2>nul || echo [알림] AI 연결 부품이 없어 오프라인 모드로 켜요. 연결하려면 README의 "AI 연결 켜기"를 보세요.
start "" /b powershell -NoProfile -Command "for ($i=0; $i -lt 40; $i++) { try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 %URL%api/status; if ($r.Content -notmatch 'seongwoo-kimdido-assistant') { throw 'other' }; try { Start-Process msedge '--app=%URL%' } catch { Start-Process '%URL%' }; exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"
%PY% server.py --port 8770
if errorlevel 1 (
  echo [비서 멈춤] 비서가 켜지지 않았거나 멈췄어요. 위의 메시지를 알려 주세요.
  pause
)
