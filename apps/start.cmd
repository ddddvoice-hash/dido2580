@echo off
chcp 65001 >nul
rem 성우 김디도 보이스 작업실 시작: 이 파일(또는 바탕화면 아이콘)을 두 번 누르면 작업실이 앱 창으로 열려요.
rem 이 컴퓨터 안에서만 도는 작은 서버(127.0.0.1)를 켜요. 녹음 파일은 밖으로 나가지 않아요.
rem 이 검은 창을 닫으면 서버도 꺼져요.
rem 순서: 1) Python이 실제로 되는지 확인 2) 포트가 비어 있는지 확인 3) 서버가 응답한 뒤에 화면 열기
title 성우 김디도 보이스 작업실 (이 창을 닫으면 작업실이 꺼져요)
cd /d "%~dp0"
set PORT=8765
set URL=http://127.0.0.1:%PORT%/index.html

rem 1) Python 찾기. 윈도우에 깔린 가짜 python 바로가기도 걸러 내려고 실제로 한 번 실행해 봐요.
set PY=
python -c "import sys" >nul 2>nul && set PY=python
if not defined PY (py -3 -c "import sys" >nul 2>nul && set PY=py -3)
if not defined PY (
  echo.
  echo [Python 없음] 작업실을 켤 Python을 찾지 못했어요.
  echo PowerShell에 아래 한 줄을 붙여 넣고 Enter를 누르세요. 중간에 Y 입력을 물으면 Y를 누르세요.
  echo winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
  echo 설치가 끝나면 이 파일을 다시 두 번 누르세요.
  echo.
  pause
  exit /b 1
)

rem 2) 포트 확인. 이미 쓰이고 있으면 우리 작업실인지 확인해요.
set BUSY=
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul && set BUSY=1
if defined BUSY (
  powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 %URL%; if ($r.Content -match 'warmth-scorer') { exit 0 } else { exit 1 } } catch { exit 1 }"
  if not errorlevel 1 (
    echo [이미 켜져 있음] 작업실이 이미 켜져 있어요. 화면만 다시 열어요.
    powershell -NoProfile -Command "try { Start-Process msedge '--app=%URL%' } catch { Start-Process '%URL%' }"
    exit /b 0
  )
  echo.
  echo [포트 사용 중] %PORT%번 포트를 다른 프로그램이 쓰고 있어요. 작업실이 아니에요.
  echo 그 프로그램을 닫거나 컴퓨터를 다시 시작한 뒤 이 파일을 다시 두 번 누르세요.
  echo.
  pause
  exit /b 1
)

rem 3) 서버가 응답할 때까지 기다렸다가 화면을 열어요(최대 20초). 엣지 앱 창으로 열고, 엣지가 없으면 기본 브라우저로 열어요.
start "" /b powershell -NoProfile -Command "for ($i=0; $i -lt 40; $i++) { try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 %URL% | Out-Null; try { Start-Process msedge '--app=%URL%' } catch { Start-Process '%URL%' }; exit 0 } catch { Start-Sleep -Milliseconds 500 } }; exit 1"
echo 서버가 켜지면 작업실 창이 열려요. 다 쓰면 이 창을 닫으세요.
%PY% -m http.server %PORT% --bind 127.0.0.1
if errorlevel 1 (
  echo.
  echo [서버 멈춤] 서버가 켜지지 않았거나 멈췄어요. 위의 영어 메시지를 알려 주세요.
  pause
)
