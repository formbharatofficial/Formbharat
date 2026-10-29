@echo off
title FormBharat phone
cd /d "%~dp0"
net session >nul 2>&1
if errorlevel 1 (
    echo.
    echo Phone par app kholne ke liye Windows ka Yes dabao.
    echo.
    powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)
netsh advfirewall firewall delete rule name="FormBharat phone check" >nul 2>&1
netsh advfirewall firewall add rule name="FormBharat phone check" dir=in action=allow protocol=TCP localport=5002 remoteip=localsubnet profile=any
echo.
echo Phone ke Chrome me ye likho:
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /c:"IPv4"') do echo   http://%%A:5002/
echo.
echo Phir Chrome ke teen bindu se Home screen par jod do.
echo Band karne ke liye is window ko band karo.
echo.
netstat -ano | findstr /C:":5002" | findstr LISTENING >nul
if errorlevel 1 goto startserver
echo App pehle se chal rahi hai. Upar wala pata phone me kholo.
pause
exit /b
:startserver
cd /d "%~dp0src"
set FORMBHARAT_ENV=production
set HOST=0.0.0.0
set PORT=5002
set FORMBHARAT_DATABASE_PATH=%~dp0formbharat.db
set FORMBHARAT_STORAGE_DIR=%~dp0documents
py -3 main.py
pause
