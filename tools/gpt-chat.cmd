@echo off
chcp 65001 >nul
rem 성우 김디도 팀: GPT 아스트라를 대표가 보는 대화창으로 열어요. 시작 안내는 tools\gpt-start.md
title GPT 아스트라 대화창 - 성우 김디도
cd /d "%~dp0.."
if errorlevel 1 goto nofolder
where codex >nul 2>nul
if errorlevel 1 goto nocodex
git pull --no-rebase
powershell -NoProfile -ExecutionPolicy Bypass -Command "codex -m gpt-6-astra -c model_reasoning_effort=high -s workspace-write (Get-Content -Raw -Encoding UTF8 'tools\gpt-start.md')"
echo.
echo GPT 대화창이 닫혔어요. 이 창은 아무 키나 누르면 닫혀요.
pause >nul
exit /b 0

:nofolder
echo [폴더 없음] 저장소 폴더를 찾지 못했어요.
pause
exit /b 1

:nocodex
echo [codex 없음] GPT 실행 프로그램 codex를 찾지 못했어요. PowerShell에 아래 한 줄을 붙여 넣고 Enter. 끝나면 이 파일을 다시 실행하세요.
echo npm install -g @openai/codex
pause
exit /b 1
