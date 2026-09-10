@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python nao foi encontrado. Instale o Python 3.10 ou superior e marque "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Preparando o FaeHub pela primeira vez...
  py -3 -m venv .venv
  if errorlevel 1 goto :failure
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
  if errorlevel 1 goto :failure
)

echo.
echo FaeHub pronto em http://127.0.0.1:5000
echo Mantenha esta janela aberta durante a apresentacao.
start "" "http://127.0.0.1:5000"
".venv\Scripts\python.exe" app.py
exit /b %errorlevel%

:failure
echo.
echo Nao foi possivel preparar o ambiente. Confira sua conexao e a instalacao do Python.
pause
exit /b 1
