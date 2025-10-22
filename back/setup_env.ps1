<#
Subimage Locator - Environment Setup Script
============================================
This script creates a virtual environment in `.venv`, activates it for the current shell,
upgrades pip and installs packages from `requirements.txt`.

Run from PowerShell in the `back` folder:
    .\setup_env.ps1

Or if using conda (currently detected), just run:
    pip install -r requirements.txt
#>

Write-Host "=== Subimage Locator Environment Setup ===" -ForegroundColor Cyan

# Check if in conda environment
$condaEnv = $env:CONDA_DEFAULT_ENV
if ($condaEnv) {
    Write-Host "`nConda environment detected: $condaEnv" -ForegroundColor Yellow
    Write-Host "Installing packages with pip..." -ForegroundColor Yellow
    
    python -m pip install --upgrade pip
    if (Test-Path (Join-Path $PSScriptRoot "requirements.txt")) {
        python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
        Write-Host "`n✅ Dependencies installed successfully!" -ForegroundColor Green
        Write-Host "`nNext steps:" -ForegroundColor Cyan
        Write-Host "  1. Run tests: `$env:PYTHONPATH=`"$PSScriptRoot\src`"; pytest tests/ -v"
        Write-Host "  2. Create demo: python create_demo.py"
        Write-Host "  3. See QUICKSTART.md for usage examples"
    }
} else {
    # Standard venv setup
    $venvPath = Join-Path $PSScriptRoot ".venv"

    if (-Not (Test-Path $venvPath)) {
        Write-Host "Creating virtual environment at $venvPath..." -ForegroundColor Yellow
        python -m venv $venvPath
    } else {
        Write-Host "Virtual environment already exists at $venvPath" -ForegroundColor Green
    }

    $activate = Join-Path $venvPath "Scripts\Activate.ps1"

    if (Test-Path $activate) {
        Write-Host "Activating virtual environment..." -ForegroundColor Yellow
        & $activate
        Write-Host "Upgrading pip and installing dependencies from requirements.txt..." -ForegroundColor Yellow
        python -m pip install --upgrade pip
        if (Test-Path (Join-Path $PSScriptRoot "requirements.txt")) {
            python -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
            Write-Host "`n✅ Setup complete!" -ForegroundColor Green
            Write-Host "`nNext steps:" -ForegroundColor Cyan
            Write-Host "  1. Run tests: `$env:PYTHONPATH=`"$PSScriptRoot\src`"; pytest tests/ -v"
            Write-Host "  2. Create demo: python create_demo.py"
            Write-Host "  3. See QUICKSTART.md for usage examples"
        } else {
            Write-Host "No requirements.txt found. Add dependencies to requirements.txt and re-run this script." -ForegroundColor Red
        }
    } else {
        Write-Host "Activation script not found at $activate. Make sure venv was created successfully." -ForegroundColor Red
    }
}
