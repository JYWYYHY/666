@echo off
cd /d "%~dp0"
for %%f in (*.txt) do if not exist "%%~nf.lrc" ren "%%f" "%%~nf.lrc"
echo Done.
pause