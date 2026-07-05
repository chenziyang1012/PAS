@echo off
chcp 65001 >nul
cd /d "%~dp0frontend"
if not exist node_modules (
    npm install
)
cmd /k npm run dev
