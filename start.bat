@echo off
cd /d "%~dp0"
"C:\Users\Andhias\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8005
