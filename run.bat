@echo off
rem ===================================================================
rem  fenologiya muhitida skript ishga tushirish (conda activate shart emas).
rem  PowerShell / VS Code terminalida:
rem    .\run.bat scripts\01_geom_tayyorlash.py --tuman "Jomboy tumani"
rem  Muhit boshqa joyda bo'lsa, quyidagi ENV qatorini o'zgartiring.
rem ===================================================================
set "ENV=%LOCALAPPDATA%\miniconda3\envs\fenologiya"
if not exist "%ENV%\python.exe" (
  echo fenologiya muhiti topilmadi: %ENV%
  echo Yaratish: conda env create -f env\environment.yml
  exit /b 1
)
"%ENV%\python.exe" %*
