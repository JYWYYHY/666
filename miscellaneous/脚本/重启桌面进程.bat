@echo off
echo ………………………………重启桌面进程………………………………
taskkill /f /im explorer.exe

explorer.exe
echo ………………………………重启成功………………………………
exit