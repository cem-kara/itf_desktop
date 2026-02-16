param(
    [string]$Root = ".",
    [int]$MaxFindings = 300
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$allowedExtensions = @(
    ".py", ".pyw", ".ps1", ".md", ".txt", ".json", ".qss", ".ini", ".yml", ".yaml"
)

$skipDirRegex = "(\\|/)(\.git|\.venv|venv|__pycache__|\.mypy_cache|\.pytest_cache|node_modules)(\\|/)"

$rules = @(
    @{ Name = "Mojibake-C3"; Token = [string][char]0x00C3 },
    @{ Name = "Mojibake-C4"; Token = [string][char]0x00C4 },
    @{ Name = "Mojibake-C5"; Token = [string][char]0x00C5 },
    @{ Name = "Mojibake-C2"; Token = [string][char]0x00C2 },
    @{ Name = "Mojibake-EmojiPrefix"; Token = ([string][char]0x011F + [char]0x0178) },
    @{ Name = "Replacement-FFFD"; Token = [string][char]0xFFFD }
)

$rootPath = (Resolve-Path $Root).Path

$files = Get-ChildItem -Path $Root -Recurse -File | Where-Object {
    $allowedExtensions -contains $_.Extension.ToLowerInvariant() -and
    $_.FullName -notmatch $skipDirRegex
}

$findings = New-Object System.Collections.Generic.List[object]

foreach ($file in $files) {
    $lines = [System.IO.File]::ReadAllLines($file.FullName, [System.Text.Encoding]::UTF8)
    for ($i = 0; $i -lt $lines.Length; $i++) {
        $line = $lines[$i]
        $matched = @()
        foreach ($rule in $rules) {
            if ($line.Contains($rule.Token)) {
                $matched += $rule.Name
            }
        }

        if ($matched.Count -gt 0) {
            $trimmed = $line.Trim()
            if ($trimmed.Length -gt 180) {
                $trimmed = $trimmed.Substring(0, 180) + "..."
            }

            $relative = $file.FullName
            if ($relative.StartsWith($rootPath, [System.StringComparison]::OrdinalIgnoreCase)) {
                $relative = $relative.Substring($rootPath.Length).TrimStart('\', '/')
            }
            $findings.Add([PSCustomObject]@{
                File = $relative
                Line = $i + 1
                Reason = ($matched -join "; ")
                Snippet = $trimmed
            })

            if ($findings.Count -ge $MaxFindings) {
                break
            }
        }
    }

    if ($findings.Count -ge $MaxFindings) {
        break
    }
}

if ($findings.Count -eq 0) {
    Write-Host "[OK] Encoding check passed. Mojibake pattern not found."
    exit 0
}

Write-Host "[ERROR] Encoding issues found: $($findings.Count)"
foreach ($f in $findings) {
    Write-Host (" - {0}:{1} | {2}" -f $f.File, $f.Line, $f.Reason)
    Write-Host ("   {0}" -f $f.Snippet)
}

Write-Host ""
Write-Host "Suggested action:"
Write-Host " - Review listed lines."
Write-Host " - Save affected files as UTF-8 (without ANSI/legacy code page conversion)."
Write-Host " - Re-run: powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1"
exit 1
