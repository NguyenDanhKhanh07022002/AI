# Script helper để chạy web interface trên Windows
# Tự động refresh PATH và chạy web app

# Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# Tìm Python
$pythonExe = $null

# Thử 1: Dùng python command
try {
    $result = python --version 2>&1
    if ($LASTEXITCODE -eq 0 -or $result -match "Python") {
        $pythonExe = "python"
        Write-Host "Found: $result" -ForegroundColor Green
    }
} catch {
    # Ignore
}

# Thử 2: Tìm Python trong PATH
if ($null -eq $pythonExe) {
    $pythonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "$env:ProgramFiles\Python310\python.exe"
    )
    
    foreach ($path in $pythonPaths) {
        if (Test-Path $path) {
            $pythonExe = $path
            $version = & $path --version 2>&1
            Write-Host "Found Python at: $path" -ForegroundColor Green
            Write-Host "Version: $version" -ForegroundColor Green
            break
        }
    }
}

# Thử 3: Dùng where.exe để tìm
if ($null -eq $pythonExe) {
    $whereResult = where.exe python 2>&1 | Where-Object { $_ -notmatch "WindowsApps" -and $_ -match "\.exe$" } | Select-Object -First 1
    if ($whereResult -and (Test-Path $whereResult)) {
        $pythonExe = $whereResult
        Write-Host "Found Python at: $pythonExe" -ForegroundColor Green
    }
}

# Kiểm tra nếu không tìm thấy
if ($null -eq $pythonExe) {
    Write-Host "Error: Python not found!" -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Or restart PowerShell after installing Python." -ForegroundColor Yellow
    exit 1
}

# Chạy web app
Write-Host ""
Write-Host "Starting System K Vehicle Counting Tool - Web Interface" -ForegroundColor Cyan
Write-Host "=" * 50
Write-Host "Server will start on http://localhost:5000" -ForegroundColor Yellow
Write-Host "Open your browser and navigate to http://localhost:5000" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "=" * 50
Write-Host ""

& $pythonExe web_app.py

