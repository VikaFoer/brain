# PowerShell скрипт для автоматичного встановлення Git та завантаження на GitHub

Write-Host "=== Автоматичне завантаження на GitHub ===" -ForegroundColor Cyan
Write-Host ""

# Функція для перевірки чи встановлений Git
function Test-GitInstalled {
    try {
        $null = Get-Command git -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

# Перевірка Git
if (-not (Test-GitInstalled)) {
    Write-Host "Git не знайдено!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Варіанти встановлення:" -ForegroundColor Cyan
    Write-Host "1. Автоматично через winget (якщо встановлено)" -ForegroundColor White
    Write-Host "2. Вручну з https://git-scm.com/download/win" -ForegroundColor White
    Write-Host ""
    
    # Спробувати встановити через winget
    $wingetAvailable = Get-Command winget -ErrorAction SilentlyContinue
    if ($wingetAvailable) {
        Write-Host "Спробую встановити Git через winget..." -ForegroundColor Yellow
        try {
            winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
            Write-Host "Git встановлено! Перезапустіть термінал та запустіть скрипт знову." -ForegroundColor Green
            Write-Host "Або виконайте команди вручну:" -ForegroundColor Cyan
            Write-Host "  git init" -ForegroundColor White
            Write-Host "  git remote add origin https://github.com/VikaFoer/brain.git" -ForegroundColor White
            Write-Host "  git add ." -ForegroundColor White
            Write-Host "  git commit -m 'Initial commit'" -ForegroundColor White
            Write-Host "  git branch -M main" -ForegroundColor White
            Write-Host "  git push -u origin main" -ForegroundColor White
            exit
        } catch {
            Write-Host "Не вдалося встановити через winget." -ForegroundColor Red
        }
    } else {
        Write-Host "winget не доступний." -ForegroundColor Yellow
    }
    
    Write-Host ""
    Write-Host "Будь ласка, встановіть Git вручну:" -ForegroundColor Yellow
    Write-Host "  https://git-scm.com/download/win" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Після встановлення перезапустіть термінал та запустіть:" -ForegroundColor Yellow
    Write-Host "  .\deploy_to_github.ps1" -ForegroundColor Cyan
    Write-Host "  або" -ForegroundColor White
    Write-Host "  python deploy_github.py" -ForegroundColor Cyan
    exit
}

# Git знайдено - продовжуємо
Write-Host "Git знайдено! Продовжую..." -ForegroundColor Green
Write-Host ""

# Ініціалізація репозиторію
if (-not (Test-Path .git)) {
    Write-Host "Ініціалізація git репозиторію..." -ForegroundColor Yellow
    git init
}

# Перевірка remote
$remoteExists = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Додавання remote репозиторію..." -ForegroundColor Yellow
    git remote add origin https://github.com/VikaFoer/brain.git
} else {
    Write-Host "Remote вже налаштовано: $remoteExists" -ForegroundColor Green
}

# Додавання файлів
Write-Host "Додавання файлів..." -ForegroundColor Yellow
git add .

# Перевірка змін
$status = git status --porcelain
if ($status) {
    Write-Host "Створення commit..." -ForegroundColor Yellow
    $commitMessage = "Initial commit: Legal Graph System - система аналізу нормативно-правових актів"
    
    git commit -m $commitMessage
    
    Write-Host "Встановлення гілки main..." -ForegroundColor Yellow
    git branch -M main
    
    Write-Host "Завантаження на GitHub..." -ForegroundColor Yellow
    Write-Host "Може знадобитися автентифікація (Personal Access Token)" -ForegroundColor Yellow
    git push -u origin main
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Успішно завантажено на GitHub!" -ForegroundColor Green
        Write-Host "Репозиторій: https://github.com/VikaFoer/brain" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "Помилка при завантаженні." -ForegroundColor Red
        Write-Host "Можливі причини:" -ForegroundColor Yellow
        Write-Host "1. Потрібна автентифікація (Personal Access Token)" -ForegroundColor White
        Write-Host "2. Репозиторій вже існує і має інші файли" -ForegroundColor White
        Write-Host ""
        Write-Host "Спробуйте:" -ForegroundColor Cyan
        Write-Host "  git pull origin main --allow-unrelated-histories" -ForegroundColor White
        Write-Host "  git push -u origin main" -ForegroundColor White
    }
} else {
    Write-Host "Немає змін для commit" -ForegroundColor Cyan
    Write-Host "Спробую отримати зміни з GitHub..." -ForegroundColor Yellow
    git pull origin main --allow-unrelated-histories 2>$null
}
