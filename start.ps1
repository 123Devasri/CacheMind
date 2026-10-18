$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Governed Semantic Cache - All-in-One Startup Script       " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Run Backend in a new window
Write-Host "Starting FastAPI Backend on http://127.0.0.1:8000..." -ForegroundColor Green
$PythonExe = if (Test-Path "$ScriptDir\.venv\Scripts\python.exe") { "$ScriptDir\.venv\Scripts\python.exe" } else { "python" }
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "cd `"$ScriptDir\backend`"; & `"$PythonExe`" app/main.py"

# 2. Wait 2 seconds
Start-Sleep -Seconds 2

# 3. Run Frontend in a new window
Write-Host "Starting Vite React Frontend on http://localhost:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", "cd `"$ScriptDir\frontend`"; npm.cmd run dev"

Write-Host "`nBoth services are launching in separate terminal windows." -ForegroundColor Yellow
Write-Host "Open http://localhost:5173 in your browser to interact with the application." -ForegroundColor Cyan

