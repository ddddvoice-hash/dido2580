@echo off
chcp 65001 >nul
rem 디도 보이스 작업실 시작: 이 파일(또는 바탕화면 아이콘)을 두 번 누르면 작업실이 앱 창으로 열립니다.
rem 이 컴퓨터 안에서만 도는 작은 서버(127.0.0.1)를 켭니다. 녹음 파일은 밖으로 나가지 않습니다.
rem 이 검은 창을 닫으면 서버도 꺼집니다.
title 디도 보이스 작업실 (이 창을 닫으면 작업실이 꺼집니다)
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
rem 엣지 앱 창(주소창 없는 창)으로 엽니다. 엣지가 없으면 기본 브라우저로 엽니다.
start "" /b cmd /c "timeout /t 2 /nobreak >nul & (start "" msedge --app=http://127.0.0.1:8765/index.html || start "" http://127.0.0.1:8765/index.html)"
echo 잠시 뒤 작업실 창이 열립니다. 다 쓰면 이 창을 닫으세요.
%PY% -m http.server 8765 --bind 127.0.0.1
if errorlevel 1 (echo 서버를 켜지 못했습니다. 이미 켜져 있거나 Python이 없습니다. & pause)
