@echo off
title 去除快捷方式小箭头（修改29号图标为透明图标）
setlocal

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 请右键以管理员身份运行本脚本。
    pause
    exit /b
)

echo ===================================================
echo 正在去除快捷方式小箭头...
echo ===================================================

:: 1. 修改注册表，将 29 号图标指向透明图标
:: 注：imageres.dll,197 在部分系统中是透明图标，以此达到去箭头的目的。
echo [1/3] 正在修改注册表...
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons" /v 29 /d "%systemroot%\system32\imageres.dll,197" /t REG_SZ /f

if %errorlevel% neq 0 (
    echo 注册表修改失败，请检查权限。
    pause
    exit /b
)

:: 2. 彻底清理图标缓存（关键步骤，防止不生效）
echo [2/3] 正在清理图标缓存（屏幕会闪烁或任务栏消失，属正常现象）...
taskkill /f /im explorer.exe >nul 2>&1
del /f /q /a "%userprofile%\AppData\Local\iconcache.db" >nul 2>&1
del /f /q /a "%userprofile%\AppData\Local\Microsoft\Windows\Explorer\thumbcache_*.db" >nul 2>&1
ie4uinit.exe -show >nul 2>&1

:: 3. 重启资源管理器
echo [3/3] 正在重启资源管理器...
start explorer.exe

echo ===================================================
echo 操作完成！小箭头应该已经消失。
echo 如果仍未生效，请重启电脑。
echo ===================================================
pause
endlocal