@echo off
setlocal
set "EXE=%~dp0ConciliaAI.exe"
if not exist "%EXE%" (
 set "EXE="
 for /f "usebackq delims=" %%I in (`powershell -NoProfile -STA -Command "Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.OpenFileDialog; $d.Filter='Executavel (*.exe)|*.exe'; if($d.ShowDialog() -eq 'OK'){$d.FileName}"`) do set "EXE=%%I"
)
if not defined EXE exit /b
for %%I in ("%EXE%") do cd /d "%%~dpI"
if not exist temp mkdir temp
if not exist logs mkdir logs
set "TEMP=%CD%\temp"
set "TMP=%TEMP%"
"%EXE%" > logs\inicializacao.log 2>&1
if errorlevel 1 (
 type logs\inicializacao.log
 pause
)
