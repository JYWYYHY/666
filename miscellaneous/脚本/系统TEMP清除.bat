@echo off
echo ………………………………开始清除临时文件TEMP……………………………… .>>D:\tmp.txt
cd %temp%
del  /f/s/q %temp%\*  .>>D:\tmp.txt
del  /f/s/q %temp%\*.tmp  .>>D:\tmp.txt
del  /f/s/q %temp%\*.zip  .>>D:\tmp.txt
del  /f/s/q %temp%\*.pptx  .>>D:\tmp.txt
del  /f/s/q %temp%\*.ppt  .>>D:\tmp.txt
del  /f/s/q %temp%\*.tmp  .>>D:\tmp.txt
del  /f/s/q %temp%\*.tmp.node  .>>D:\tmp.txt
cd %temp%
rd /s/q .>>D:\tmp1.txt
echo ………………………………开始清除windows临时文件TEMP……………………………… .>>D:\tmp.txt
cd %windir%/temp
rd /s/q .>>D:\tmp2.txt
echo ………………………………清除完毕…………………………………… .>>D:\tmp.txt
echo ………………………………清除完毕……………………………………
echo ………………………………清除完毕……………………………………
timeout /T 3
exit