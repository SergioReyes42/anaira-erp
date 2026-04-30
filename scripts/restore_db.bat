@echo off
setlocal

REM Restaurar base de datos Django desde fixture JSON
REM Uso: scripts\restore_db.bat backups\db_backup_YYYYMMDD_HHMMSS.json

if "%~1"=="" (
  echo Uso: scripts\restore_db.bat ^<ruta_fixture.json^>
  exit /b 1
)

set FIXTURE=%~1

if not exist "%FIXTURE%" (
  echo [ERROR] No existe el archivo: %FIXTURE%
  exit /b 1
)

python manage.py loaddata "%FIXTURE%"

if errorlevel 1 (
  echo [ERROR] No se pudo restaurar la base de datos.
  exit /b 1
)

echo [OK] Restauración completada desde: %FIXTURE%
exit /b 0
