$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$targetTriple = 'x86_64-pc-windows-msvc'
$temporaryPackages = Join-Path $repoRoot '.python_packages'
$backendRoot = Join-Path $repoRoot 'backend'
$binaryDirectory = Join-Path $repoRoot 'apps\desktop\src-tauri\binaries'

$env:PYTHONPATH = "$temporaryPackages;$backendRoot"
New-Item -ItemType Directory -Force $binaryDirectory | Out-Null

python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --name bubble-agent-backend `
  --paths $temporaryPackages `
  --paths $backendRoot `
  --collect-submodules langgraph `
  --collect-submodules langchain_core `
  --collect-submodules langgraph_checkpoint_sqlite `
  --hidden-import sqlite_vec `
  --distpath (Join-Path $backendRoot 'dist') `
  --workpath (Join-Path $backendRoot 'build') `
  --specpath $backendRoot `
  (Join-Path $backendRoot 'bubble_agent\main.py')

$builtBinary = Join-Path $backendRoot 'dist\bubble-agent-backend.exe'
$sidecarBinary = Join-Path $binaryDirectory "bubble-agent-backend-$targetTriple.exe"
Copy-Item -LiteralPath $builtBinary -Destination $sidecarBinary -Force
Write-Output $sidecarBinary
