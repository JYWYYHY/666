@echo off
chcp 936 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

set N=0
for /f "delims=" %%f in ('dir /b /a-d *.bmk *.lib *.pl 2^>nul') do (
    echo   %%f
    set /a N+=1
)
if %N%==0 ( echo 当前目录没有匹配的文件。& pause & exit /b )
choice /c YN /n /m "确认删除以上 %N% 个文件？[Y/N] "
if errorlevel 2 ( echo 已取消。& pause & exit /b )

rem 关键：先去掉只读/隐藏/系统属性，再强制删除
attrib -r -h -s *.bmk *.lib *.pl >nul 2>&1
del /q /f /a *.bmk *.lib *.pl

rem 复核：用同样的 dir 枚举，看还剩几个
set LEFT=0
for /f "delims=" %%f in ('dir /b /a-d *.bmk *.lib *.pl 2^>nul') do set /a LEFT+=1
if !LEFT! GTR 0 (
    echo 警告：仍有 !LEFT! 个文件未删除：
    dir /a *.bmk *.lib *.pl
) else (
    echo 已删除。
)
pause