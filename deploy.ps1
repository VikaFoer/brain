# Simple Git deployment script
$ErrorActionPreference = "Continue"

# Find Git
$gitExe = $null
$paths = @("git", "C:\Program Files\Git\cmd\git.exe", "C:\Program Files (x86)\Git\cmd\git.exe")

foreach ($path in $paths) {
    try {
        if ($path -eq "git") {
            $null = Get-Command git -ErrorAction Stop
            $gitExe = "git"
            break
        } elseif (Test-Path $path) {
            $null = & $path --version 2>&1
            if ($?) {
                $gitExe = $path
                break
            }
        }
    } catch { }
}

if (-not $gitExe) {
    Write-Host "Git not found! Please restart terminal after installing Git." -ForegroundColor Red
    exit 1
}

Write-Host "Using Git: $gitExe" -ForegroundColor Green

function Run-Git {
    param([string[]]$args)
    if ($gitExe -eq "git") {
        & git $args
    } else {
        & $gitExe $args
    }
}

# Initialize
if (-not (Test-Path .git)) {
    Write-Host "Initializing repository..." -ForegroundColor Yellow
    Run-Git @("init")
}

# Add remote
$remoteCheck = Run-Git @("remote", "get-url", "origin") 2>&1
if ($remoteCheck -match "error|fatal|not found") {
    Write-Host "Adding remote..." -ForegroundColor Yellow
    Run-Git @("remote", "add", "origin", "https://github.com/VikaFoer/brain.git")
}

# Add files
Write-Host "Adding files..." -ForegroundColor Yellow
Run-Git @("add", ".")

# Commit
$status = Run-Git @("status", "--porcelain")
if ($status) {
    Write-Host "Creating commit..." -ForegroundColor Yellow
    Run-Git @("commit", "-m", "Initial commit: Legal Graph System")
    
    Write-Host "Setting branch to main..." -ForegroundColor Yellow
    Run-Git @("branch", "-M", "main")
    
    Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
    Write-Host "Authentication may be required" -ForegroundColor Yellow
    Run-Git @("push", "-u", "origin", "main")
    
    if ($?) {
        Write-Host "Successfully pushed to GitHub!" -ForegroundColor Green
        Write-Host "Repository: https://github.com/VikaFoer/brain" -ForegroundColor Cyan
    } else {
        Write-Host "Push failed. May need authentication (Personal Access Token)" -ForegroundColor Red
    }
} else {
    Write-Host "No changes to commit" -ForegroundColor Cyan
}

