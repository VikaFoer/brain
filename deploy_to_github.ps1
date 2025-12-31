# PowerShell скрипт для завантаження на GitHub
# Використання: .\deploy_to_github.ps1

Write-Host "🚀 Початок завантаження на GitHub..." -ForegroundColor Green

# Перевірка чи ініціалізовано git репозиторій
if (-not (Test-Path .git)) {
    Write-Host "📦 Ініціалізація git репозиторію..." -ForegroundColor Yellow
    git init
}

# Перевірка remote
$remoteExists = git remote get-url origin 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "🔗 Додавання remote репозиторію..." -ForegroundColor Yellow
    git remote add origin https://github.com/VikaFoer/brain.git
} else {
    Write-Host "✅ Remote вже налаштовано: $remoteExists" -ForegroundColor Green
}

# Додавання всіх файлів
Write-Host "📝 Додавання файлів..." -ForegroundColor Yellow
git add .

# Перевірка чи є зміни для commit
$status = git status --porcelain
if ($status) {
    Write-Host "💾 Створення commit..." -ForegroundColor Yellow
    git commit -m "Initial commit: Legal Graph System - система аналізу нормативно-правових актів
    
- Backend на FastAPI з підтримкою PostgreSQL та Neo4j
- Frontend з візуалізацією графів (D3.js)
- Інтеграція з API Ради України
- Виділення елементів множини через OpenAI
- GraphRAG для аналізу зв'язків
- Чат-аналітика з OpenAI"
    
    Write-Host "📤 Завантаження на GitHub..." -ForegroundColor Yellow
    git branch -M main
    git push -u origin main
    
    Write-Host "✅ Успішно завантажено на GitHub!" -ForegroundColor Green
} else {
    Write-Host "ℹ️  Немає змін для commit" -ForegroundColor Cyan
}

Write-Host "`n📚 Репозиторій: https://github.com/VikaFoer/brain" -ForegroundColor Cyan

