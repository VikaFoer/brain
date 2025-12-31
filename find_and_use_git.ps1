# Знайти та використати Git
$gitExe = $null

# Список можливих місць
$possiblePaths = @(
    "git",  # В PATH
    "C:\Program Files\Git\cmd\git.exe",
    "C:\Program Files (x86)\Git\cmd\git.exe",
    "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe",
    "$env:ProgramFiles\Git\cmd\git.exe"
)

# Перевірити GitHub Desktop
$githubDesktop = Get-ChildItem "$env:LOCALAPPDATA\GitHubDesktop" -Directory -ErrorAction SilentlyContinue | 
    Sort-Object Name -Descending | Select-Object -First 1
if ($githubDesktop) {
    $gitPath = Join-Path $githubDesktop.FullName "resources\app\git\cmd\git.exe"
    if (Test-Path $gitPath) {
        $possiblePaths += $gitPath
    }
}

# Шукати Git
foreach ($path in $possiblePaths) {
    try {
        if ($path -eq "git") {
            $result = Get-Command git -ErrorAction Stop
            $gitExe = "git"
            Write-Host "Знайдено Git в PATH" -ForegroundColor Green
            break
        } elseif (Test-Path $path) {
            $result = & $path --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                $gitExe = $path
                Write-Host "Знайдено Git: $path" -ForegroundColor Green
                break
            }
        }
    } catch {
        continue
    }
}

if (-not $gitExe) {
    Write-Host "Git не знайдено!" -ForegroundColor Red
    Write-Host "Будь ласка, перезапустіть термінал після встановлення Git" -ForegroundColor Yellow
    Write-Host "Або встановіть Git з: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nВикористовую: $gitExe`n" -ForegroundColor Cyan

# Функція для виконання git команд
function Invoke-Git {
    param([string[]]$Args)
    if ($gitExe -eq "git") {
        & git $Args
    } else {
        & $gitExe $Args
    }
}

# Виконати команди
Write-Host "Ініціалізація репозиторію..." -ForegroundColor Yellow
if (-not (Test-Path .git)) {
    Invoke-Git init
} else {
    Write-Host "Репозиторій вже ініціалізовано" -ForegroundColor Green
}

Write-Host "`nПеревірка remote..." -ForegroundColor Yellow
try {
    $remote = Invoke-Git @("remote", "get-url", "origin") 2>&1
    if ($remote -and -not ($remote -match "error|fatal")) {
        Write-Host "Remote вже налаштовано: $remote" -ForegroundColor Green
    } else {
        throw "Remote not found"
    }
} catch {
    Write-Host "Додавання remote..." -ForegroundColor Yellow
    Invoke-Git @("remote", "add", "origin", "https://github.com/VikaFoer/brain.git")
}

Write-Host "`nДодавання файлів..." -ForegroundColor Yellow
Invoke-Git add .

Write-Host "`nПеревірка статусу..." -ForegroundColor Yellow
$status = Invoke-Git @("status", "--porcelain")
if ($status) {
    Write-Host "Створення commit..." -ForegroundColor Yellow
    Invoke-Git @("commit", "-m", "Initial commit: Legal Graph System")
    
    Write-Host "`nВстановлення гілки main..." -ForegroundColor Yellow
    Invoke-Git @("branch", "-M", "main")
    
    Write-Host "`nЗавантаження на GitHub..." -ForegroundColor Yellow
    Write-Host "Може знадобитися автентифікація" -ForegroundColor Yellow
    Invoke-Git @("push", "-u", "origin", "main")
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`nУспішно завантажено!" -ForegroundColor Green
        Write-Host "Репозиторій: https://github.com/VikaFoer/brain" -ForegroundColor Cyan
    } else {
        Write-Host "`nПомилка при завантаженні" -ForegroundColor Red
        Write-Host "Можливо потрібна автентифікація (Personal Access Token)" -ForegroundColor Yellow
    }
} else {
    Write-Host "Немає змін для commit" -ForegroundColor Cyan
}
