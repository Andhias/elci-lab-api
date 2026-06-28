@echo off
setlocal

echo ======================================
echo Elevator AI API - Database Setup
echo ======================================

REM Check Python
python --version 2>nul || (echo ERROR: Python not found & exit /b 1)

REM Install dependencies
echo.
echo [1/4] Installing Python dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (echo ERROR: pip install failed & exit /b 1)

REM Setup database
echo.
echo [2/4] Running Alembic migrations...
cd /d "%~dp0"
python -m alembic upgrade head
if errorlevel 1 (echo ERROR: alembic upgrade failed & exit /b 1)

echo.
echo ======================================
echo Setup complete!
echo.
echo Next steps:
echo   1. Configure .env with your settings
echo   2. Start the server:
echo      python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
echo.
echo For PostgreSQL:
echo   1. Install PostgreSQL 17
echo   2. Create database: createdb elevator_ai
echo   3. Update DATABASE_URL in .env
echo   4. Re-run: python -m alembic upgrade head
echo ======================================

endlocal
