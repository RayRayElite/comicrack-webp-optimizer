$ErrorActionPreference = 'Stop'
$probe = Join-Path $PSScriptRoot ('Test Environment/Runs/filesystem_probe_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $probe | Out-Null
$sourceFile = Join-Path $probe 'source.cbz'
$convertedFile = Join-Path $probe 'converted.cbz'
[System.IO.File]::WriteAllText($sourceFile, 'original')
[System.IO.File]::WriteAllText($convertedFile, 'converted')
[System.IO.File]::Replace($convertedFile, $sourceFile, [System.Management.Automation.Language.NullString]::Value)
if ([System.IO.File]::ReadAllText($sourceFile) -ne 'converted') { throw 'Replacement failed' }
[System.IO.File]::WriteAllText($convertedFile, 'new')
$heldFile = [System.IO.File]::Open($sourceFile, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::None)
$blocked = $false
try { [System.IO.File]::Replace($convertedFile, $sourceFile, [System.Management.Automation.Language.NullString]::Value) } catch { $blocked = $true } finally { $heldFile.Dispose() }
if (-not $blocked -or -not [System.IO.File]::Exists($convertedFile) -or [System.IO.File]::ReadAllText($sourceFile) -ne 'converted') { throw 'Locked-file preservation failed' }
'PASS: actual .NET replacement and locked destination preserve both files' | Tee-Object -FilePath (Join-Path $probe 'result.txt')
