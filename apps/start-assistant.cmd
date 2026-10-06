@echo off
chcp 65001 >nul
rem 성우 김디도 AI 비서 시작: 이 파일을 두 번 누르면 비서가 앱 창으로 열려요. 이 검은 창을 닫으면 비서도 꺼져요.
rem 다른 번호로 켜려면: start-assistant.cmd 8771
title 성우 김디도 AI 비서 (이 창을 닫으면 비서가 꺼져요)
cd /d "%~dp0dido-assistant"
set PORT=8770
if not "%~1"=="" set PORT=%~1
set URL=http://127.0.0.1:%PORT%/
set PY=
python -c "import sys" >nul 2>nul
if not errorlevel 1 set PY=python
if not defined PY py -3 -c "import sys" >nul 2>nul
if not defined PY if not errorlevel 1 set PY=py -3
if not defined PY goto nopython
rem 이 포트를 누가 쓰는지 확인: 0=비어 있음, 10=이미 켜진 우리 비서, 11=다른 프로그램
powershell -NoProfile -Command "try { $r = Invoke-RestMethod -TimeoutSec 2 %URL%api/status; if ($r.service -eq 'dido-assistant') { exit 10 } else { exit 11 } } catch { if (Get-NetTCPConnection -State Listen -LocalPort %PORT% -ErrorAction SilentlyContinue) { exit 11 } else { exit 0 } }"
if errorlevel 11 goto portbusy
if errorlevel 10 goto already
%PY% -c "import anthropic" >nul 2>nul
if errorlevel 1 echo [알림] AI 연결 부품이 없어 오프라인 모드로 켜요. 연결하려면 README의 "AI 연결 켜기"를 보세요.
rem 우리 비서가 응답할 때만 화면을 열어요(다른 서비스가 대신 열리지 않게 service 값을 확인)
start "" /b powershell -NoProfile -Command "for ($i=0; $i -lt 40; $i++) { try { $r = Invoke-RestMethod -TimeoutSec 1 %URL%api/status; if ($r.service -eq 'dido-assistant') { try { Start-Process msedge '--app=%URL%' } catch { Start-Process '%URL%' }; exit 0 } } catch { }; Start-Sleep -Milliseconds 500 }; exit 1"
%PY% server.py --port %PORT%
if errorlevel 1 (
  echo [비서 멈춤] 비서가 켜지지 않았거나 멈췄어요. 위의 메시지를 알려 주세요.
  pause
)
exit /b
:nopython
echo [Python 없음] PowerShell에 아래 한 줄을 붙여 넣고 Enter. Y를 물으면 Y. 설치가 끝나면 이 창을 닫고 start-assistant.cmd를 다시 두 번 누르세요.
echo winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
pause
exit /b 1
:portbusy
echo [포트 사용 중] %PORT%번 자리를 다른 프로그램이 쓰고 있어요. PowerShell에 아래 한 줄을 붙여 넣으면 어떤 프로그램인지 보여요.
echo Get-NetTCPConnection -LocalPort %PORT% -State Listen ^| ForEach-Object { Get-Process -Id $_.OwningProcess } ^| Select-Object Id,ProcessName
echo 그 프로그램을 끌 수 없으면 다른 번호로 켜요. 이 파일 이름 뒤에 번호를 붙이면 돼요(예: start-assistant.cmd 8771).
pause
exit /b 1
:already
echo [이미 켜져 있어요] 비서가 이미 %URL% 에서 돌고 있어요. 앱 창을 다시 열어요.
powershell -NoProfile -Command "try { Start-Process msedge '--app=%URL%' } catch { Start-Process '%URL%' }"
exit /b
