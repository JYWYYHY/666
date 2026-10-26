@echo off
chcp 65001 >nul

set "script=%~nx0"

(for /f "delims=" %%i in ('dir /b /a-d') do (
    if not "%%i"=="%script%" (
        if not "%%i"=="Thumbs.db" (
            if not "%%i"=="Desktop.ini" (
                echo %%i
            )
        )
    )
)) > file_list.txt

echo 文件列表已生成到 file_list.txt

del /q "%~f0"