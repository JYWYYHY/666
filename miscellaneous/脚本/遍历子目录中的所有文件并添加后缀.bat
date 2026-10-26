@echo off
for /r %%i in (*.*) do ren "%%i" "%%~ni.zip"
pause