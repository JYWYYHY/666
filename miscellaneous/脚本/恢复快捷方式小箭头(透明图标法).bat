@echo off
title 恢复快捷方式小箭头（彻底删除29键值并重建缓存）
setlocal

:: 检查管理员权限
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo 请右键以管理员身份运行本脚本。
    pause
    exit /b
)

echo ===================================================
echo 正在恢复快捷方式小箭头...
echo ===================================================

:: 1. 删除 Shell Icons 下的 29 键值
:: 注：29号键值就是控制快捷方式小箭头的，删除它即可恢复默认小箭头。
echo [1/4] 正在删除 Shell Icons 下的 29 键值...
reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Icons" /v 29 /f >nul 2>&1

:: 2. 检查并修复 IsShortcut 键值（这是Windows判断快捷方式的灵魂）
echo [2/4] 正在检查并修复 lnkfile 下的 IsShortcut 键值...
reg query "HKEY_CLASSES_ROOT\lnkfile" /v IsShortcut >nul 2>&1
if %errorlevel% neq 0 (
    echo 未找到 IsShortcut，正在新建...
    reg add "HKEY_CLASSES_ROOT\lnkfile" /v IsShortcut /t REG_SZ /d "" /f >nul 2>&1
) else (
    echo 确保 IsShortcut 数值数据为空...
    reg add "HKEY_CLASSES_ROOT\lnkfile" /v IsShortcut /t REG_SZ /d "" /f >nul 2>&1
)

:: 3. 彻底清理图标缓存（这是恢复生效的关键）
echo [3/4] 正在清理图标缓存（屏幕会闪烁或任务栏消失，属正常现象）...
taskkill /f /im explorer.exe >nul 2>&1
:: 清理主流系统的图标缓存
del /f /q /a "%userprofile%\AppData\Local\iconcache.db" >nul 2>&1
del /f /q /a "%userprofile%\AppData\Local\Microsoft\Windows\Explorer\thumbcache_*.db" >nul 2>&1
:: 调用系统命令强制刷新图标
ie4uinit.exe -show >nul 2>&1

:: 4. 重启资源管理器
echo [4/4] 正在重启资源管理器...
start explorer.exe

echo ===================================================
echo 操作完成！请查看桌面快捷方式。
echo 如果仍未生效，请重启电脑。
echo ===================================================
pause
endlocal