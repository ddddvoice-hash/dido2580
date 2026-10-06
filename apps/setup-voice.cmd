@echo off
chcp 65001 >nul
rem 성우 김디도 음성 비서 한 번에 준비: 두 번 누르면 필요한 부품을 깔고, 목소리 폴더를 확인하고, Claude·GPT·Gemini 앱에 연결해요.
title 성우 김디도 음성 비서 준비
cd /d "%~dp0dido-assistant"
set PY=
python -c "import sys" >nul 2>nul && set PY=python
if not defined PY (py -3 -c "import sys" >nul 2>nul && set PY=py -3)
if not defined PY (
  echo [Python 없음] PowerShell에 아래 한 줄을 붙여 넣고 Enter. Y를 물으면 Y.
  echo winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
  pause
  exit /b 1
)
echo [1/4] 부품 설치. 처음에는 수 GB를 내려받아 오래 걸려요. 창을 닫지 마세요.
%PY% -m pip install --upgrade mcp anthropic qwen-tts soundfile
if errorlevel 1 (
  echo [설치 실패] 위의 메시지를 알려 주세요.
  pause
  exit /b 1
)
echo [2/4] 목소리 폴더 확인
if not exist "voice\ref.txt" copy /y "voice\ref_sentence.txt" "voice\ref.txt" >nul
if not exist "voice\ref.wav" (
  echo.
  echo [목소리 녹음이 아직 없어요] voice\ref_sentence.txt 의 문장을 평소처럼 읽어 WAV로 녹음하고
  echo   "%~dp0dido-assistant\voice\ref.wav" 이름으로 넣은 뒤 이 파일을 다시 두 번 누르세요.
  echo   녹음 부스나 낭독 코치로 녹음해도 돼요. 10~15초, 잡음 없이.
  echo.
  start "" "%~dp0dido-assistant\voice"
)
echo [3/4] Claude·GPT·Gemini 앱에 연결
%PY% connect.py
echo [4/4] 상태
%PY% -c "import sys; sys.path.insert(0,'.'); from tts import make_engine, voice_ready; e=make_engine(); print('목소리:', e.label); print('목소리 폴더:', voice_ready()[1])"
echo.
echo 끝났어요. 비서 화면은 start-assistant.cmd, AI 앱에서는 "김디도 목소리로 읽어 줘"라고 하면 돼요.
pause
