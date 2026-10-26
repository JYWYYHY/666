@echo off
chcp 936 >nul
title 去除快捷方式小箭头 - IsShortcut 方法

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 请右键以管理员身份运行本脚本。
    pause
    exit /b
)

echo 正在删除 lnkfile 下的 IsShortcut...
reg delete "HKCR\lnkfile" /v IsShortcut /f >nul 2>&1

echo 正在删除 piffile 下的 IsShortcut...
reg delete "HKCR\piffile" /v IsShortcut /f >nul 2>&1

echo 正在重启资源管理器...
taskkill /f /im explorer.exe >nul 2>&1
start explorer.exe

echo 完成。若小箭头仍未消失，请重启电脑。
pause