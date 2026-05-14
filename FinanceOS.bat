@echo off
title FinanceOS
cd /d "%~dp0"
echo Starting FinanceOS...
start "" /B ".venv\Scripts\pythonw.exe" desktop_app.py
