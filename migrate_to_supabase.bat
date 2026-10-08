@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python nao foi encontrado. Instale o Python 3.10 ou superior.
  pause
  exit /b 1
)

if not exist ".env" (
  echo Crie o arquivo .env a partir de .env.example e preencha FAEHUB_DATABASE_URL.
  echo Copie a connection string Session pooler em Connect no painel do Supabase.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Preparando ambiente isolado...
  py -3 -m venv .venv || goto :failure
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto :failure
)

echo.
echo Conferindo origem local sem alterar o Supabase...
".venv\Scripts\python.exe" scripts\migrate_sqlite_to_supabase.py || goto :failure
echo.
set /p confirm="Digite MIGRAR para enviar os dados ao Supabase: "
if /I not "%confirm%"=="MIGRAR" (
  echo Operacao cancelada. Nenhum dado foi alterado.
  exit /b 0
)

echo.
echo Migrando em uma unica transacao...
".venv\Scripts\python.exe" scripts\migrate_sqlite_to_supabase.py --apply || goto :failure
".venv\Scripts\python.exe" scripts\check_database.py || goto :failure
echo.
echo Migracao concluida e validada. O aplicativo agora usa apenas Supabase.
pause
exit /b 0

:failure
echo.
echo A migracao falhou e a transacao foi revertida. Revise a mensagem acima.
pause
exit /b 1
