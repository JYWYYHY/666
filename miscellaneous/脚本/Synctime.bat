@echo off
echo 系统准备中...请勿关闭本窗口!
echo 系统准备中...请勿关闭本窗口!
echo 系统准备中...请勿关闭本窗口!


date 2025-08-03
time 07:10:00

TIMEOUT /T 5
net stop w32time

TIMEOUT /T 5
w32tm /config /syncfromflags:manual /manualpeerlist:"time.windows.com"

TIMEOUT /T 5
net start w32time

TIMEOUT /T 5
w32tm /config /update
w32tm /resync /rediscover