@echo off
reg export "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" backup.reg
set /p "title=请输入标题文本>>>"
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /d %title% /v LegalNoticeCaption /f
set /p "content=请输入内容>>>"
reg add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /d %content% /v LegalNoticeText /f
echo 设置完成！
pause