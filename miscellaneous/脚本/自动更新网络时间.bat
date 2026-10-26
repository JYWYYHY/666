@echo off
echo 停止time服务........
net stop w32time >nul
echo 启动time 服务.........
regsvr32 /s w32time.dll
regsvr32 /s w32time.dll
net start w32time>nul
echo 配置时间服务器
w32tm /config /manualpeerlist:"time.windows.com" /syncfromflags:manual /reliable:yes /update

echo 同步时间
w32tm /resync /force

echo 当前系统时间
echo %date% %time%
echo 同步完成
echo.
pause