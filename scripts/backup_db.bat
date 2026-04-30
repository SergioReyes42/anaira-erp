@echo off
setlocal

REM Backup de base de datos Django (JSON fixture)
REM Uso: scripts\backup_db.bat
REM Requiere entorno Python activo donde funcione manage.py

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set TS=%%i

set OUTDIR=backups
set OUTFILE=%OUTDIR%\db_backup_%TS%.json

if not exist "%OUTDIR%" mkdir "%OUTDIR%"

python manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.Permission --indent 2 --output "%OUTFILE%"

if errorlevel 1 (
  echo [ERROR] No se pudo generar backup.
  exit /b 1
)

echo [OK] Backup generado: %OUTFILE%
exit /b 0
