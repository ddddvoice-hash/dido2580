@echo off
chcp 65001 >nul
rem 디도 보이스 작업실 시작: 이 파일을 두 번 누르면 작업실 첫 화면이 브라우저에 열립니다.
rem 이 컴퓨터 안에서만 도는 작은 서버(127.0.0.1)를 켭니다. 녹음 파일은 밖으로 나가지 않습니다.
rem 창을 닫으면 서버도 꺼집니다.
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
start "" /b cmd /c "timeout /t 2 /nobreak >nul & start "" http://127.0.0.1:8765/index.html"
echo 잠시 뒤 작업실이 브라우저에 열립니다. 다 쓰면 이 창을 닫으세요.
%PY% -m http.server 8765 --bind 127.0.0.1
if errorlevel 1 (echo 서버를 켜지 못했습니다. 이미 켜져 있거나 Python이 없습니다. & pause)
