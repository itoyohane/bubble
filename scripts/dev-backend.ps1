$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$env:PYTHONPATH = "$repoRoot\.python_packages;$repoRoot\backend"
$env:BUBBLE_AGENT_DATA_DIR = "$repoRoot\demo-data"
Set-Location $repoRoot
python -m bubble_agent.main
