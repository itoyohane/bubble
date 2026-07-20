$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $repoRoot
node .\node_modules\vite\bin\vite.js --host 127.0.0.1 --port 1420
