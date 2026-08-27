$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..
& .\.venv\Scripts\python.exe manage.py backup_database --verify
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
