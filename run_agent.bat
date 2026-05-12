@echo off
title SOC Deadman Switch - Detection Agent
color 0A

echo =============================================
echo  Visual SOC Deadman Switch - Agent Starting
echo =============================================
echo.

call venv\Scripts\activate.bat

rem  EDIT THE LINE BELOW - paste your deployed Replit URL
set API_URL=https://visual-soc-sentinel--prajavsb.replit.app

echo Connecting to: %API_URL%
echo Camera index : 0  (change --camera 1 if built-in does not work)
echo Press Q in the video window to stop.
echo.

python detection_agent.py --api-url %API_URL% --camera 0

echo.
echo Agent stopped.
pause