@echo off
chcp 65001 >nul
cd /d "%~dp0"
start pythonw article_fetcher_gui.py
