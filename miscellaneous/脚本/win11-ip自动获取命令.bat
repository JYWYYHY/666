@echo off
echo    正在设置IP自动获取.........................
ipconfig /release
ipconfig /renew
echo    正在设置DNS自动获取....................
ipconfig /flushdns
echo 设置完成
pause