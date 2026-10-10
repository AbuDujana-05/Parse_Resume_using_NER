$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendRoot = Join-Path $ProjectRoot "backend"
$Requirements = Join-Path $BackendRoot "requirements.txt"
$HealthUrl = "http://127.0.0.1:8000/api/health"
$FrontendUrl = "http://127.0.0.1:5173"

function Stop-PortProcess([int]$Port) {
    $connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    foreach ($connection in $connections) {
        $processId = $connection.OwningProcess
        if ($processId -and $processId -ne $PID) {
            try {
                Stop-Process -Id $processId -Force -ErrorAction Stop
                Write-Host "[INFO] Stopped stale process $processId on port ${Port}" -ForegroundColor Yellow
            } catch {
                Write-Host "[WARN] Could not stop process $processId on port ${Port}: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }
    }
}

function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python -and $python.Source -notlike "*WindowsApps*") { return $python.Source }

    $installedPython = Get-ChildItem "$env:LocalAppData\Programs\Python\Python*\python.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
    if ($installedPython) { return $installedPython }

    if (Get-Command py -ErrorAction SilentlyContinue) { return "py" }
    throw "Python was not found. Install Python 3.11+ and ensure 'python' or 'py' is available in PATH."
}

function Test-BackendImports([string]$PythonCommand) {
    & $PythonCommand -c "import fastapi, uvicorn, spacy, cv2, pytesseract, docx, pptx, PIL" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-BackendDependencies([string]$PythonCommand) {
    if (Test-BackendImports $PythonCommand) { return }
    Write-Host "[INFO] Backend Python packages are missing. Installing backend requirements..." -ForegroundColor Yellow
    & $PythonCommand -m pip install -r $Requirements
    if ($LASTEXITCODE -ne 0) {
        throw "Backend dependency installation failed. Run: $PythonCommand -m pip install -r backend\requirements.txt"
    }
}

function Test-Tesseract {
    $configured = $env:TESSERACT_CMD
    $candidates = @(
        $configured,
        "${env:ProgramFiles}\Tesseract-OCR\tesseract.exe",
        "${env:ProgramFiles(x86)}\Tesseract-OCR\tesseract.exe"
    ) | Where-Object { $_ -and (Test-Path $_) }
    if ($candidates.Count -gt 0) {
        $env:TESSERACT_CMD = $candidates[0]
        return
    }
    if (-not (Get-Command tesseract -ErrorAction SilentlyContinue)) {
        throw "Tesseract OCR is required for JPG/PNG resume uploads. Install it, then restart: winget install UB-Mannheim.TesseractOCR"
    }
}

function Wait-Backend([int]$Attempts = 60) {
    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            $response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 2
            if ($response.status -eq "ok" -and $response.model_loaded -eq $true) {
                return $true
            }
        } catch { }
        Start-Sleep -Milliseconds 750
    }
    return $false
}

Write-Host "=== PARSE RESUME USING NER ===" -ForegroundColor Cyan
Write-Host "Starting local FastAPI + React only. Netlify configuration is not used here." -ForegroundColor Gray

$PythonCommand = Get-PythonCommand
Ensure-BackendDependencies $PythonCommand
Test-Tesseract

Stop-PortProcess 8000
Stop-PortProcess 5173

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-Command",
    "Set-Location '$BackendRoot'; & '$PythonCommand' app.py"
)

if (-not (Wait-Backend)) {
    throw "FastAPI did not become healthy on $HealthUrl. Check the backend terminal for the actual startup error."
}

Write-Host "[OK] FastAPI is healthy and the spaCy model is loaded." -ForegroundColor Green

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-NoProfile",
    "-Command",
    "Set-Location '$ProjectRoot'; npm run dev:frontend -- --host 127.0.0.1"
)

Write-Host "Backend : http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Frontend: $FrontendUrl" -ForegroundColor Green
Write-Host "Open the frontend only after the [OK] message above appears." -ForegroundColor Cyan
