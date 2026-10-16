# Run from a NEW empty lesson folder in an administrator Windows PowerShell terminal.
# Analysis only, not cleanup. Writes results and DISM/system logs; not a machine snapshot.
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'This capture needs Windows. Fixture tests do not.' }
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) { throw 'Open a Windows terminal as administrator before capture.' }
$root = [IO.Path]::GetFullPath($PSScriptRoot)
$item = Get-Item -LiteralPath $root -Force
while ($null -ne $item) {
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked/reparse lesson parents are unsupported.' }
    $item = $item.Parent
}
$out = Join-Path $root 'results'
# No -Force: an existing results folder/file refuses before DISM is called.
$null = New-Item -ItemType Directory -Path $out -ErrorAction Stop
$log = Join-Path $out 'dism-engine.log'
$report = Join-Path $out 'dism-report.txt'
Write-Output 'Running DISM component-store analysis, not cleanup. This can take minutes.'
$lines = & "$env:WINDIR\System32\dism.exe" /Online /English /Cleanup-Image /AnalyzeComponentStore "/LogPath:$log" 2>&1
$exit = $LASTEXITCODE
$bytes = [Text.UTF8Encoding]::new($false).GetBytes(($lines -join "`n") + "`n")
$stream = [IO.File]::Open($report, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
Write-Output "Saved results/dism-report.txt and results/dism-engine.log. DISM exit: $exit"
if ($exit -ne 0) { throw 'DISM did not succeed. Keep the partial reports; do not retry into the same folder.' }
Write-Output 'Analysis returned success. No cleanup command was run. Windows may still write servicing logs/state.'
