@echo off
setlocal EnableDelayedExpansion

:: ============================================================
:: EQUITY BOARD — AUTO INGEST + GITHUB PUSH
:: ============================================================
:: NOTE: quotes around set values handle & in folder names

set "REPO=E:\Quarks&Quants\Quants\0.1. Equity Board"
set "LOG=%REPO%\Automation\update_log.txt"
set "SUMMARY=%REPO%\Automation\last_run.txt"
set "PYTHON=python"

cd /d "%REPO%"

echo. >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo [%date% %time%] Starting equity data update >> "%LOG%"
echo ============================================================ >> "%LOG%"

echo [%date% %time%] Starting equity data update
echo.

:: ============================================================
:: STEP 1 — RUN INGEST
:: ============================================================

echo [%date% %time%] Running ingest...
echo [%date% %time%] Running ingest... >> "%LOG%"

"%PYTHON%" "%REPO%\Ingest\The Ingest.py" >> "%LOG%" 2>&1

if %errorlevel% neq 0 (
    echo [%date% %time%] ERROR: Ingest script failed. Check log.
    echo [%date% %time%] ERROR: Ingest script failed >> "%LOG%"
    goto end
)

echo [%date% %time%] Ingest complete.
echo [%date% %time%] Ingest complete >> "%LOG%"

:: ============================================================
:: STEP 2 — CHECK FOR CHANGES IN DATABASE FOLDER
:: ============================================================

set "HAS_CHANGES=0"

for /f "tokens=*" %%i in ('git status --porcelain -- Database/') do (
    set "HAS_CHANGES=1"
)

if "%HAS_CHANGES%"=="0" (
    echo [%date% %time%] No new data. Skipping push.
    echo [%date% %time%] No changes detected. Skipping push >> "%LOG%"
    goto end
)

:: ============================================================
:: STEP 3 — COMMIT AND PUSH
:: ============================================================

echo [%date% %time%] New data detected — pushing to GitHub...
echo [%date% %time%] New data detected — pushing to GitHub >> "%LOG%"

git add "Database/SENSEX30_2000_PRESENT.parquet" >> "%LOG%" 2>&1
git add "Database/SENSEX30_2000_PRESENT.csv"     >> "%LOG%" 2>&1

git commit -m "Auto-update: Equity data refresh %date%" >> "%LOG%" 2>&1

if %errorlevel% neq 0 (
    echo [%date% %time%] ERROR: Git commit failed. Check log.
    echo [%date% %time%] ERROR: Git commit failed >> "%LOG%"
    goto end
)

git push origin main >> "%LOG%" 2>&1

if %errorlevel% neq 0 (
    echo [%date% %time%] ERROR: Git push failed. Check log.
    echo [%date% %time%] ERROR: Git push failed >> "%LOG%"
    powershell -Command "(Get-Content '%SUMMARY%') -replace 'GIT PUSH       : PENDING', 'GIT PUSH       : FAILED' | Set-Content '%SUMMARY%'"
    goto end
)

echo [%date% %time%] Push complete.
echo [%date% %time%] Push complete >> "%LOG%"
powershell -Command "(Get-Content '%SUMMARY%') -replace 'GIT PUSH       : PENDING', 'GIT PUSH       : SUCCESS' | Set-Content '%SUMMARY%'"

:end
echo.
echo [%date% %time%] Done.
echo [%date% %time%] Done >> "%LOG%"

endlocal
