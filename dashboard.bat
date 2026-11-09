@echo off
rem ===================================================================
rem  Interaktiv dashboard (scripts\dashboard.py) -> http://localhost:8501
rem  Alohida "fenologiya_viz" muhiti (pipeline muhitiga tegmaydi). Yaratish:
rem    conda env create -f env\environment_viz.yml
rem  Qo'shimcha parametrlar streamlit'ga uzatiladi, masalan:
rem    .\dashboard.bat --server.port 8502
rem ===================================================================
set "ENV=%LOCALAPPDATA%\miniconda3\envs\fenologiya_viz"
if not exist "%ENV%\python.exe" (
  echo fenologiya_viz muhiti topilmadi: %ENV%
  echo Yaratish: conda env create -f env\environment_viz.yml
  exit /b 1
)
cd /d "%~dp0"
"%ENV%\python.exe" -m streamlit run scripts\dashboard.py %*
