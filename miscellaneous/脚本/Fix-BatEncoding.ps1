<#
.SYNOPSIS
    批量修正 BAT/CMD 文件的编码与换行符，适配 Windows cmd.exe。
.DESCRIPTION
    - 统一换行符为 CRLF。
    - 含中文的文件转为 GBK(936) 编码，并确保开头有 chcp 936 >nul。
    - 移除已有的 chcp 65001（GBK 下会乱码）。
    - 纯 ASCII 文件写回 UTF-8 无 BOM（仅规范化换行）。
    - 写前自动备份 .bak，不覆盖已存在的 .bak。
#>

param(
    [string]$TargetDir = $PSScriptRoot,
    [string]$ExcludeFile = "",
    [switch]$Recurse
)

$ErrorActionPreference = "Stop"
$Utf8NoBom  = New-Object System.Text.UTF8Encoding($false)
$StrictUtf8 = New-Object System.Text.UTF8Encoding($false, $true)
$Gbk        = [System.Text.Encoding]::GetEncoding(936)

try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

if (-not $TargetDir) { $TargetDir = "." }

if (-not (Test-Path -LiteralPath $TargetDir -PathType Container)) {
    Write-Host "[错误] 目录不存在: $TargetDir" -ForegroundColor Red
    exit 1
}

if ($Recurse) {
    $Files = Get-ChildItem -Path $TargetDir -File -Recurse |
             Where-Object { $_.Extension -in '.bat','.cmd' }
} else {
    $Files = Get-ChildItem -Path $TargetDir -File |
             Where-Object { $_.Extension -in '.bat','.cmd' }
}

if ($ExcludeFile) {
    $Files = $Files | Where-Object { $_.Name -ne $ExcludeFile }
}

if (-not $Files -or @($Files).Count -eq 0) {
    Write-Host "未找到需要处理的 .bat/.cmd 文件。" -ForegroundColor Yellow
    exit 0
}

$total = @($Files).Count
$ok = 0
$fail = 0

foreach ($file in $Files) {
    Write-Host ""
    Write-Host "处理: $($file.Name)" -ForegroundColor Cyan

    try {
        # 1. 读取：严格 UTF-8 优先，失败回退 GBK
        $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
        try {
            $content   = $StrictUtf8.GetString($bytes)
            $sourceEnc = "UTF-8"
        } catch {
            $content   = $Gbk.GetString($bytes)
            $sourceEnc = "GBK"
        }

        # 2. 统一 CRLF
        $content = $content -replace "`r?`n", "`r`n"

        # 3. 判断是否含中文
        $hasChinese = $content -match '[\u4e00-\u9fff]'

        if ($hasChinese) {
            # 移除 chcp 65001 行（GBK 下会乱码）
            $has65001 = $content -match '(?im)^\s*chcp\s+65001'
            if ($has65001) {
                $lines = $content -split "`r`n" |
                         Where-Object { $_.Trim() -notmatch '^chcp\s+65001' }
                $content = ($lines -join "`r`n")
                Write-Host "  已移除 chcp 65001" -ForegroundColor Yellow
            }

            # 确保有 chcp 936 >nul（防止系统代码页被改成 65001）
            $has936 = $content -match '(?im)^\s*chcp\s+936'
            if (-not $has936) {
                $lines    = $content -split "`r`n"
                $inserted = $false
                $newLines = New-Object System.Collections.Generic.List[string]
                foreach ($line in $lines) {
                    $newLines.Add($line)
                    if (-not $inserted -and $line.Trim() -imatch '^@?echo\s+off') {
                        $newLines.Add("chcp 936 >nul")
                        $inserted = $true
                    }
                }
                if (-not $inserted) { $newLines.Insert(0, "chcp 936 >nul") }
                $content = ($newLines -join "`r`n")
                Write-Host "  已插入 chcp 936 >nul" -ForegroundColor Green
            }

            $outEnc  = $Gbk
            $encName = "GBK(936)"
        } else {
            # 纯 ASCII，UTF-8 无 BOM
            $outEnc  = $Utf8NoBom
            $encName = "UTF-8(ASCII)"
        }

        # 4. 备份（不覆盖已有 .bak）
        $bak = $file.FullName + ".bak"
        if (-not (Test-Path -LiteralPath $bak)) {
            Copy-Item -LiteralPath $file.FullName -Destination $bak -Force
        }

        # 5. 写回
        [System.IO.File]::WriteAllText($file.FullName, $content, $outEnc)

        Write-Host "  完成（源编码: $sourceEnc，输出编码: $encName，已备份 .bak）" -ForegroundColor Green
        $ok++
    }
    catch {
        Write-Host "  失败: $($_.Exception.Message)" -ForegroundColor Red
        $fail++
    }
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "处理完成：成功 $ok 个，失败 $fail 个，共 $total 个。" -ForegroundColor Cyan